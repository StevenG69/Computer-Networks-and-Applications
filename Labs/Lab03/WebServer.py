from socket import *
import sys

if len(sys.argv) != 2:
    print("Usage: python3 WebServer.py <port>")
    sys.exit(1)

serverPort = int(sys.argv[1])

if serverPort in {80, 8080} or serverPort < 1024:
    print("Please change to a different port number.")
    sys.exit(1)

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(('localhost', serverPort))
serverSocket.listen(1)
print(f"Server is ready! Running on http://127.0.0.1:{serverPort}/")

while True:
    connectionSocket, addr = serverSocket.accept()
    try:
        request = connectionSocket.recv(1024).decode()
        if not request:
            continue
        fileName = request.split()[1][1:]

        try:
            with open(fileName, 'rb') as file:
                response = file.read()
            if fileName.endswith('.jpeg') or fileName.endswith('.jpg'):
                contentType = 'image/jpeg'
            elif fileName.endswith('.html'):
                contentType = 'text/html'
            else:
                contentType = 'application/octet-stream'

            headers = f"HTTP/1.1 200 OK\r\nContent-Type: {contentType}\r\n\r\n"
            connectionSocket.send(headers.encode())
            connectionSocket.send(response)
            print(f"{fileName} sent successfully!")

        except FileNotFoundError:
            print("404 File Not Found")
            error_message = "<html><h1>404 File Not Found</h1><p>"
            headers = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n"
            connectionSocket.send(headers.encode())
            connectionSocket.send(error_message.encode())

    finally:
        connectionSocket.close()