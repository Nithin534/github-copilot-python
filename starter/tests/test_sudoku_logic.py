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


class TestSolutionUniqueness:
    """Tests for solution uniqueness verification."""

    def test_count_solutions_empty_board_has_multiple(self, empty_board):
        """Test that empty board has multiple solutions."""
        count = sudoku_logic.count_solutions(empty_board, max_count=2)
        assert count >= 2

    def test_count_solutions_complete_board_has_one(self, solved_board):
        """Test that completed board has exactly one solution."""
        count = sudoku_logic.count_solutions(solved_board)
        assert count == 1

    def test_count_solutions_respects_max_count(self, empty_board):
        """Test that count_solutions stops at max_count."""
        count = sudoku_logic.count_solutions(empty_board, max_count=2)
        assert count <= 2

    def test_is_valid_puzzle_accepts_solved_board(self, solved_board):
        """Test that is_valid_puzzle recognizes solved board as valid."""
        assert sudoku_logic.is_valid_puzzle(solved_board) is True

    def test_is_valid_puzzle_rejects_empty_board(self, empty_board):
        """Test that is_valid_puzzle rejects empty board (too many solutions)."""
        assert sudoku_logic.is_valid_puzzle(empty_board) is False


class TestCellRemoval:
    """Tests for intelligent cell removal with uniqueness guarantee."""

    def test_remove_cells_safely_respects_clues(self, solved_board):
        """Test that remove_cells_safely creates puzzle with target clues."""
        target_clues = 30
        puzzle = sudoku_logic.remove_cells_safely(solved_board, target_clues)
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        assert filled_cells == target_clues

    def test_remove_cells_safely_generates_valid_puzzle(self, solved_board):
        """Test that removed puzzle has exactly one solution."""
        puzzle = sudoku_logic.remove_cells_safely(solved_board, 35)
        assert sudoku_logic.is_valid_puzzle(puzzle) is True

    def test_remove_cells_safely_puzzle_matches_solution(self, solved_board):
        """Test that remaining clues match the solution."""
        puzzle = sudoku_logic.remove_cells_safely(solved_board, 35)
        for i in range(9):
            for j in range(9):
                if puzzle[i][j] != 0:
                    assert puzzle[i][j] == solved_board[i][j]

    def test_remove_cells_safely_creates_different_puzzles(self):
        """Test that multiple calls create different puzzles (randomness)."""
        board = sudoku_logic.create_empty_board()
        sudoku_logic.fill_board(board)
        
        puzzle1 = sudoku_logic.remove_cells_safely(board, 30)
        puzzle2 = sudoku_logic.remove_cells_safely(board, 30)
        
        # Puzzles should be different (extremely unlikely to be the same)
        assert puzzle1 != puzzle2


class TestDifficultyLevels:
    """Tests for difficulty level system."""

    def test_difficulty_levels_defined(self):
        """Test that all difficulty levels are defined."""
        assert 'easy' in sudoku_logic.DIFFICULTY_LEVELS
        assert 'medium' in sudoku_logic.DIFFICULTY_LEVELS
        assert 'hard' in sudoku_logic.DIFFICULTY_LEVELS

    def test_difficulty_levels_ordering(self):
        """Test that easy > medium > hard (more clues = easier)."""
        easy_clues = sudoku_logic.DIFFICULTY_LEVELS['easy']
        medium_clues = sudoku_logic.DIFFICULTY_LEVELS['medium']
        hard_clues = sudoku_logic.DIFFICULTY_LEVELS['hard']
        
        assert easy_clues > medium_clues > hard_clues

    def test_generate_puzzle_with_easy_difficulty(self):
        """Test puzzle generation with easy difficulty."""
        puzzle, solution = sudoku_logic.generate_puzzle(difficulty='easy')
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        # Allow 1-2 cell variance due to uniqueness constraint
        target = sudoku_logic.DIFFICULTY_LEVELS['easy']
        assert abs(filled_cells - target) <= 2
        assert sudoku_logic.is_valid_puzzle(puzzle) is True

    def test_generate_puzzle_with_medium_difficulty(self):
        """Test puzzle generation with medium difficulty."""
        puzzle, solution = sudoku_logic.generate_puzzle(difficulty='medium')
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        # Allow 1-2 cell variance due to uniqueness constraint
        target = sudoku_logic.DIFFICULTY_LEVELS['medium']
        assert abs(filled_cells - target) <= 2
        assert sudoku_logic.is_valid_puzzle(puzzle) is True

    def test_generate_puzzle_with_hard_difficulty(self):
        """Test puzzle generation with hard difficulty."""
        puzzle, solution = sudoku_logic.generate_puzzle(difficulty='hard')
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        # Allow 1-2 cell variance due to uniqueness constraint
        target = sudoku_logic.DIFFICULTY_LEVELS['hard']
        assert abs(filled_cells - target) <= 2
        assert sudoku_logic.is_valid_puzzle(puzzle) is True

    def test_generate_puzzle_clues_parameter_overrides_difficulty(self):
        """Test that explicit clues parameter overrides difficulty."""
        custom_clues = 40
        puzzle, _ = sudoku_logic.generate_puzzle(clues=custom_clues, difficulty='hard')
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        # Should use custom_clues (40), not hard (25)
        assert filled_cells == custom_clues

    def test_generate_puzzle_defaults_to_medium(self):
        """Test that no parameters defaults to medium difficulty."""
        puzzle, _ = sudoku_logic.generate_puzzle()
        filled_cells = sum(1 for row in puzzle for cell in row if cell != 0)
        assert filled_cells == sudoku_logic.DIFFICULTY_LEVELS['medium']

    def test_generate_puzzle_invalid_difficulty_raises_error(self):
        """Test that invalid difficulty raises ValueError."""
        with pytest.raises(ValueError, match="Invalid difficulty"):
            sudoku_logic.generate_puzzle(difficulty='impossible')

    def test_difficulty_puzzles_are_valid_and_unique(self):
        """Test that all difficulty levels generate valid unique puzzles."""
        for difficulty in ['easy', 'medium', 'hard']:
            puzzle, solution = sudoku_logic.generate_puzzle(difficulty=difficulty)
            # Verify unique solution
            assert sudoku_logic.is_valid_puzzle(puzzle) is True
            # Verify clues are approximately at expected count
            # (allow 1-2 variance due to uniqueness constraint)
            filled = sum(1 for row in puzzle for cell in row if cell != 0)
            target = sudoku_logic.DIFFICULTY_LEVELS[difficulty]
            assert abs(filled - target) <= 2


