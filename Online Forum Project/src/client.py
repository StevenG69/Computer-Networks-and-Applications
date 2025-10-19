"""
"client.py"
Forum Application Client
Usage: python3 client.py SERVER_IP SERVER_PORT
"""

from socket import *
from threading import Thread
import sys
import os

if len(sys.argv) != 3:
    print("\n=== Usage: python3 client.py SERVER_IP SERVER_PORT ====\n")
    exit(1)
# Server configuration
SERVER_HOST = sys.argv[1]
SERVER_PORT = int(sys.argv[2])
SERVER_ADDRESS = (SERVER_HOST, SERVER_PORT)
# Global variables
udp_socket = None  # For Thread operation
tcp_socket = None  # For UPD/DWN implementation
current_user = None
is_client_running = False


def send_command(command):
    global udp_socket
    for _ in range(6):
        try:
            udp_socket.sendto(command.encode(), SERVER_ADDRESS)
            response, _ = udp_socket.recvfrom(1024)
            return response.decode()
        except timeout:
            print("Timeout...Retrying...")
    return "ERROR: No response"


def auth_user():
    global current_user
    password = None
    while True:
        username = input("Enter username: ").strip()
        if not username:
            print("ERROR: Name required!")
            continue
        response = send_command(f"LOGIN {username}")
        if response == "PASSWORD_REQUIRED":
            password = input("Enter password: ")
            if not password:
                print("ERROR: Password required!")
                continue
            auth_response = send_command(f"AUTH {username} {password}")
            if "Login successful" in auth_response:
                current_user = username
                print(f"Welcome to the forum, {current_user}!")
                return
            print(auth_response)
            password = None
        elif response == "NEW_USER":
            pwd = input("Enter password to register: ").strip()
            if not pwd:
                print("ERROR: Password required!")
                continue
            reg_response = send_command(f"REGISTER {username} {pwd}")
            if "Registration successful" in reg_response:
                current_user = username
                print(f"Welcome to the forum, {username}!")
                return
            else:
                print(reg_response)


def exit_forum():
    global is_client_running
    response = send_command(f"XIT {current_user}")
    is_client_running = False
    print(response)


def create_thread(title):
    if not title or " " in title:
        print("ERROR: Invalid title")
        return
    response = send_command(f"CRT {current_user} {title}")
    print(response)


def list_threads():
    response = send_command("LST")
    print(response)


def post_message(args):
    msg_parts = args.split(" ", 1)
    if len(msg_parts) != 2:
        print("Input with: MSG <thread_title> <message>")
        return
    title, message = msg_parts
    if not title or " " in title:
        print("ERROR: Invalid title")
        return
    response = send_command(f"MSG {current_user} {title} {message}")
    print(response)


def read_thread(title):
    if not title or " " in title:
        print("ERROR: Invalid title")
        return
    response = send_command(f"RDT {title}")
    print(f"\n---Thread: {title}\n{response}\n---")


def edit_message(args):
    edt_parts = args.split(" ", 2)
    if len(edt_parts) != 3:
        print("Input with: EDT <thread_title> <message_number> <new_message>")
        return
    title, msg_num_str, new_msg = edt_parts
    try:
        msg_num = int(msg_num_str)
        if msg_num <= 0:
            raise ValueError
    except ValueError:
        print("ERROR: Invalid message number")
        return
    if not title or " " in title:
        print("ERROR: Invalid title")
        return
    if not new_msg:
        print("ERROR: New message required")
        return
    response = send_command(f"EDT {current_user} {title} {msg_num} {new_msg}")
    print(response)


def delete_message(args):
    try:
        title, msg_num_str = args.split(" ", 1)
    except ValueError:
        print("Input with: DLT <thread_title> <message_number>")
        return
    if not title or " " in title:
        print("ERROR: Invalid title")
        return
    try:
        msg_num = int(msg_num_str)
        if msg_num < 1:
            raise ValueError
    except ValueError:
        print("ERROR: Invalid message number")
        return
    response = send_command(f"DLT {current_user} {title} {msg_num}")
    print(response)


def remove_thread(args):
    title = args.strip()
    if not title or " " in title:
        print("ERROR: Invalid title")
        return
    response = send_command(f"RMV {current_user} {title}")
    print(response)


def upload_file(args):
    parts = args.split(" ", 1)
    if len(parts) != 2:
        print("Input with: UPD <thread> <file>")
        return
    title, fname = parts
    if not os.path.exists(fname):
        print(f"{fname} not found")
        return
    print(f"Upload '{fname}' to '{title}'")
    response = send_command(f"UPD {current_user} {title} {fname}")
    if not response.startswith("Upload ready"):
        print("Upload rejected:" + response)
        return
    try:
        with socket(AF_INET, SOCK_STREAM) as tcp:
            tcp.connect(SERVER_ADDRESS)
            tcp.sendall(f"UPD:{current_user}#{title}#{fname}\n".encode())
            with open(fname, "rb") as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    tcp.sendall(data)
            print(f"Sent '{fname}'")
            tcp.shutdown(SHUT_WR)
            confirm = tcp.recv(1024).decode()
            print(f"Server: " + confirm)
    except Exception as e:
        print("Upload failed: " + str(e))


def download_file(args):
    parts = args.split(" ", 1)
    if len(parts) != 2:
        print("Input with: DWN <thread> <file>")
        return
    title, fname = parts
    if os.path.exists(fname):
        print(f"Local file {fname} already exists")
        return
    response = send_command(f"DWN {current_user} {title} {fname}")
    if not response.startswith("Download ready"):
        print("Rejected: " + response)
        return
    try:
        with socket(AF_INET, SOCK_STREAM) as tcp:
            tcp.connect(SERVER_ADDRESS)
            tcp.sendall(f"DWN:{title}#{fname}\n".encode())
            with open(fname, "wb") as f:
                while True:
                    data = tcp.recv(1024)
                    if not data:
                        break
                    f.write(data)
                    print(f"Received '{fname}'")
    except Exception as e:
        print("Download failed: " + str(e))


def main():
    global is_client_running, current_user, udp_socket
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    udp_socket.bind(('', 0))
    udp_socket.settimeout(1.0)
    auth_user()
    cmd_list = {
        'XIT': (0, exit_forum),
        'CRT': (1, create_thread),
        'LST': (0, list_threads),
        'MSG': (2, post_message),
        'RDT': (1, read_thread),
        'EDT': (3, edit_message),
        'DLT': (2, delete_message),
        'RMV': (1, remove_thread),
        'UPD': (2, upload_file),
        'DWN': (2, download_file)
    }
    print("\n====== Input with CMD below ======")
    print("1. /XIT (no arguments) - Exit forum")
    print("2. /CRT <threadtitle> - Create thread title")
    print("3. /LST (no arguments) - List thread title")
    print("4. /MSG <threadtitle> <msg> - Post message")
    print("5. /RDT <threadtitle> - Read thread content")
    print("6. /EDT <threadtitle> <msg_num> <msg> - Edit message")
    print("7. /DLT <threadtitle> <msg_num> - Delete message")
    print("8. /RMV <threadtitle> - Remove thread")
    print("9. /UPD <threadtitle> <filename> - Upload file")
    print("X. /DWN <threadtitle> <filename> - Download file")
    print("===================================\n")
    is_client_running = True
    try:
        while is_client_running:
            raw = input(f"{current_user}> ").strip()
            if not raw:
                continue
            parts = raw.split(" ", 1)
            command = parts[0]
            if not command.isupper():
                print("ERROR: Commands must be UPPERCASE")
                continue
            cmd = command
            args = parts[1].strip() if len(parts) > 1 else ""
            if cmd not in cmd_list:
                print("ERROR: Invalid command.")
                continue
            req_args, func = cmd_list[cmd]
            if req_args == 0:
                if args:
                    print("ERROR: No arguments")
                    continue
                func()
            else:
                func(args)
    except KeyboardInterrupt:
        print("\nClosing client...")
    finally:
        if udp_socket:
            udp_socket.close()
            udp_socket = None
            print("Connection closed...")


if __name__ == "__main__":
    main()

# python server.py 8888
# python client.py 127.0.0.1 8888
