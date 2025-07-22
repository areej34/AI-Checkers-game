import tkinter as tk
from tkinter import messagebox
import copy

# --- Constants ---
EMPTY = 0
P1 = 1           # Human Player
P1_KING = 2
P2 = 3           # AI Player
P2_KING = 4
BOARD_SIZE = 8

TILE_SIZE = 80
BOARD_COLOR_1 = "#D18B47"
BOARD_COLOR_2 = "#FFCE9E"
HIGHLIGHT_COLOR = "#00FF00"

# --- Utility Functions ---
def opponent(player):
    return P2 if player in [P1, P1_KING] else P1

def is_king(piece):
    return piece in [P1_KING, P2_KING]

def is_player(piece, player):
    if player == P1:
        return piece == P1 or piece == P1_KING
    return piece == P2 or piece == P2_KING

def promote(row, piece):
    if piece == P1 and row == 0:
        return P1_KING
    elif piece == P2 and row == 7:
        return P2_KING
    return piece

# --- Game State Class ---
class GameState:
    def __init__(self):
        self.board = self.create_board()
        self.current_player = P1

    def create_board(self):
        board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        for row in range(3):
            for col in range(BOARD_SIZE):
                if (row + col) % 2 == 1:
                    board[row][col] = P2
        for row in range(5, 8):
            for col in range(BOARD_SIZE):
                if (row + col) % 2 == 1:
                    board[row][col] = P1
        return board

    def clone(self):
        return copy.deepcopy(self)

    def get_piece_directions(self, piece):
        if piece == P1:
            return [(-1, -1), (-1, 1)]
        if piece == P2:
            return [(1, -1), (1, 1)]
        return [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    def is_within_bounds(self, r, c):
        return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE

    def get_all_moves(self, player):
        captures = []
        normal_moves = []

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if not is_player(piece, player):
                    continue
                cap = self.get_captures(r, c)
                if cap:
                    captures.extend(cap)
                else:
                    normal_moves.extend(self.get_simple_moves(r, c))

        return captures if captures else normal_moves

    def get_simple_moves(self, r, c):
        piece = self.board[r][c]
        directions = self.get_piece_directions(piece)
        moves = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if self.is_within_bounds(nr, nc) and self.board[nr][nc] == EMPTY:
                moves.append([(r, c), (nr, nc)])
        return moves

    def get_captures(self, r, c, path=None, visited=None):
        if path is None:
            path = [(r, c)]
        if visited is None:
            visited = set()

        piece = self.board[r][c]
        directions = self.get_piece_directions(piece)
        captures = []

        for dr, dc in directions:
            mid_r, mid_c = r + dr, c + dc
            end_r, end_c = r + 2 * dr, c + 2 * dc
            if not self.is_within_bounds(end_r, end_c):
                continue
            mid_piece = self.board[mid_r][mid_c]
            end_piece = self.board[end_r][end_c]
            if (end_r, end_c) in visited:
                continue
            if is_player(mid_piece, opponent(self.current_player)) and end_piece == EMPTY:
                new_board = self.clone()
                new_board.make_move([(r, c), (end_r, end_c)], simulate=True)
                subcaptures = new_board.get_captures(end_r, end_c, path + [(end_r, end_c)], visited | {(r, c)})
                if subcaptures:
                    captures.extend(subcaptures)
                else:
                    captures.append(path + [(end_r, end_c)])
        return captures

    def make_move(self, move, simulate=False):
        board = self.board
        (sr, sc) = move[0]
        (er, ec) = move[-1]
        piece = board[sr][sc]
        board[sr][sc] = EMPTY
        for i in range(1, len(move)):
            mr, mc = move[i]
            if abs(mr - move[i - 1][0]) == 2:
                cap_r = (mr + move[i - 1][0]) // 2
                cap_c = (mc + move[i - 1][1]) // 2
                board[cap_r][cap_c] = EMPTY
        board[er][ec] = promote(er, piece)
        if not simulate:
            self.current_player = opponent(self.current_player)

    def evaluate(self):
        score = 0
        for row in self.board:
            for piece in row:
                if piece == P1:
                    score -= 1
                elif piece == P1_KING:
                    score -= 2
                elif piece == P2:
                    score += 1
                elif piece == P2_KING:
                    score += 2
        return score

    def is_terminal(self):
        return len(self.get_all_moves(self.current_player)) == 0

# --- Minimax ---
def minimax(state, depth, alpha, beta, maximizing):
    if depth == 0 or state.is_terminal():
        return state.evaluate(), None

    moves = state.get_all_moves(state.current_player)
    best_move = None

    if maximizing:
        max_eval = float('-inf')
        for move in moves:
            new_state = state.clone()
            new_state.make_move(move)
            eval, _ = minimax(new_state, depth - 1, alpha, beta, False)
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in moves:
            new_state = state.clone()
            new_state.make_move(move)
            eval, _ = minimax(new_state, depth - 1, alpha, beta, True)
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval, best_move

# --- GUI ---
class CheckersGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Checkers")
        self.canvas = tk.Canvas(root, width=8*TILE_SIZE, height=8*TILE_SIZE)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

        self.state = GameState()
        self.selected_piece = None
        self.valid_moves = []

        self.draw_board()

    def get_pieces_with_captures(self, player):
        capture_sources = []
        moves = self.state.get_all_moves(player)
        for move in moves:
            if abs(move[1][0] - move[0][0]) == 2:  # jump
                if move[0] not in capture_sources:
                    capture_sources.append(move[0])
        return capture_sources

    def draw_board(self):
        self.canvas.delete("all")

        capture_sources = self.get_pieces_with_captures(P1) if self.state.current_player == P1 else []

        for r in range(8):
            for c in range(8):
                color = BOARD_COLOR_1 if (r + c) % 2 == 1 else BOARD_COLOR_2
                x1 = c * TILE_SIZE
                y1 = r * TILE_SIZE
                x2 = x1 + TILE_SIZE
                y2 = y1 + TILE_SIZE

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color)

                piece = self.state.board[r][c]
                if piece != EMPTY:
                    fill = "white" if piece in [P1, P1_KING] else "black"
                    self.canvas.create_oval(x1+10, y1+10, x2-10, y2-10, fill=fill)

                    if piece in [P1_KING, P2_KING]:
                        self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text="K", fill="white", font=("Arial", 24, "bold"))

                if self.selected_piece == (r, c):
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline=HIGHLIGHT_COLOR, width=4)

                if (r, c) in capture_sources:
                    self.canvas.create_rectangle(x1+3, y1+3, x2-3, y2-3, outline="red", width=3)

        for move in self.valid_moves:
            (_, (r, c)) = move[0], move[-1]
            x1 = c * TILE_SIZE
            y1 = r * TILE_SIZE
            x2 = x1 + TILE_SIZE
            y2 = y1 + TILE_SIZE
            self.canvas.create_rectangle(x1+5, y1+5, x2-5, y2-5, outline="green", width=3)

    def on_click(self, event):
        if self.state.current_player != P1:
            return

        col = event.x // TILE_SIZE
        row = event.y // TILE_SIZE

        if self.selected_piece:
            moves = [m for m in self.state.get_all_moves(P1) if m[0] == self.selected_piece and m[-1] == (row, col)]
            if moves:
                self.state.make_move(moves[0])
                self.selected_piece = None
                self.valid_moves = []
                self.draw_board()
                self.root.after(500, self.ai_turn)
                return

        piece = self.state.board[row][col]
        if piece in [P1, P1_KING]:
            self.selected_piece = (row, col)
            self.valid_moves = [m for m in self.state.get_all_moves(P1) if m[0] == (row, col)]
        else:
            self.selected_piece = None
            self.valid_moves = []
        self.draw_board()

    def ai_turn(self):
        if self.state.is_terminal():
            self.end_game()
            return
        _, move = minimax(self.state, 4, float('-inf'), float('inf'), True)
        if move:
            self.state.make_move(move)
            self.draw_board()
            if self.state.is_terminal():
                self.end_game()

    def end_game(self):
        winner = "AI" if self.state.current_player == P1 else "You"
        messagebox.showinfo("Game Over", f"{winner} won!")
        self.root.quit()

# --- Run Game ---
if __name__ == "__main__":
    root = tk.Tk()
    app = CheckersGUI(root)
    root.mainloop()
