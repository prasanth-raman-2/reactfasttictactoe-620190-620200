from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict

# Tic Tac Toe FastAPI app with REST endpoints for game logic and board state

openapi_tags = [
    {"name": "tic-tac-toe", "description": "Endpoints for Tic Tac Toe game operations"}
]

app = FastAPI(
    title="Tic Tac Toe API",
    description="Backend API for a Tic Tac Toe game (Player vs Player) with game management and game logic.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MoveRequest(BaseModel):
    """Request model for making a move on the board."""
    row: int = Field(..., ge=0, le=2, description="Row index (0-2)")
    col: int = Field(..., ge=0, le=2, description="Column index (0-2)")


class BoardResponse(BaseModel):
    """Response model for board state and status."""
    board: List[List[Optional[Literal["X", "O"]]]] = Field(..., description="Current game board")
    player_turn: Literal["X", "O"] = Field(..., description="Current player turn")
    status: Literal["ongoing", "win", "draw"] = Field(..., description="Current game status")
    winner: Optional[Literal["X", "O"]] = Field(None, description="Winner if game over, else None")


# Core in-memory "singleton" state (reset on server restart)
class TicTacToeGame:
    def __init__(self):
        self.reset()

    # PUBLIC_INTERFACE
    def reset(self):
        """Reset the game to the initial state."""
        self.board = [[None for _ in range(3)] for _ in range(3)]
        self.player_turn = "X"
        self.status = "ongoing"
        self.winner = None

    # PUBLIC_INTERFACE
    def make_move(self, row: int, col: int):
        """Make a move for the current player, update the board and check game status."""
        if self.status != "ongoing":
            raise ValueError("Game is not ongoing. Please start/reset a new game.")
        if not (0 <= row <= 2 and 0 <= col <= 2):
            raise ValueError("Row and column must be between 0 and 2.")
        if self.board[row][col] is not None:
            raise ValueError("Cell is already occupied.")
        self.board[row][col] = self.player_turn
        self._update_status()
        if self.status == "ongoing":
            # Switch player
            self.player_turn = "O" if self.player_turn == "X" else "X"

    # PUBLIC_INTERFACE
    def get_status(self):
        """Get the current game board, player turn, status and winner."""
        return {
            "board": self.board,
            "player_turn": self.player_turn,
            "status": self.status,
            "winner": self.winner,
        }

    def _update_status(self):
        lines = []
        # Rows and columns
        lines.extend(self.board)
        lines.extend([[self.board[r][c] for r in range(3)] for c in range(3)])
        # Diagonals
        lines.append([self.board[i][i] for i in range(3)])
        lines.append([self.board[i][2 - i] for i in range(3)])
        # Check for win
        for line in lines:
            if line[0] and line.count(line[0]) == 3:
                self.status = "win"
                self.winner = line[0]
                return
        # Check for draw
        if all(self.board[r][c] is not None for r in range(3) for c in range(3)):
            self.status = "draw"
            self.winner = None
            return
        # Ongoing
        self.status = "ongoing"
        self.winner = None


# Singleton instance to persist game state (reset on server restart)
GAME = TicTacToeGame()


@app.get("/", tags=["tic-tac-toe"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


@app.post("/start", response_model=BoardResponse, tags=["tic-tac-toe"], summary="Start a new game", description="Starts a new Tic Tac Toe game and returns the initial board.", operation_id="start_game")
# PUBLIC_INTERFACE
def start_game():
    """
    Start a new game of Tic Tac Toe.

    Returns:
        BoardResponse: Current (reset) board and state.
    """
    GAME.reset()
    state = GAME.get_status()
    return BoardResponse(**state)


@app.post("/move", response_model=BoardResponse, tags=["tic-tac-toe"], summary="Make a move", description="Make a move at the specified row and column for the current player.", operation_id="make_move")
# PUBLIC_INTERFACE
def make_move(request: MoveRequest):
    """
    Make a move by the current player.

    Args:
        request (MoveRequest): Contains row and column of the move.

    Returns:
        BoardResponse: Updated board and state.
    Raises:
        400 error if the move is invalid.
    """
    try:
        GAME.make_move(request.row, request.col)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    state = GAME.get_status()
    return BoardResponse(**state)


@app.get("/status", response_model=BoardResponse, tags=["tic-tac-toe"], summary="Get game status", description="Gets the current board, player turn, and game status.", operation_id="get_status")
# PUBLIC_INTERFACE
def get_status():
    """
    Get the current status of the game board.

    Returns:
        BoardResponse: Board, player turn, winner, and game status ("ongoing", "win", "draw").
    """
    state = GAME.get_status()
    return BoardResponse(**state)


@app.post("/reset", response_model=BoardResponse, tags=["tic-tac-toe"], summary="Reset game", description="Resets the current Tic Tac Toe game to initial state and returns the board.", operation_id="reset_game")
# PUBLIC_INTERFACE
def reset_game():
    """
    Reset the game to the initial empty board.

    Returns:
        BoardResponse: Board, player turn, status (should be "ongoing"), and no winner.
    """
    GAME.reset()
    state = GAME.get_status()
    return BoardResponse(**state)
