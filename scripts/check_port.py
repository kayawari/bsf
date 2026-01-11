#!/usr/bin/env python3
"""
Utility script to check what's using port 5000 and help resolve conflicts.
"""
import subprocess
import sys

def check_port_usage(port=5000):
    """Check what process is using the specified port."""
    try:
        # Use lsof to find processes using the port
        result = subprocess.run(
            ['lsof', '-i', f':{port}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"Port {port} is being used by:")
            print(result.stdout)
            print("\nTo resolve this:")
            print("1. On macOS, check System Settings > Sharing > AirPlay Receiver and disable it")
            print("2. Or kill the process using the PID shown above")
            print(f"3. Or use a different port: PORT=8080 python run.py")
        else:
            print(f"Port {port} appears to be available.")
            
    except FileNotFoundError:
        print("lsof command not found. On macOS, this should be available by default.")
    except Exception as e:
        print(f"Error checking port usage: {e}")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    check_port_usage(port)