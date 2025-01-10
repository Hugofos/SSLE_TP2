const net = require('net');
const express = require('express');
const fs = require('fs');
const uuid = require('uuid');
const moment = require('moment');

class NodeServer {
    constructor(id, port, peers) {
        this.id = id;
        this.port = port;
        this.peers = peers;
        this.isTraitor = false;
        this.log = {};
        this.processedMessages = new Set();
        this.trustScores = Object.fromEntries(peers.map(peer => [`${peer.host}:${peer.port}`, 1.0]));
    }

    startPeerServer() {
        const server = net.createServer(socket => {
            socket.on('data', data => {
                try {
                    const message = JSON.parse(data.toString());
                    this.handlePeerMessage(message);
                } catch (err) {
                    //console.error(`Node ${this.id}: Error processing message -`, err.message);
                }
            });
        });

        server.listen(this.port, () => {
            console.log(`Node ${this.id}: Peer server started on port ${this.port}`);
        });
    }

    async handlePeerMessage(message) {
        const {
            senderId,
            originId,
            amount,
            messageId,
            senderPort,
            senderAddress
        } = message;
    
        // Check if the message has already been processed
        if (this.processedMessages.has(`${senderAddress}-${messageId}`)) {
            return;
        }
    
        // Mark the message as processed
        this.processedMessages.add(`${senderAddress}-${messageId}`);
    
        console.log(`Node ${this.id}: Received from Node ${senderAddress}:${senderPort} (origin: ${originId}): ${amount}`);
    
        // Log the message
        this.logMessage(`${senderAddress}:${senderPort}`, amount);
    
        // Avoid rebroadcasting messages that originated from this node
        if (originId === this.id) return;
    
        // Forward to peers
        this.peers.forEach(async peer => {
            await this.sendPeerMessage(peer, originId, amount, messageId);
        });
    }

    async sendPeerMessage(peer, originId, amount, messageId) {
        const client = new net.Socket();

        const message = {
            senderId: this.port - 8000,
            originId: originId,
            amount: this.isTraitor
                ? Math.random() > 0.5
                    ? amount + 50
                    : amount - 50
                : amount,
            messageId: messageId,
            senderPort: this.port,
            senderAddress: "0.0.0.0" //Replace with node ip
        };

        try {
            client.connect(peer.port, peer.host, () => {
                client.write(JSON.stringify(message));
                client.end();
            });
        } catch (err) {
            console.error(`Node ${this.id}: Failed to connect to Node at ${peer.host}:${peer.port}`);
        }
    }

    startHttpServer() {
        const app = express();
        app.use(express.json());

        app.post('/send', async (req, res) => {
            const { amount } = req.body;
            if (amount === undefined) {
                return res.status(400).send("Missing 'amount' in request");
            }

            console.log(`Node ${this.id}: Received HTTP request to send amount ${amount}`);
            const messageId = uuid.v4();
            this.processedMessages.add(`${this.id}-${messageId}`);
            await this.broadcastMessage(amount, messageId);
            res.send('Message broadcasted successfully');
        });

        // New metrics endpoint to return trust scores as JSON
        app.get('/metrics', (req, res) => {
            const metrics = {
                timestamp: moment().format('YYYY-MM-DD HH:mm:ss'),
                trustScores: this.trustScores,
                tecnology: 'Node'
            };
            res.json(metrics);
        });

        const httpPort = this.port + 1000;
        app.listen(httpPort, () => {
            console.log(`Node ${this.id}: HTTP server started on port ${httpPort}`);
        });
    }

    async broadcastMessage(amount, messageId) {
        const originId = this.id;
        const tasks = this.peers.map(peer => this.sendPeerMessage(peer, originId, amount, messageId));
        await Promise.all(tasks);
    }

    logMessage(senderAddress, amount) {
        // Log the message with the sender's address
        this.log[`${senderAddress}`] = { amount, senderAddress };
        
        // Check if the threshold is met
        if (Object.keys(this.log).length % this.peers.length === 0) {
            console.log(`Node ${this.port - 8000}: Threshold reached. Validating trust...`);
            this.validateAndUpdateTrust();
        }
    }

    validateAndUpdateTrust() {
        const counts = {};
    
        // Count occurrences of each amount
        for (const key in this.log) {
            const { amount } = this.log[key];
            counts[amount] = (counts[amount] || 0) + 1;
        }
    
        // Find the consensus amount
        const consensusAmount = Object.keys(counts)
            .map(Number) // Convert keys to numbers
            .reduce((a, b) => (counts[a] > counts[b] ? a : b));
    
        // Validate and update trust scores
        for (const key in this.log) {
            const { amount, senderAddress } = this.log[key];
    
            if (amount !== consensusAmount) {
                if (this.trustScores[key] === undefined) {
                    console.error(`Node ${this.id}: Trust key ${key} not found in trustScores`);
                } else {
                    this.trustScores[key] = Math.max(0, this.trustScores[key] - 0.2).toFixed(1);
                    console.log(`Node ${this.id}: Lowering trust in Node ${senderAddress}. Trust: ${this.trustScores[key]}`);
                }
            } else {
                this.trustScores[key] = 1.0;
                console.log(`Node ${this.id}: Node ${senderAddress} sent correct value!`);
            }
        }
    
        this.writeTrustScoresToLog();
        this.log = {};
    }

    writeTrustScoresToLog() {
        const logFile = `trust_scores_node_${this.id}.log`;
        const logData = `Trust Scores at ${moment().format('YYYY-MM-DD HH:mm:ss')}:\n` +
            Object.entries(this.trustScores)
                .map(([peer, score]) => `${peer}: ${score}`)
                .join('\n') +
            '\n\n';

        fs.appendFileSync(logFile, logData);
    }
}

// Main logic
const nodeId = 0;
const nodePort = 8000;
const peerPorts = [
    { host: '10.151.101.203', port: 8000 },
    { host: '10.151.101.197', port: 8000 },
    { host: '10.151.101.179', port: 8000 },
    { host: '10.151.101.192', port: 8000 },
    { host: '10.151.101.152', port: 8000 }
]

const node = new NodeServer(nodeId, nodePort, peerPorts);
node.startPeerServer();
node.startHttpServer();
