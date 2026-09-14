"""Shared pytest configuration and fixtures."""
import sys
from pathlib import Path

# Add parent directory to path so we can import app and sudoku_logic
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sudoku_logic


@pytest.fixture
def empty_board():
    """Fixture providing an empty 9x9 Sudoku board."""
    return sudoku_logic.create_empty_board()


@pytest.fixture
def solved_board():
    """Fixture providing a completed valid Sudoku board."""
    board = sudoku_logic.create_empty_board()
    sudoku_logic.fill_board(board)
    return board
