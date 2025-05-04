from enum import Enum, auto

class GameState(Enum):
    WON = auto()
    TIE = auto()
    PLAYING = auto()

BOARD_SIZE = 3


class Board:
    def __init__(self):
        self.matrix = []
        self.empty_cells = []
        self.reset()

    def reset(self):
        self.matrix = [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.empty_cells = [(i, j) for j in range(BOARD_SIZE) for i in range(BOARD_SIZE)]

    def place(self, row, column, mark):
        self.matrix[row][column] = mark
        self.empty_cells.remove((row, column))

    def check_win(self, mark):
        lr_diagonal_win = True
        rl_diagonal_win = True
        tie = True
        for i in range(BOARD_SIZE):
            if self.matrix[i][i] != mark:
                lr_diagonal_win = False
            if self.matrix[i][BOARD_SIZE - (1+i)] != mark:
                rl_diagonal_win = False
            if self.matrix[i][0] == 0 and self.matrix[0][i] == 0:
                continue
            row_win = True
            column_win = True
            for j in range(BOARD_SIZE):
                if self.matrix[i][j] == 0:
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
