"""Test suite for sudoku_logic module."""
import pytest
import sudoku_logic


class TestBoardCreation:
    """Tests for board creation functions."""

    def test_create_empty_board(self):
        """Test that empty board has all zeros."""
        board = sudoku_logic.create_empty_board()
        assert len(board) == 9
        for row in board:
            assert len(row) == 9
            assert all(cell == 0 for cell in row)

    def test_deep_copy_creates_independent_copy(self, empty_board):
        """Test that deep_copy creates independent copy of board."""
        empty_board[0][0] = 5
        copied = sudoku_logic.deep_copy(empty_board)
        copied[0][0] = 7
        assert empty_board[0][0] == 5
        assert copied[0][0] == 7


class TestSudokuRules:
    """Tests for Sudoku rule validation."""

    def test_is_safe_returns_true_for_valid_placement(self, empty_board):
        """Test that is_safe returns True for valid number placement."""
        # Empty board, placing any number should be safe
        assert sudoku_logic.is_safe(empty_board, 0, 0, 1) is True
        assert sudoku_logic.is_safe(empty_board, 4, 4, 5) is True

    def test_is_safe_detects_row_conflict(self, empty_board):
        """Test that is_safe detects duplicates in same row."""
        empty_board[0][0] = 5
        assert sudoku_logic.is_safe(empty_board, 0, 1, 5) is False

    def test_is_safe_detects_column_conflict(self, empty_board):
        """Test that is_safe detects duplicates in same column."""
        empty_board[0][0] = 3
        assert sudoku_logic.is_safe(empty_board, 1, 0, 3) is False

    def test_is_safe_detects_box_conflict(self, empty_board):
        """Test that is_safe detects duplicates in same 3x3 box."""
        empty_board[0][0] = 7
        # (1,1) is in same 3x3 box as (0,0)
        assert sudoku_logic.is_safe(empty_board, 1, 1, 7) is False

    def test_is_safe_allows_number_in_different_box(self, empty_board):
        """Test that is_safe allows same number in different 3x3 box."""
        empty_board[0][0] = 7
        # (3,3) is in different 3x3 box from (0,0)
        assert sudoku_logic.is_safe(empty_board, 3, 3, 7) is True


class TestPuzzleGeneration:
    """Tests for puzzle generation."""

    def test_generate_puzzle_returns_tuple(self):
        """Test that generate_puzzle returns puzzle and solution."""
        puzzle, solution = sudoku_logic.generate_puzzle(clues=35)
        assert isinstance(puzzle, list)
        assert isinstance(solution, list)

    def test_generate_puzzle_creates_valid_sizes(self):
        """Test that generated puzzle and solution have correct dimensions."""
        puzzle, solution = sudoku_logic.generate_puzzle(clues=40)
        assert len(puzzle) == 9
        assert len(solution) == 9
        assert all(len(row) == 9 for row in puzzle)
        assert all(len(row) == 9 for row in solution)

    def test_generate_puzzle_respects_clues_count(self):
        """Test that generated puzzle has approximately correct number of clues."""
        clues = 30
        puzzle, _ = sudoku_logic.generate_puzzle(clues=clues)
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        assert filled_cells == clues

    def test_solution_is_complete(self):
        """Test that generated solution has no empty cells."""
        _, solution = sudoku_logic.generate_puzzle(clues=35)
        for row in solution:
            assert all(cell != 0 for cell in row)

    def test_puzzle_is_subset_of_solution(self):
        """Test that puzzle clues match the solution values."""
        puzzle, solution = sudoku_logic.generate_puzzle(clues=35)
        for i in range(9):
            for j in range(9):
                if puzzle[i][j] != 0:
                    assert puzzle[i][j] == solution[i][j]
