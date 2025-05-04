import socket
import time
import json
import threading
from time import sleep
from board import Board, GameState
from random import sample


PORT = 8765
HOST = socket.gethostbyname(socket.gethostname())
BROADCASTING_ADDRESS = '255.255.255.255'
ack_message = json.dumps({'type': 'ack'}).encode()
close_message = json.dumps({'type': 'close'}).encode()
turn_message = json.dumps({'type': 'turn'}).encode()
tie_message = json.dumps({'type': 'tie'}).encode()


class Room:
    def __init__(self, conn=None):
        self.connection = conn
        self.connection.settimeout(1.0)
        self.on_move = None
        self.on_chat = None
        self.on_turn = None
        self.on_match = None
        self.on_win = None
        self.on_tie = None
        self.active = True
        threading.Thread(target=self.listener).start()

    def listener(self):
        while self.active:
            try:
                data = self.connection.recv(1024).decode()
                messages = data.split('\n')[:-1]
            except socket.timeout:
                continue
            except ConnectionResetError:
                messages = [{'type': 'close'}]
            for message in messages:
                message = json.loads(message)
                if message['type'] == 'move':
                    self.on_move(message['row'], message['column'])
                elif message['type'] == 'chat':
                    self.on_chat(message['nickname'], message['content'])
                elif message['type'] == 'turn':
                    self.on_turn()
                elif message['type'] == 'match':
                    self.on_match(message['x'], message['o'], message['first'])
                elif message['type'] == 'win':
                    self.on_win(message['winner'])
                elif message['type'] == 'tie':
                    self.on_tie()
                elif message['type'] == 'close':
                    self.connection.close()
                    self.active = False

    def send_move(self, row, column):
        self.connection.sendall(create_move_message(row, column))

    def send_chat(self, content):
        self.connection.sendall(create_chat_message(content))

    def close(self):
        if self.active:
            self.active = False
            self.connection.sendall(close_message)


class HostRoom:
    def __init__(self, room_name):
        self.room_name = room_name
        self.broadcasting = True
        self.active = True
        self.clients = []
        self.nicknames = {}
        self.move_history = []
        self.board = Board()
        self.hoster = None
        self.players = []
        self.turn = 1
        self.players_nicknames = []
        self.count = 3
        threading.Thread(target=self.broadcast).start()
        threading.Thread(target=self.host).start()

    def register_client(self, conn, nickname):
        self.clients.append(conn)
        self.nicknames[conn] = nickname
        if len(self.clients) == 1:
            self.hoster = conn
        elif len(self.clients) == 2:
            sleep(1)
            self.start_match(self.turn)

    def random_match(self):
        self.players = sample(self.clients, 2)
        self.relay(create_match_message(self.nicknames[self.players[0]], self.nicknames[self.players[1]]))
        self.move_history.append(
            create_match_message(self.nicknames[self.players[0]], self.nicknames[self.players[1]]))
        self.send_turn()

    def rematch(self, first):
        self.relay(create_match_message(self.nicknames[self.players[0]], self.nicknames[self.players[1]], first))
        self.move_history.append(create_match_message(self.nicknames[self.players[0]], self.nicknames[self.players[1]], first))
        self.send_turn()

    def start_match(self, first):
        self.move_history.clear()
        self.board.reset()
        if self.count == 3:
            self.count = 0
            self.random_match()
        else:
            self.rematch(first)
            self.count += 1

    def send_turn(self):
        self.players[self.turn-1].sendall(turn_message+'\n'.encode())

    def next_turn(self):
        self.turn += 1
        if self.turn == 3:
            self.turn = 1

    def host(self):
        print(f'[STARTING]Starting server at {HOST}')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.settimeout(1.0)
            s.bind((HOST, PORT))
            s.listen()
            while self.active:
                try:
                    conn, _ = s.accept()
                except socket.timeout:
                    continue
                message = json.loads(conn.recv(1024).decode())
                if message['type'] == 'enter' and message['room'] == self.room_name:
                    conn.sendall(ack_message)
                    print(f"[CONNECTION]{message['nickname']} connected to server")
                    if self.move_history:
                        conn.sendall('\n'.encode().join(self.move_history) + '\n'.encode())
                    self.register_client(conn, message['nickname'])
                    threading.Thread(target=self.listener, args=(conn,)).start()

    def broadcast(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            message = create_broadcasting_message(self.room_name)
            while self.broadcasting:
                s.sendto(message, (BROADCASTING_ADDRESS, PORT))
                time.sleep(2)

    def listener(self, conn):
        conn.settimeout(1.0)
        while self.active:
            try:
                data = conn.recv(1024)
                message = json.loads(data.decode())
            except ConnectionResetError:
                message = {'type': 'close'}
            except socket.timeout:
                continue
            if message['type'] == 'move':
                if conn == self.players[self.turn-1]:
                    self.move_history.append(data)
                    self.relay(data)
                    self.handle_move(message['row'], message['column'])
            elif message['type'] == 'chat':
                message['nickname'] = self.nicknames[conn]
                self.relay((json.dumps(message)).encode())
            elif message['type'] == 'close':
                if conn == self.hoster:
                    self.relay(close_message)
                    self.active = False
                    self.broadcasting = False
                break

    def handle_move(self, row, column):
        self.board.place(row, column, self.turn)
        match self.board.check_win(self.turn):
            case GameState.WON:
                self.relay(create_win_message(self.nicknames[self.players[self.turn-1]]))
                self.start_match(self.turn)
            case GameState.TIE:
                self.relay(tie_message)
                self.next_turn()
                self.start_match(self.turn)
            case GameState.PLAYING:
                self.next_turn()
                self.send_turn()

    def relay(self, data):
        for client in self.clients:
            client.sendall(data+'\n'.encode())


def find_rooms():
    rooms = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("", PORT))
        while True:
            data = s.recv(1024)
            message = json.loads(data.decode())
            if message['type'] == 'advertisement':
                rooms[message['room']] = message['host'], message['port']
                print(f"[ROOM] {message['room']}")
                return rooms

def enter_room(room_name, nickname):
    rooms = find_rooms()
    if room_name not in rooms:
        print('[ERROR]Room Not Found')
        return
    host, port = rooms[room_name]
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((host, port))
    conn.sendall(create_entering_message(room_name, nickname))
    response = json.loads(conn.recv(1024).decode())
    if response['type'] == 'ack':
        print(f'[JOINED]You joined {room_name}')
        return Room(conn)
    else:
        conn.close()
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

def create_entering_message(room_name, nickname):
    msg = {
        'type': 'enter',
        'room': room_name,
        'nickname': nickname
    }
    return json.dumps(msg).encode()

def create_chat_message(content):
    msg = {
        'type': 'chat',
        'content': content
    }
    return json.dumps(msg).encode()

def create_match_message(x, o, first=1):
    msg = {
        'type': 'match',
        'x': x,
        'o': o,
        'first': first
    }
    return json.dumps(msg).encode()

def create_win_message(winner):
    msg = {
        'type': 'win',
        'winner': winner
    }
    return json.dumps(msg).encode()