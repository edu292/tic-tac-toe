import asyncio
import socket
import time
import json
import threading

PORT = 8765
HOST = socket.gethostbyname(socket.gethostname())
BROADCASTING_ADDRESS = '255.255.255.255'
ack_message = json.dumps({'type': 'ack'}).encode()


class Room:
    def __init__(self, conn=None):
        self.connection = conn

    def wait_move(self):
        message = json.loads(self.connection.recv(1024).decode())
        print(message)
        if message['type'] == 'move':
            return message['row'], message['column']

    def send_move(self, row, column):
        self.connection.sendall(create_move_message(row, column))


class HostRoom(Room):
    def __init__(self):
        super().__init__()
        self.room_name = input('Enter the Room Name: ')
        threading.Thread(target=self.host, daemon=True).start()
        self.broadcasting = True
        threading.Thread(target=self.broadcast, daemon=True).start()

    def host(self):
        print(f'[STARTING]Starting server at {HOST}')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            conn, adr = s.accept()
            self.connection = conn
            print(f'[CONNECTION]{adr[0]} connected to server')
            message = json.loads(conn.recv(1024).decode())
            if message['type'] == 'enter' and message['room'] == self.room_name:
                conn.sendall(ack_message)

    def broadcast(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            message = create_broadcasting_message(self.room_name)
            while self.broadcasting:
                s.sendto(message, (BROADCASTING_ADDRESS, PORT))
                time.sleep(2)


class ClientRoom(Room):
    def __init__(self):
        self.rooms = {}
        self.find_rooms()
        s = self.enter_room()
        time.sleep(3)
        super().__init__(s)

    def find_rooms(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(("", PORT))
            while True:
                data = s.recv(1024)
                message = json.loads(data.decode())
                if message['type'] == 'advertisement':
                    self.rooms[message['room']] = message['host'], message['port']
                    print(f"[ROOM] {message['room']}")
                    break

    def enter_room(self):
        room_name = input('Enter the room name: ')
        if room_name not in self.rooms:
            print('[ERROR]Room Not Found')
            return
        host, port = self.rooms[room_name]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.sendall(create_entering_message(room_name))
        response = json.loads(s.recv(1024).decode())
        if response['type'] == 'ack':
            print(f'[JOINED]You joined {room_name}')
            return s
        else:
            s.close()
            print('[ERROR]Failed to join')


def create_broadcasting_message(room_name):
    msg = {
        'type': 'advertisement',
        'room': room_name,
        'host': HOST,
        'port': PORT
    }
    return json.dumps(msg).encode()


def create_move_message(row, column):
    msg = {
        'type': 'move',
        'row': row,
        'column': column
    }
    return json.dumps(msg).encode()

def create_entering_message(room_name):
    msg = {
        'type': 'enter',
        'room': room_name
    }
    return json.dumps(msg).encode()