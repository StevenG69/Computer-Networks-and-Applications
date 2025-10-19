# Computer-Networks-and-Applications

# COMP9331 – Forum & File Sharing Application

> **Programming Language**: Python 3.13  
> **Platform**: Windows 11
---

## 🎯 Objective

Implement a **multi-user networked forum application** that supports:
- User authentication (login/registration)
- Thread and message management
- File upload and download

The system uses **UDP for command exchange** and **TCP for reliable file transfers**.

---

## 📡 Features Implemented

### 🔐 User Management (UDP)
- `login`: authenticate existing users  
- `register`: create new accounts  
- `exit`: log out from the forum

### 💬 Forum Operations (UDP)
- `create thread <title>`: create a new discussion thread  
- `list threads (LST)`: show all active threads  
- `read thread <title> (RDT)`: view all messages in a thread  
- `post message <title> <message>`: add a message to a thread  
- `edit message <title> <msg_no> <new_msg>`: modify an existing message  
- `delete message <title> <msg_no>`: remove a message  
- `remove thread <title> (RMV)`: delete a thread and all associated files

### 📤 File Transfer (TCP + UDP coordination)
- `upload file <title> <filename>`: upload a local file to a thread  
- `download file <title> <filename>`: download a file from a thread

---

## 🗃️ Data Structures Used

- `user_credentials`: `{username: password}`  
- `active_users`: `{username: (ip, port)}`  
- `thread_metadata`:  
  ```python
  {
    title: {
      "owner": str,
      "messages": list of {"user": str, "content": str},
      "files": list of filenames
    }
  }

Application Layer Protocol
Request–Response model over text-based commands
Workflow:
Client authenticates via UDP
Client sends command (e.g., MSG Hello!)
Server parses and executes operation
Server sends success/error response to client address
For file operations: client initiates TCP connection for actual transfer

Transport Layer Usage
Authentication & Forum Commands
UDP
File Upload / Download
TCP

Example Interaction

User A (Batman):
  CRT BvSScripts          → Thread BvSScripts created.
  MSG Do you bleed?       → Message posted.
  UPD BvSScripts doom.exe → UPLOAD_SUCCESS

User B (Superman):
  RDT BvSScripts          → 1 Batman: Do you bleed?
  DWN BvSScripts doom.exe → BvSScripts-doom.exe downloaded.

User A:
  RMV BvSScripts          → Thread and file removed.

Known Limitations
Code Structure: Heavy use of if-else chains → hard to maintain/debug
Error Handling: Limited input validation; split() may fail on malformed input
UDP Reliability: Basic retransmission logic; no ACK/sequence numbers or congestion control

How to Run
Server:
python3 server.py <port>
Client (run multiple instances):
python3 client.py 127.0.0.1 <port>

References
Python 3.13 Docs: os, threading, concurrent.futures, re
Batman v Superman: Dawn of Justice (for demo scenario inspiration 😄)
