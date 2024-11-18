from socket import *
from threading import *
from select import *



class ServerTCP:
    def __init__(self, server_port):
        self.server_port = server_port
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        addr = gethostbyname(gethostname())
        self.server_socket.bind((addr, self.server_port))
        self.clients = dict()
        self.run_event = Event()
        self.handle_event = Event()
        self.server_socket.listen(5)
    

    def accept_client(self):
        client_socket = None
        try:
            readable, writeable, exceptional = select([self.server_socket], [], [], 0.1)
            if self.server_socket in readable:
                client_socket, client_addr = self.server_socket.accept()
                readable, writeable, exceptional = select([client_socket], [], [], 0.1)
                if client_socket in readable:
                    name = client_socket.recv(1024).decode()
                    if name in self.clients.values():
                        client_socket.send("Name already taken.".encode())
                        client_socket.close()
                        return False
                    else:
                        client_socket.send(f"Welcome {name}! [type \"exit\" to leave chatroom]".encode())
                        self.clients[client_socket] = name
                        self.broadcast(client_socket, "join")
                        return True
        except (KeyboardInterrupt):
            if client_socket:
                client_socket.close()
            raise
        except:
            if client_socket:
                client_socket.close()
            return False
    

    def close_client(self, client_socket):
        try:
            if client_socket in self.clients:
                del self.clients[client_socket]
                client_socket.close()
                return True
            else:
                return False
        except:
            return False
    

    def broadcast(self, client_socket_sent, message):
        client_name = self.clients[client_socket_sent]
        if message.lower() == "join":
            response = f"User {client_name} joined."
            print(response)
        elif message.lower() == "exit":
            response = f"User {client_name} left."
            print(response)
        else:
            response = f"{client_name}: {message}"
        
        num_clients = self.get_clients_number()
        client_list = list(self.clients.keys())
        for client in range(num_clients):
            if client_list[client] != client_socket_sent:
                client_list[client].send(response.encode())
    

    def shutdown(self):
        num_clients = self.get_clients_number()
        client_list = list(self.clients.keys())
        for client in range(num_clients):
            client_list[client].send("server-shutdown".encode())
            self.close_client(client_list[client])
        self.run_event.set()
        self.handle_event.set()
        self.server_socket.close()


    def get_clients_number(self):
        return len(self.clients)
    

    def handle_client(self, client_socket):
        while not self.handle_event.is_set():
            try:
                readable, writeable, exceptional = select([client_socket], [], [], 0.1)
                if client_socket in readable:
                    message = client_socket.recv(1024).decode()
                    if message.lower() == "exit":
                        self.broadcast(client_socket, "exit")
                        self.close_client(client_socket)
                        break
                    else:
                        self.broadcast(client_socket, message)
            except:
                self.close_client(client_socket)
                break


    def run(self):
        print("Server is running.")
        try:
            while not self.run_event.is_set():
                if self.accept_client() == True:
                    client_socket = list(self.clients.keys())[-1]
                    Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
            pass
        finally:
            print("Shutting down server.")
            self.shutdown()



class ClientTCP:
    def __init__(self, client_name, server_port):
        self.server_addr = gethostbyname(gethostname())
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.server_port = server_port
        self.client_name = client_name
        self.exit_run = Event()
        self.exit_receive = Event()


    def connect_server(self):
        self.client_socket.connect((self.server_addr, self.server_port))
        self.send(self.client_name)
        try:
            readable, writeable, exceptional = select([self.client_socket], [], [], 0.1)
            if self.client_socket in readable:
                response = self.client_socket.recv(1024).decode()
                print(response)
                if "Welcome" in response:
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False
    

    def send(self, text):
        self.client_socket.send(text.encode())
    

    def receive(self):
        while not self.exit_receive.is_set():
            try:
                readable, writeable, exceptional = select([self.client_socket], [], [], 0.1)
                if self.client_socket in readable:
                    message = self.client_socket.recv(1024).decode()
                    if message == "server-shutdown":
                        print("\rServer is shutting down.")
                        self.exit_run.set()
                        self.exit_receive.set()
                    else:
                        print(f"\r{message}\n{self.client_name}: ", end='', flush=True)
            except:
                self.client_socket.send("exit".encode())
                self.exit_run.set()
                self.exit_receive.set()
    

    def run(self):
        if self.connect_server() == True:
            try:
                Thread(target=self.receive, daemon=True).start()
                while not self.exit_run.is_set():
                    message = input(f"\r{self.client_name}: ")
                    if message.lower() == "exit":
                        self.client_socket.send("exit".encode())
                        self.exit_run.set()
                        self.exit_receive.set()
                        print("\rExiting server.")
                    else:
                        self.send(message)
            except KeyboardInterrupt:
                self.client_socket.send("exit".encode())
                self.exit_run.set()
                self.exit_receive.set()
                print("\rExiting server.")



class ServerUDP:
    def __init__(self, server_port):
        self.server_port = server_port
        self.server_socket = socket(AF_INET, SOCK_DGRAM)
        addr = gethostbyname(gethostname())
        self.server_socket.bind((addr, self.server_port))
        self.clients = dict()
        self.messages = []
    

    def accept_client(self, client_addr, message):
        name = message.split(": ")[0]
        if name in self.clients.values():
            self.server_socket.sendto("Name already taken.".encode(), client_addr)
            return False
        else:
            self.server_socket.sendto(f"Welcome {name}! [type \"exit\" to leave chatroom]".encode(), client_addr)
            self.clients[client_addr] = name
            response = f"User {name} joined."
            print(response)
            self.messages.append((response, client_addr))
            self.broadcast()
            return True
    

    def close_client(self, client_addr):
        try:
            name = self.clients[client_addr]
            del self.clients[client_addr]
            message = f"User {name} left."
            print(message)
            self.messages.append((message, client_addr))
            self.broadcast()
            return True
        except:
            return False
    

    def broadcast(self):
        if len(self.messages) > 0:
            message, client_addr = self.messages.pop(0)
            num_clients = self.get_clients_number()
            client_list = list(self.clients.keys())
            for client in range(num_clients):
                if client_list[client] != client_addr:
                    self.server_socket.sendto(message.encode(), client_list[client])
    

    def shutdown(self):
        num_clients = self.get_clients_number()
        client_list = list(self.clients.keys())
        for client in range(num_clients):
            self.server_socket.sendto("server-shutdown".encode(), client_list[client])
            del self.clients[client_list[client]]
        self.server_socket.close()
    

    def get_clients_number(self):
        return len(self.clients)
    

    def run(self):
        print("Server is running.")
        try:
            while True:
                readable, writeable, exceptional = select([self.server_socket], [], [], 0.1)
                if self.server_socket in readable:
                    message, client_addr = self.server_socket.recvfrom(1024)
                    decoded_message = message.decode()
                    if decoded_message.split(": ")[1] == "join":
                        self.accept_client(client_addr, decoded_message)
                    elif decoded_message.split(": ")[1] == "exit":
                        self.close_client(client_addr)
                    else:
                        self.messages.append((decoded_message, client_addr))
                        self.broadcast()
        except:
            print("Shutting down server.")
            self.shutdown()



class ClientUDP:
    def __init__(self, client_name, server_port):
        self.server_addr = gethostbyname(gethostname())
        self.client_socket = socket(AF_INET, SOCK_DGRAM)
        self.server_port = server_port
        self.client_name = client_name
        self.exit_run = Event()
        self.exit_receive = Event()
    

    def connect_server(self):
        self.send("join")
        try:
            readable, writeable, exceptional = select([self.client_socket], [], [], 0.1)
            if self.client_socket in readable:
                response, client_addr = self.client_socket.recvfrom(1024)
                decoded_response = response.decode()
                print(decoded_response)
                if "Welcome" in decoded_response:
                    return True
                else:
                    return False
        except:
            return False
    

    def send(self, text):
        message = f"{self.client_name}: {text}"
        self.client_socket.sendto(message.encode(), (self.server_addr, self.server_port))
    

    def receive(self):
        while not self.exit_receive.is_set():
            try:
                readable, writeable, exceptional = select([self.client_socket], [], [], 0.1)
                if self.client_socket in readable:
                    message, client_addr = self.client_socket.recvfrom(1024)
                    decoded_message = message.decode()
                    if decoded_message == "server-shutdown":
                        print("\rServer is shutting down.")
                        self.exit_run.set()
                        self.exit_receive.set()
                    else:
                        print(f"\r{decoded_message}\n{self.client_name}: ", end='', flush=True)
            except Exception as e:
                print(e)
                self.exit_run.set()
                self.exit_receive.set()
    

    def run(self):
        if self.connect_server() == True:
            try:
                Thread(target=self.receive, daemon=True).start()
                while not self.exit_run.is_set():
                    message = input(f"\r{self.client_name}: ")
                    self.send(message)
                    if message.lower() == "exit":
                        self.exit_run.set()
                        self.exit_receive.set()
                        print("\rExiting server.")
            except:
                self.send("exit")
                self.exit_run.set()
                self.exit_receive.set()
                print("\rExiting server.")