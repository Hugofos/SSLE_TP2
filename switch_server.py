from flask import Flask
import os
import subprocess

app = Flask(__name__)

# Global variables to hold the processes
node_process = None
python_process = None

# Function to start the Node.js server
def start_node():
    global node_process
    if node_process is None:
        print("Starting Node.js server...")
        node_process = subprocess.Popen(['node', 'node.js'])
        print(f"Node.js server started with PID {node_process.pid}")

# Function to start the Python server
def start_python():
    global python_process
    if python_process is None:
        print("Starting Python server...")
        python_process = subprocess.Popen(['python3', 'node.py'])
        print(f"Python server started with PID {python_process.pid}")

# Function to stop the current server
def stop_server():
    global node_process, python_process
    if node_process:
        print(f"Stopping Node.js server with PID {node_process.pid}...")
        node_process.terminate()
        node_process.wait()
        print(f"Node.js server with PID {node_process.pid} stopped")
        node_process = None

    if python_process:
        print(f"Stopping Python server with PID {python_process.pid}...")
        python_process.terminate()
        python_process.wait()
        print(f"Python server with PID {python_process.pid} stopped")
        python_process = None

# Endpoint to switch to the Python server
@app.route('/change_be', methods=['GET'])
def change_tbe():
    print("Received request to switch to Python server...")

# Endpoint to switch to the Node.js server
@app.route('/change_to_node', methods=['GET'])
def change_to_node():
    print("Received request to switch to Node.js server...")
    stop_server()
    start_node()
    return "Switched to Node.js server."

# Main execution
if __name__ == '__main__':
    # Start the initial server (Node.js by default)
    start_node()

    # Run Flask directly in the main thread
    app.run(host='0.0.0.0', port=5000)