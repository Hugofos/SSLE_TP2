import os
import signal
import subprocess
import time

# Global variables to hold the processes
node_process = None
python_process = None

# Function to start the Node.js server
def start_node():
    global node_process
    print("Starting Node.js server...")
    node_process = subprocess.Popen(['node', 'node.js'])
    print(f"Node.js server started with PID {node_process.pid}")

# Function to start the Python server
def start_python():
    global python_process
    print("Starting Python server...")
    python_process = subprocess.Popen(['python3', 'node.py'])
    print(f"Python server started with PID {python_process.pid}")

# Function to stop the current server
def stop_server():
    global node_process, python_process
    if node_process:
        print(f"Stopping Node.js server with PID {node_process.pid}...")
        node_process.terminate()
        node_process.wait()  # Wait for the Node.js process to finish
        print(f"Node.js server with PID {node_process.pid} stopped")
        node_process = None

    if python_process:
        print(f"Stopping Python server with PID {python_process.pid}...")
        python_process.terminate()
        python_process.wait()  # Wait for the Python process to finish
        print(f"Python server with PID {python_process.pid} stopped")
        python_process = None

# Signal handlers to switch between servers
def switch_to_python(signum, frame):
    print("Switching to Python server...")
    stop_server()
    start_python()

def switch_to_node(signum, frame):
    print("Switching to Node.js server...")
    stop_server()
    start_node()

# Set up signal handling
signal.signal(signal.SIGUSR1, switch_to_python)  # Switch to Python
signal.signal(signal.SIGUSR2, switch_to_node)    # Switch to Node.js

# Start the initial server (Node.js by default)
start_node()

# Keep the script running, waiting for signals
print(f"Current script PID is {os.getpid()}")
while True:
    time.sleep(1)  # Keep the script running to listen for signals
