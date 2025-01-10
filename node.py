import asyncio
import random
import json
from aiohttp import web
import uuid
import datetime
import requests

class NodeServer:
    def __init__(self, id, port, peers):
        self.id = id
        self.port = port
        self.peers = peers
        self.is_traitor = False
        self.log = {}
        self.trust_scores = {f"{peer[0]}:{peer[1]}": 1.0 for peer in peers}

    async def handle_peer_message(self, reader, writer):
        """Handle incoming peer messages."""
        try:
            data = await reader.read(-1)
            message = json.loads(data.decode())
            sender_address = message['senderAddress']
            sender_port = message['senderPort']
            sender_key = f"{sender_address}:{sender_port}"
            origin_id = message['originId']
            amount = message['amount']
            message_id = message['messageId']
        except Exception as es:
            return

        # Log the message
        self.log_message(origin_id, sender_key, amount)

        # Avoid rebroadcasting processed messages
        if message_id in self.log:
            return

        # Forward to peers
        for peer in self.peers:
            if f"{peer[0]}:{peer[1]}" != sender_key:
                try:
                    await self.send_peer_message(peer, origin_id, amount, message_id)
                except Exception as e:
                    print(f"Node {self.id}: Failed to forward to Node at {peer}: {e}")

    async def send_peer_message(self, peer, origin_id, amount, message_id):
        """Send a message to a peer."""
        try:
            reader, writer = await asyncio.open_connection(*peer)
            message = {
                "senderId": self.id,
                "originId": origin_id,
                "amount": random.choice([amount + 50, amount - 50]) if self.is_traitor else amount,
                "messageId": message_id,
                "senderPort": self.port,
                "senderAddress": "0.0.0.0" #Replace with node ip
            }
            writer.write(json.dumps(message).encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            print(f"Node {self.id}: Failed to connect to Node at {peer}: {e}")
    
    async def handle_metrics_request(self, request):
        """Handle the /metrics endpoint to return trust scores."""
        trust_scores_output = {
            "trust_scores": self.trust_scores,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "tecnology": "Python"
        }
        return web.json_response(trust_scores_output)

    async def start_peer_server(self):
        """Start the node server to receive messages."""
        server = await asyncio.start_server(self.handle_peer_message, '0.0.0.0', self.port)
        print(f"Node {self.id}: Peer server started on port {self.port}")
        async with server:
            await server.serve_forever()

    def validate_and_update_trust(self):
        """Validate messages and update trust levels."""
        # Determine the most common amount (consensus)
        counts = {}
        for sender_key, amount in self.log.items():
            counts[amount] = counts.get(amount, 0) + 1
        consensus_amount = max(counts, key=counts.get)

        # Update trust scores for nodes that sent inconsistent messages
        for sender_key, amount in self.log.items():
            if amount != consensus_amount:
                self.trust_scores[sender_key] = max(0, round(self.trust_scores[sender_key] - 0.2, 1))
                print(f"Node {self.id}: Lowering trust in Node {sender_key}. Trust: {self.trust_scores[sender_key]}")
            else:
                self.trust_scores[sender_key] = 1.0
                print(f"Node {self.id}: Node {sender_key} sent correct value!")

        self.write_trust_scores_to_log()
        self.log = {}

    def write_trust_scores_to_log(self):
        """Write current trust scores to a log file."""
        with open(f"trust_scores_node_{self.id}.log", "a") as log_file:
            log_file.write(f"Trust Scores at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n")
            for peer, score in self.trust_scores.items():
                log_file.write(f"{peer}: {score}\n")
            log_file.write("\n")

    def log_message(self, origin_id, sender_key, amount):
        """Log a message and trigger validation when enough messages are received."""
        self.log[sender_key] = amount

        if len(self.log) % len(self.peers) == 0:
            print(f"Node {self.id}: Threshold reached. Validating trust...")
            self.validate_and_update_trust()

    async def start_http_server(self):
        """Start the HTTP server to handle incoming POST requests."""
        app = web.Application()
        app.router.add_post('/send', self.handle_http_request)
        app.router.add_get('/metrics', self.handle_metrics_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port + 1000)
        print(f"Node {self.id}: HTTP server started on port {self.port + 1000}")
        await site.start()

    async def handle_http_request(self, request):
        """Handle incoming HTTP requests to send messages."""
        data = await request.json()
        amount = data.get("amount")
        if amount is None:
            return web.Response(text="Missing 'amount' in request", status=400)

        message_id = str(uuid.uuid4())
        print(f"Node {self.id}: Received HTTP request to send amount {amount}")
        await self.broadcast_message(amount, message_id)
        return web.Response(text="Message broadcasted successfully")

    async def broadcast_message(self, amount, message_id):
        """Send a message to all peers."""
        tasks = [self.send_peer_message(peer, self.id, amount, message_id) for peer in self.peers]
        await asyncio.gather(*tasks)

def register_with_consul():
    payload = {
        "ID": "node0",
        "Name": "node0",
        "Tags": ["Python"],
        "Address": "10.151.101.203",
        "Port": 8000,
        "Check": {
            "http": "http://10.151.101.203:8000/metrics",
            "Interval": "10s"
        }
    }
    requests.put("http://10.151.101.98:8500/v1/agent/service/register", json=payload)

async def main():
    node_id = 0
    node_port = 8000
    peer_ports = [
        ("10.151.101.203", 8000),
        ("10.151.101.197", 8000),
        ("10.151.101.179", 8000),
        ("10.151.101.192", 8000),
        ("10.151.101.152", 8000)
    ]

    node = NodeServer(node_id, node_port, peer_ports)

    # Start peer server and HTTP server concurrently
    await asyncio.gather(
        node.start_peer_server(),
        node.start_http_server()
    )

if __name__ == "__main__":
    #register_with_consul()
    asyncio.run(main())
