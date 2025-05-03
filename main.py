import threading
from itertools import cycle
from enum import Enum, auto
from time import sleep
import pygame
import client
import host


class Mark(Enum):
    EMPTY = auto()
    X = auto()
    O = auto()


class GameState(Enum):
    PLAYING = auto()
    WAITING = auto()
    WON = auto()
    TIE = auto()


class GameType(Enum):
    HOST = auto()
    PLAYER = auto()
    SPECTATOR = auto()


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


def draw_mark(mark, rect):
    side = min(rect.height, rect.width)
    square = pygame.Rect(0, 0, side, side)
    square.center = rect.center
    match mark:
        case Mark.X:
            draw_x(square)
        case Mark.O:
            draw_o(square)


class Player:
    def __init__(self, name, mark):
        self.name = name
        self.mark = mark
        self.score = 0


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


class Board:
    def __init__(self):
        self.matrix = []
        self.empty_cells = []
        self.cell_pos = ()
        self.rectangles = self.create_rectangles()
        self.reset()

    def reset(self):
        self.draw_board()
        self.matrix = [[Mark.EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.empty_cells = [(i, j) for j in range(BOARD_SIZE) for i in range(BOARD_SIZE)]

    def place(self, row, column, mark):
        self.matrix[row][column] = mark
        self.empty_cells.remove((row, column))

    @staticmethod
    def create_rectangles():
        rectangles = []
        y = SCORE_TAB_HEIGHT+CELL_GAP
        for _ in range(BOARD_SIZE):
            x = CELL_GAP
            row = []
            for _ in range(BOARD_SIZE):
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                pygame.rect.Rect()
                row.append(rect)
                x += CELL_SIZE+CELL_GAP
            rectangles.append(row)
            y += CELL_SIZE+CELL_GAP

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

    def check_win(self, mark):
        lr_diagonal_win = True
        rl_diagonal_win = True
        tie = True
        for i in range(BOARD_SIZE):
            if self.matrix[i][i] != mark:
                lr_diagonal_win = False
            if self.matrix[i][BOARD_SIZE - (1+i)] != mark:
                rl_diagonal_win = False
            if self.matrix[i][0] == Mark.EMPTY and self.matrix[0][i] == Mark.EMPTY:
                continue
            row_win = True
            column_win = True
            for j in range(BOARD_SIZE):
                if self.matrix[i][j] == Mark.EMPTY:
                    tie = False
                if self.matrix[i][j] != mark:
                    row_win = False
                if self.matrix[j][i] != mark:
                    column_win = False
            if row_win:
                return GameState.WON
            elif column_win:
                return GameState.WON
        if lr_diagonal_win:
            return GameState.WON
        if rl_diagonal_win:
            return GameState.WON
        if tie:
            return GameState.TIE

        return GameState.PLAYING

    def draw_board(self):
        for row in range(BOARD_SIZE):
            for column in range(BOARD_SIZE):
                pygame.draw.rect(screen, (255, 255, 255), self.rectangles[row][column])

    def draw_mark(self, row, column):
        rect = self.rectangles[row][column]
        mark = self.matrix[row][column]
        draw_mark(mark, rect)


class Game:
    def __init__(self, gametype, room):
        self.board = Board()
        self.room = room
        players = [Player('Player 1', Mark.X), Player('Player 2', Mark.O)]
        self.players = cycle(players)
        self.score = ScoreTab(players)
        self.player = next(self.players)
        if gametype == GameType.HOST:
            self.game_state = GameState.PLAYING
        elif gametype == GameType.PLAYER:
            self.game_state = GameState.WAITING
            self.wait_move()

    def click(self, pos):
        if self.game_state != GameState.PLAYING:
            return
        if self.board.clicked(pos):
            row, column = self.board.get_cell()
            self.room.send_move(row, column)
            self.move(row, column)

    def move(self, row, column):
        self.board.place(row, column, self.player.mark)
        self.board.draw_mark(row, column)
        match self.board.check_win(self.player.mark):
            case GameState.WON:
                self.player.score += 1
                self.score.draw_score(self.player)
                sleep(0.5)
                self.board.reset()
            case GameState.TIE:
                self.board.reset()
            case GameState.PLAYING:
                self.game_state = GameState.WAITING
                self.player = next(self.players)
                self.wait_move()

    def wait_move(self):
        def waiting():
            row, column = self.room.wait_move()
            self.move(row, column)
            self.game_state = GameState.PLAYING
        threading.Thread(target=waiting, daemon=True).start()


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
if option == '1':
    room = host.HostRoom()
    game = Game(GameType.HOST, room)
    print('a')
if option == '2':
    room = host.ClientRoom()
    game = Game(GameType.PLAYER, room)
    print('b')


running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                game.click(pygame.mouse.get_pos())
    pygame.display.update()
    clock.tick(60)
