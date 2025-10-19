"""
"server.py"
Forum Application Server
Usage: python3 server.py SERVER_PORT
"""

from socket import *
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
import sys
import time
import os
import re

if len(sys.argv) != 2:
    print("=== Usage: python3 server.py SERVER_PORT ===")
    exit(1)
# Server configuration
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])

# Locks for shared data, Thread synchronization
user_lock = Lock()
thread_lock = Lock()
executor = ThreadPoolExecutor(max_workers=5)
# Data structures
user_credentials = {}  # {username: password}
active_users = {}  # {username: client_address}
thread_metadata = {}  # {title: {"owner": str, "messages": list, "files": list}}
# Sockets, File handling
udpSocket = None
tcpSocket = None
CREDENTIALS_FILE = "credentials.txt"


def load_credentials():
    global user_credentials
    print(f"Loading credentials from '{CREDENTIALS_FILE}'...")
    with open(CREDENTIALS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                name, pwd = line.split(" ", 1)
                user_credentials[name] = pwd
    print(f"*Loaded {len(user_credentials)} user credentials")


def save_credentials():
    global user_credentials
    with open(CREDENTIALS_FILE, "w") as f:
        for user, pwd in user_credentials.items():
            f.write(f"{user} {pwd}\n")
    print(f"*Credentials saved to '{CREDENTIALS_FILE}'...")


def load_threads():
    global thread_metadata
    print("Loading existing threads...")
    for fname in os.listdir():
        if ("." in fname or "_" in fname):
            continue
        if os.path.isfile(fname):
            with open(fname, "r") as f:
                owner = f.readline().strip()
            thread_metadata[fname] = {
                "owner": owner, "messages": [], "files": []}
    print(f"*Loaded {len(thread_metadata)} threads")


def get_username(client_address):
    with user_lock:
        for user, addr in active_users.items():
            if addr == client_address:
                return user
    return None


def login_user(args, client_addr):
    username = args
    if not username:
        print("*ERROR: Username empty")
        return "ERROR: Username empty"
    with user_lock:
        if username in active_users and active_users[username] != client_addr:
            addr = active_users[username]
            print(f"*ERROR: User {username} already active at {addr}")
            return f"ERROR: User {username} already active at {addr}"
    if username in user_credentials:
        return "PASSWORD_REQUIRED"
    return "NEW_USER"


def auth_user(args, client_addr):
    username, password = args.split(" ", 1)
    if user_credentials.get(username) != password:
        print("*ERROR: Invalid password")
        return "ERROR: Invalid password"
    with user_lock:
        if username in active_users and active_users[username] != client_addr:
            print(f"*ERROR: User {username} already active")
            return f"ERROR: User {username} already active"
        active_users[username] = client_addr
    return "Login successful"


def reg_user(args, client_addr):
    username, password = args.split(" ", 1)
    if " " in username:
        print("*ERROR: Username can not have spaces")
        return "ERROR: Username can not have spaces"
    if username in user_credentials:
        print("*ERROR: Username already exists")
        return "ERROR: Username already exists"
    user_credentials[username] = password
    save_credentials()
    with user_lock:
        active_users[username] = client_addr
    return "Registration successful"


def exit_forum(req_user):
    with user_lock:
        if req_user not in active_users:
            print(f"*ERROR: Logout failed for {req_user}")
            return "ERROR: Logout failed"
        del active_users[req_user]
    print(f"*Goodbye {req_user}!")
    return f"Goodbye {req_user}!"


def create_thread(args, req_user):
    _, threadtitle = args.split(" ", 1)
    threadtitle = threadtitle.strip()
    if not threadtitle:
        print("*ERROR: Empty title")
        return "ERROR: Empty title"
    if " " in threadtitle:
        print("*ERROR: Title have to be single word")
        return "ERROR: Title have to be single word"
    with thread_lock:
        if threadtitle in thread_metadata:
            print(f"*ERROR: Thread {threadtitle} already created")
            return f"ERROR: Thread {threadtitle} already created"
        with open(threadtitle, "w") as f:
            f.write(f"{req_user}\n")
        thread_metadata[threadtitle] = {
            "owner": req_user, "messages": [], "files": []}
    print(f"*Thread '{threadtitle}' created by '{req_user}'")
    return f"Thread {threadtitle} created"


def list_threads():
    with thread_lock:
        if not thread_metadata:
            print("*ERROR: No threads")
            return "ERROR: No threads"
        return "All threads showed below:\n" + "\n".join(thread_metadata.keys())


def post_message(args, req_user):
    msg_parts = args.split(" ", 2)
    if len(msg_parts) != 3:
        print("*ERROR: Invalid MSG input")
        return "*ERROR: Invalid MSG input"
    _, threadtitle, message = msg_parts
    if not threadtitle or " " in threadtitle:
        print("*ERROR: Invalid title")
        return "ERROR: Invalid title"
    if not message:
        print("*ERROR: Empty message")
        return "ERROR: Empty message"
    with thread_lock:
        if threadtitle not in thread_metadata:
            print(f"*ERROR: Thread {threadtitle} not found")
            return f"ERROR: Thread {threadtitle} not found"
        msg_count = 0
        with open(threadtitle, "r") as f:
            lines = f.readlines()
        for line in lines[1:]:
            msg_line = line.strip()
            if re.match(r"^\d+ .+?: ", msg_line):
                msg_count += 1
        next_msg_num = msg_count + 1
        with open(threadtitle, "a") as f:
            f.write(f"{next_msg_num} {req_user}: {message}\n")
    print(f"*{message} posted by {req_user}")
    return "Message posted"


def read_thread(args):
    threadtitle = args.strip()
    if not threadtitle:
        print("*ERROR: Title required")
        return "ERROR: Title required"
    if " " in threadtitle:
        print("*ERROR: Title must be single word")
        return "ERROR: Title must be single word"
    with thread_lock:
        if threadtitle not in thread_metadata:
            print(f"*ERROR: Thread {threadtitle} not found")
            return f"ERROR: Thread {threadtitle} not found"
        with open(threadtitle, "r") as f:
            lines = f.readlines()
    if len(lines) <= 1:
        print("*Thread is empty")
        return "Thread is empty"
    content = "".join(lines[1:])
    print(f"*Sending contents of '{threadtitle}'")
    return content


def edit_message(args, req_user):
    edt_parts = args.split(" ", 3)
    if len(edt_parts) != 4:
        print("*ERROR: Invalid EDT input")
        return "ERROR: Invalid EDT input"
    _, threadtitle, msg_num_str, new_msg = edt_parts
    if not threadtitle or " " in threadtitle:
        print("*ERROR: Invalid threadtitle")
        return "ERROR: Invalid threadtitle"
    try:
        msg_num = int(msg_num_str)
        if msg_num < 1:
            raise ValueError
    except ValueError:
        print("*ERROR: No message number")
        return "ERROR: No message number"
    with thread_lock:
        if threadtitle not in thread_metadata:
            print(f"*ERROR: Thread {threadtitle} can not be found")
            return f"ERROR: Thread {threadtitle} can not be found"
        lines = []
        with open(threadtitle, "r") as f:
            lines = f.readlines()
        msg_count = 0
        line_index = -1
        for index, line in enumerate(lines[1:]):
            msg_index = index + 1
            msg_line = line.strip()
            if re.match(r"^\d+ .+?: ", msg_line):
                msg_count += 1
                if msg_count == msg_num:
                    line_index = msg_index
                    break
        if line_index == -1:
            print("*ERROR: No message number")
            return "ERROR: No message number"
        line_content = lines[line_index].strip()
        if f"{msg_num} {req_user}:" not in line_content:
            print("*ERROR: You can only edit your own message")
            return "ERROR: You can only edit your own message"
        lines[line_index] = f"{msg_num} {req_user}: {new_msg}\n"
        with open(threadtitle, "w") as f:
            f.writelines(lines)
        print(f"*Message updated {msg_num} to {threadtitle}")
        return "Message updated"


def delete_message(args, req_user):
    parts = args.split(" ", 2)
    if len(parts) != 3:
        print("*ERROR: Invalid DLT input")
        return "ERROR: Invalid DLT input"
    _, threadtitle, msg_num_str = parts
    if not threadtitle or " " in threadtitle:
        print("*ERROR: Invalid thread title")
        return "ERROR: Invalid thread title"
    try:
        msg_num = int(msg_num_str)
        if msg_num < 1:
            raise ValueError
    except ValueError:
        print("*ERROR: No message number")
        return "ERROR: No message number"
    with thread_lock:
        if threadtitle not in thread_metadata:
            print(f"*ERROR: Thread {threadtitle} not exist")
            return f"ERROR: Thread {threadtitle} not exist"
        lines = []
        with open(threadtitle, "r") as f:
            lines = f.readlines()
        msg_count = 0
        line_index = -1
        for index, line in enumerate(lines[1:]):
            msg_index = index + 1
            msg_line = line.strip()
            if re.match(r"^\d+ .+?: ", msg_line):
                msg_count += 1
                if msg_count == msg_num:
                    line_index = msg_index
                    break
        if line_index == -1:
            print("*ERROR: No message number")
            return "ERROR: No message number"
        line_content = lines[line_index].strip()
        if f"{msg_num} {req_user}:" not in line_content:
            print("*ERROR: You can only delete your own message")
            return "ERROR: You can only delete your own message"
        del lines[line_index]
        for i in range(line_index, len(lines)):
            parts = lines[i].split(": ", 1)
            if len(parts) == 2:
                user_part = parts[0].split(" ", 1)[-1]
                lines[i] = f"{i - 1} {user_part}: {parts[1]}"
        with open(threadtitle, "w") as f:
            f.writelines(lines)
        print(f"*Deleted message {msg_num} from {threadtitle}")
        return "Message deleted"


def remove_thread(args, req_user):
    try:
        _, threadtitle = args.split(" ", 1)
    except ValueError:
        print("*ERROR: Invalid RMV input")
        return "ERROR: Invalid RMV input"
    with thread_lock:
        if threadtitle not in thread_metadata:
            print(f"*ERROR: Thread {threadtitle} not exist")
            return f"ERROR: Thread {threadtitle} not exist"
        with open(threadtitle, "r") as f:
            creator = f.readline().strip()
        if creator != req_user:
            print("*ERROR: You can only remove your own thread")
            return "ERROR: You can only remove your own thread"
        rmv_count = 0
        files_found = False
        prefix = f"{threadtitle}-"
        for fname in os.listdir('.'):
            if fname.startswith(prefix) and os.path.isfile(fname):
                files_found = True
                os.remove(fname)
                rmv_count += 1
                print(f"*Removed file: {fname}")
        if files_found == True:
            os.remove(threadtitle)
            del thread_metadata[threadtitle]
            print(
                f"*Thread {threadtitle} and {rmv_count} related file(s) removed")
        return "Thread and related files removed"


def process_udp_request(data, client_addr):
    message = data.decode().strip()
    parts = message.split(" ", 1)
    command = parts[0].upper()
    args = parts[1] if len(parts) > 1 else ""
    req_user = get_username(client_addr)
    print(f"@UDP - {command} from {client_addr} by (User: {req_user})")
    if command == "LOGIN":
        return login_user(args, client_addr)
    elif command == "AUTH":
        return auth_user(args, client_addr)
    elif command == "REGISTER":
        return reg_user(args, client_addr)
    elif command == "XIT":
        return exit_forum(req_user)
    elif command == "CRT":
        return create_thread(args, req_user)
    elif command == "LST":
        return list_threads()
    elif command == "MSG":
        return post_message(args, req_user)
    elif command == "RDT":
        return read_thread(args)
    elif command == "EDT":
        return edit_message(args, req_user)
    elif command == "DLT":
        return delete_message(args, req_user)
    elif command == "RMV":
        return remove_thread(args, req_user)
    elif command == "UPD":
        _, threadtitle, filename = args.split(" ", 2)
        if threadtitle not in thread_metadata:
            return f"ERROR: Thread '{threadtitle}' not exist"
        if filename in thread_metadata[threadtitle]["files"]:
            return f"ERROR: File '{filename}' already exists"
        return "Upload ready"
    elif command == "DWN":
        print(f"*Download ready {args}")
        return f"Download ready {args}"
    else:
        print("*ERROR: Unknown command")
        return "ERROR: Unknown command"


def udp_server():
    udpSocket = socket(AF_INET, SOCK_DGRAM)
    udpSocket.bind(("", serverPort))
    print(f"@UDP Server listening on port {serverPort}...")
    try:
        while True:
            data, clientAddress = udpSocket.recvfrom(4096)
            # response = process_udp_request(data, clientAddress)
            # if response:
            # udpSocket.sendto(response.encode(), clientAddress)
            executor.submit(process_udp_request_sync,
                            udpSocket, data, clientAddress)
    except KeyboardInterrupt:
        print("@UDP server shutting down")
    finally:
        if udpSocket:
            udpSocket.close()
            print("@UDP socket closed.")

def process_udp_request_sync(socket, data, clientAddress):
    response = process_udp_request(data, clientAddress)
    socket.sendto(response.encode(), clientAddress)

def tcp_server():
    tcpSocket = socket(AF_INET, SOCK_STREAM)
    tcpSocket.bind(("", serverPort))
    tcpSocket.listen(5)
    print(f"@TCP Server listening on port {serverPort}...")
    while True:
        conn, addr = tcpSocket.accept()
        transfer_thread = Thread(
            target=file_transfer, args=(conn, addr), daemon=True)
        transfer_thread.start()
        if tcpSocket:
            tcpSocket.close()
            print("@TCP socket closed.")


def file_transfer(conn, addr):
    print(f"@TCP - Connection from {addr}")
    try:
        header = b""
        while b"\n" not in header:
            part = conn.recv(1)
            if not part:
                return
            header += part
        header = header.decode().strip()
        if header.startswith("UPD:"):
            uname, title, fname = header[4:].split("#", 2)
            print(uname)
            full_name = f"{title}-{fname}"
            if os.path.exists(full_name):
                conn.sendall(b"ERROR: File already exists in thread")
                return
            with open(full_name, "wb") as f:
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
                    f.write(data)
            with open(title, "a") as thread_file:
                thread_file.write(f"{uname} uploaded {fname}\n")
            thread_metadata[title]["files"].append(fname)
            print(f"@UPD - {fname} saved to {title}")
            conn.sendall(b"UPLOAD_SUCCESS")
        elif header.startswith("DWN:"):
            title, fname = header[4:].split("#", 1)
            full_name = f"{title}-{fname}"
            if os.path.exists(full_name):
                with open(full_name, "rb") as f:
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        conn.sendall(data)
                print(f"@DWN - Sent {full_name} from {title}")
            else:
                conn.sendall(b"FILE_NOT_FOUND")
    except Exception as e:
        print(f"@TCP Error - {str(e)}")
    finally:
        conn.close()


def start_server():
    print("=== Starting server... ===")
    load_credentials()
    load_threads()
    udpThread = Thread(target=udp_server, daemon=True)
    udpThread.start()
    tcpThread = Thread(target=tcp_server, daemon=True)
    tcpThread.start()
    print("Server started. Press Ctrl+C to shut down.")
    try:
        while True:
            time.sleep(7200)
    except KeyboardInterrupt:
        print("\nShutting down server...")


if __name__ == "__main__":
    start_server()

# python server.py 8888
# python client.py 127.0.0.1 8888
