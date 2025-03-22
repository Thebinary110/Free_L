import subprocess
import time
import sys
import os
import threading
import signal

def run_backend():
    print("Starting FastAPI backend...")
    return subprocess.Popen(
        ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

def run_frontend():
    print("Starting Streamlit frontend...")
    return subprocess.Popen(
        ["streamlit", "run", "streamlit_app.py", "--server.port", "8501"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

def log_output(process, name):
    for line in iter(process.stdout.readline, ''):
        print(f"[{name}] {line}", end='')

def main():
    # Create the processes
    backend_process = run_backend()
    time.sleep(3)  # Give backend time to start before frontend
    frontend_process = run_frontend()
    
    # Set up process output logging
    backend_thread = threading.Thread(target=log_output, args=(backend_process, "Backend"), daemon=True)
    frontend_thread = threading.Thread(target=log_output, args=(frontend_process, "Frontend"), daemon=True)
    
    backend_thread.start()
    frontend_thread.start()
    
    # Set up signal handling to terminate processes on Ctrl+C
    def signal_handler(sig, frame):
        print("\nShutting down processes...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep main thread alive
    try:
        print("\nNEET Counseling Predictor is running!")
        print(f"Backend:  http://localhost:8000/docs")
        print(f"Frontend: http://localhost:8501")
        
        # Wait for processes
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        # This handles the case when Ctrl+C is pressed
        print("\nShutting down processes...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main() 