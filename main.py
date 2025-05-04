import pygame
import host
from board import Board


def draw_x(rect):
    side = rect.height
    offset = int(side * 0.2)
    thickness = int(side * 0.2)
    pygame.draw.line(screen, 'black', (rect.left + offset, rect.top + offset),
                     (rect.right - offset, rect.bottom - offset), thickness)
    pygame.draw.line(screen, 'black', (rect.right - offset, rect.top + offset),
                     (rect.left + offset, rect.bottom - offset), thickness)


def draw_o(rect):
    upscale = 4
    width, height = rect.size
    circle_surface = pygame.Surface((width*upscale, height*upscale), pygame.SRCALPHA)
    outer_radius = int(width * (upscale//2-0.2))
    thickness = int(outer_radius * 0.21)
    pygame.draw.circle(circle_surface, (255, 0, 0),
                       (width*(upscale//2),
                        height*(upscale//2)),
                       outer_radius, thickness)
    downscaled = pygame.transform.smoothscale(circle_surface, (width, height))
    screen.blit(downscaled, rect)


def draw_mark(mark, rectangle):
    side = min(rectangle.height, rectangle.width)
    square = pygame.Rect(0, 0, side, side)
    square.center = rectangle.center
    match mark:
        case 1:
            draw_x(square)
        case 2:
            draw_o(square)


class ClientBoard(Board):
    def __init__(self):
        self.rectangles = self.create_rectangles()
        self.cell_pos = (-1,-1)
        super().__init__()

    def reset(self):
        super().reset()
        self.draw_board()

    @staticmethod
    def create_rectangles():
        rectangles = []
        y = SCORE_TAB_HEIGHT + CELL_GAP
        for _ in range(BOARD_SIZE):
            x = CELL_GAP
            row = []
            for _ in range(BOARD_SIZE):
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                pygame.rect.Rect()
                row.append(rect)
                x += CELL_SIZE + CELL_GAP
            rectangles.append(row)
            y += CELL_SIZE + CELL_GAP

        return rectangles

    def clicked(self, pos):
        for index, (row, column) in enumerate(self.empty_cells):
            rectangle = self.rectangles[row][column]
            if rectangle.collidepoint(pos):
                self.cell_pos = (row, column)
                return True
        return False

    def get_cell(self):
        return self.cell_pos

    def draw_board(self):
        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                pygame.draw.rect(screen, (255, 255, 255), self.rectangles[row][column])

    def draw_mark(self, row, column):
        rect = self.rectangles[row][column]
        mark = self.matrix[row][column]
        draw_mark(mark, rect)


class ScoreTab:
    def __init__(self, players):
        self.font = pygame.font.Font(size=40)
        self.players = players
        self.mark_rects = []
        self.score_rects = []
        portion = SCREEN_WIDTH//(len(players)*4)
        for x in range(portion, portion*7, portion*3):
            icon_rect = pygame.Rect(x, 0, portion, SCORE_TAB_HEIGHT)
            score_rect = pygame.Rect(x+portion, 0, portion, SCORE_TAB_HEIGHT)
            self.mark_rects.append(icon_rect)
            self.score_rects.append(score_rect)
        self.draw()

    def draw_score(self, player):
        player_id = self.players.index(player)
        score_surface = self.font.render(str(player.score), True, 'black', 'white')
        screen.blit(score_surface, score_surface.get_rect(center=self.score_rects[player_id].center))

    def draw(self):
        for player, icon_rect, score_rect in zip(self.players, self.mark_rects, self.score_rects):
            pygame.draw.rect(screen, (255, 255, 255), icon_rect)
            draw_mark(player.mark, icon_rect)
            pygame.draw.rect(screen, (255, 255, 255), score_rect)
            self.draw_score(player)


class Client:
    def __init__(self, room):
        self.board = ClientBoard()
        self.room = room
        self.my_turn = False
        self.current_turn = 0
        self.message = ''

        self.room.on_turn = self.turn
        self.room.on_move = self.move
        self.room.on_chat = self.show_chat
        self.room.on_match = self.match
        self.room.on_win = self.win
        self.room.on_tie = self.tie

    def win(self, winner):
        print(winner)

    def tie(self):
        print('tie')

    def match(self, player1, player2, first):
        self.board.reset()
        print(f'[MATCH]{player1} Vs. {player2}')
        self.current_turn = first

    def turn(self):
        self.my_turn = True

    def click(self, pos):
        if not self.my_turn:
            return
        if self.board.clicked(pos):
            self.my_turn = False
            row, column = self.board.get_cell()
            self.room.send_move(row, column)

    def write_chat(self, letter):
        self.message += letter

    def send_chat(self):
        room.send_chat(self.message)
        self.message = ''

    def show_chat(self, nick, content):
        print(f'[CHAT]{nick}: {content}')

    def move(self, row, column):
        self.board.place(row, column, self.current_turn)
        self.board.draw_mark(row, column)
        self.current_turn += 1
        if self.current_turn == 3:
            self.current_turn = 1


SCORE_TAB_HEIGHT = 30
SCREEN_WIDTH = 300
BOARD_SIZE = 3
CELL_GAP = 5
CELL_SIZE = (SCREEN_WIDTH-(CELL_GAP*BOARD_SIZE-1))//BOARD_SIZE
SCREEN_HEIGHT = SCREEN_WIDTH+SCORE_TAB_HEIGHT
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

option = input('1-HOST\n2-ENTER ROOM\nSELECT AN OPTION: ')
room_name = input('Enter The Room Name: ')
nick = input('Enter Your Nickname: ')
if option == '1':
    host.HostRoom(room_name)
    room = host.enter_room(room_name, nick)
    game = Client(room)
if option == '2':
    room = host.enter_room(room_name, nick)
    game = Client(room)


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.unicode.isalpha():
                game.write_chat(event.unicode)
            if event.key == pygame.K_RETURN:
                game.send_chat()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                game.click(pygame.mouse.get_pos())
    pygame.display.update()
    clock.tick(60)
pygame.quit()
room.close()