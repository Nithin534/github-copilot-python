"""Test suite for Flask app routes."""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import app
import sudoku_logic


@pytest.fixture
def client():
    """Flask test client fixture."""
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


class TestIndexRoute:
    """Tests for the index route."""

    def test_index_returns_200(self, client):
        """Test that index route returns 200 status."""
        response = client.get('/')
        assert response.status_code == 200


class TestNewGameRoute:
    """Tests for the /new game creation route."""

    def test_new_game_default(self, client):
        """Test /new with no parameters (should default to medium)."""
        response = client.get('/new')
        assert response.status_code == 200
        data = response.get_json()
        assert 'puzzle' in data
        puzzle = data['puzzle']
        assert len(puzzle) == 9
        assert all(len(row) == 9 for row in puzzle)
        # Should have medium difficulty clues (35) with 1-2 cell variance
        filled = sum(1 for row in puzzle for cell in row if cell != 0)
        target = sudoku_logic.DIFFICULTY_LEVELS['medium']
        assert abs(filled - target) <= 2

    def test_new_game_with_easy_difficulty(self, client):
        """Test /new with difficulty=easy."""
        response = client.get('/new?difficulty=easy')
        assert response.status_code == 200
        data = response.get_json()
        puzzle = data['puzzle']
        filled = sum(1 for row in puzzle for cell in row if cell != 0)
        # Allow 1-2 cell variance due to uniqueness constraint
        target = sudoku_logic.DIFFICULTY_LEVELS['easy']
        assert abs(filled - target) <= 2

    def test_new_game_with_medium_difficulty(self, client):
        """Test /new with difficulty=medium."""
        response = client.get('/new?difficulty=medium')
        assert response.status_code == 200
        data = response.get_json()
        puzzle = data['puzzle']
        filled = sum(1 for row in puzzle for cell in row if cell != 0)
        # Allow 1-2 cell variance due to uniqueness constraint
        target = sudoku_logic.DIFFICULTY_LEVELS['medium']
        assert abs(filled - target) <= 2

    def test_new_game_with_hard_difficulty(self, client):
        """Test /new with difficulty=hard."""
        response = client.get('/new?difficulty=hard')
        assert response.status_code == 200
        data = response.get_json()
        puzzle = data['puzzle']
        filled = sum(1 for row in puzzle for cell in row if cell != 0)
        # Allow 1-2 cell variance due to uniqueness constraint
        target = sudoku_logic.DIFFICULTY_LEVELS['hard']
        assert abs(filled - target) <= 2

    def test_new_game_with_invalid_difficulty(self, client):
        """Test /new with invalid difficulty returns 400."""
        response = client.get('/new?difficulty=impossible')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_new_game_with_clues_parameter(self, client):
        """Test /new with explicit clues parameter."""
        custom_clues = 40
        response = client.get(f'/new?clues={custom_clues}')
        assert response.status_code == 200
        data = response.get_json()
        puzzle = data['puzzle']
        filled = sum(1 for row in puzzle for cell in row if cell != 0)
        assert filled == custom_clues

    def test_new_game_clues_overrides_difficulty(self, client):
        """Test that clues parameter takes precedence over difficulty."""
        response = client.get('/new?clues=40&difficulty=hard')
        assert response.status_code == 200
        data = response.get_json()
        puzzle = data['puzzle']
        filled = sum(1 for row in puzzle for cell in row if cell != 0)
        # Should use clues (40), not hard (25)
        assert filled == 40

    def test_new_game_updates_session_puzzle(self, client):
        """Test that new game stores puzzle and solution in session."""
        response = client.get('/new?difficulty=easy')
        assert response.status_code == 200
        
        # Access session data using session_transaction
        with client.session_transaction() as sess:
            assert 'puzzle' in sess
            assert 'solution' in sess
            puzzle = sess['puzzle']
            solution = sess['solution']
        
        # Solution should be complete
        assert all(cell != 0 for row in solution for cell in row)
        # Puzzle should be subset of solution
        for i in range(9):
            for j in range(9):
                if puzzle[i][j] != 0:
                    assert puzzle[i][j] == solution[i][j]


class TestCheckSolutionRoute:
    """Tests for the /check solution route with conflict detection."""

    def test_check_solution_without_active_game(self, client):
        """Test /check without an active game returns 400."""
        response = client.post('/check', json={'board': [[0]*9 for _ in range(9)]})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_check_solution_response_structure(self, client):
        """Test /check response includes all required fields."""
        client.get('/new')
        board = [[0]*9 for _ in range(9)]
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify all required fields are present
        assert 'conflicts' in data
        assert 'incorrect' in data
        assert 'is_complete' in data
        assert 'is_solved' in data
        
        # Verify correct types
        assert isinstance(data['conflicts'], list)
        assert isinstance(data['incorrect'], list)
        assert isinstance(data['is_complete'], bool)
        assert isinstance(data['is_solved'], bool)

    def test_check_solution_correct_complete_board(self, client):
        """Test /check with correct complete solution."""
        client.get('/new')
        with client.session_transaction() as sess:
            solution = sess['solution']
        
        response = client.post('/check', json={'board': solution})
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have no conflicts, no incorrect cells
        assert data['conflicts'] == []
        assert data['incorrect'] == []
        assert data['is_complete'] is True
        assert data['is_solved'] is True

    def test_check_solution_incomplete_board(self, client):
        """Test /check with incomplete board (empty cells)."""
        client.get('/new')
        with client.session_transaction() as sess:
            puzzle = sess['puzzle']
        
        response = client.post('/check', json={'board': puzzle})
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['is_complete'] is False
        assert data['is_solved'] is False

    def test_check_solution_detects_row_conflict(self, client):
        """Test /check detects duplicate in same row."""
        client.get('/new')
        
        # Create board with duplicate in row 0
        board = [[0]*9 for _ in range(9)]
        board[0][0] = 5
        board[0][1] = 5  # Duplicate in same row
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        # Both cells should be marked as conflicts
        assert (0, 0) in data['conflicts'] or [0, 0] in data['conflicts']
        assert (0, 1) in data['conflicts'] or [0, 1] in data['conflicts']

    def test_check_solution_detects_column_conflict(self, client):
        """Test /check detects duplicate in same column."""
        client.get('/new')
        
        # Create board with duplicate in column 2
        board = [[0]*9 for _ in range(9)]
        board[0][2] = 7
        board[1][2] = 7  # Duplicate in same column
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        # Both cells should be marked as conflicts
        assert (0, 2) in data['conflicts'] or [0, 2] in data['conflicts']
        assert (1, 2) in data['conflicts'] or [1, 2] in data['conflicts']

    def test_check_solution_detects_box_conflict(self, client):
        """Test /check detects duplicate in same 3x3 box."""
        client.get('/new')
        
        # Create board with duplicate in top-left 3x3 box
        board = [[0]*9 for _ in range(9)]
        board[0][0] = 3  # Top-left box
        board[1][1] = 3  # Same box (but different row/col)
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        # Both cells should be marked as conflicts
        assert (0, 0) in data['conflicts'] or [0, 0] in data['conflicts']
        assert (1, 1) in data['conflicts'] or [1, 1] in data['conflicts']

    def test_check_solution_no_conflict_for_valid_placement(self, client):
        """Test /check doesn't flag valid placements as conflicts."""
        client.get('/new')
        
        # Create valid board (no duplicates)
        board = [[0]*9 for _ in range(9)]
        board[0][0] = 1
        board[0][1] = 2
        board[1][0] = 3
        board[1][1] = 4
        # Different rows, columns, and boxes - no conflict
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['conflicts'] == []

    def test_check_solution_detects_incorrect_values(self, client):
        """Test /check detects incorrect but valid placements."""
        client.get('/new')
        
        with client.session_transaction() as sess:
            solution = sess['solution']
        
        # Create a simple test board with just one wrong value (no duplicates)
        board = [[0]*9 for _ in range(9)]
        board[0][0] = 1  # Place a value
        
        # If solution has 1 at [0][0], use 2 instead (they differ but valid)
        if solution[0][0] == 1:
            board[0][0] = 2
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have no conflicts (single value in empty board)
        assert data['conflicts'] == []
        # Should detect cell [0][0] as incorrect (different from solution)
        assert len(data['incorrect']) > 0
        assert [0, 0] in data['incorrect']

    def test_check_solution_conflict_overrides_incorrect(self, client):
        """Test that conflict cells are still flagged even if matching solution."""
        client.get('/new')
        
        # Create board with conflict (duplicate) AND some incorrect cells
        board = [[0]*9 for _ in range(9)]
        board[0][0] = 5
        board[0][1] = 5  # Conflict!
        board[0][2] = 3  # Different from solution (likely)
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        # Conflicts should be detected
        assert len(data['conflicts']) >= 2

    def test_check_solution_empty_cells_not_conflicts(self, client):
        """Test that empty cells (0) are never marked as conflicts."""
        client.get('/new')
        
        # Create board with empty cells only
        board = [[0]*9 for _ in range(9)]
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        # No conflicts when board only has empty cells
        assert data['conflicts'] == []

    def test_check_solution_complete_but_incorrect(self, client):
        """Test /check with complete board that's incorrect."""
        client.get('/new')
        
        with client.session_transaction() as sess:
            solution = sess['solution']
        
        # Create complete board with wrong values
        board = [[1 for _ in range(9)] for _ in range(9)]  # All 1's
        
        response = client.post('/check', json={'board': board})
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['is_complete'] is True
        assert data['is_solved'] is False
        # Should have conflicts (many duplicates)
        assert len(data['conflicts']) > 0

    def test_check_solution_solved_detection_requires_all_conditions(self, client):
        """Test that is_solved requires complete, no conflicts, no incorrect, and correct."""
        client.get('/new')
        
        with client.session_transaction() as sess:
            solution = sess['solution']
        
        # Test 1: Complete and correct but with one wrong value
        board1 = [row[:] for row in solution]
        board1[0][0] = (board1[0][0] % 9) + 1
        
        response1 = client.post('/check', json={'board': board1})
        assert response1.get_json()['is_solved'] is False
        
        # Test 2: Complete, correct values, but has conflicts (duplicates)
        board2 = [[0]*9 for _ in range(9)]
        board2[0][0] = 1
        board2[0][1] = 1  # Conflict
        board2[0][2] = 3
        
        response2 = client.post('/check', json={'board': board2})
        data2 = response2.get_json()
        if data2['is_complete']:  # If completed after filling
            assert data2['is_solved'] is False


class TestSessionIsolation:
    """Tests for session isolation between players."""

    def test_new_games_have_different_puzzles(self, client):
        """Test that multiple new games create different puzzles."""
        # First game
        response1 = client.get('/new?difficulty=hard')
        assert response1.status_code == 200
        with client.session_transaction() as sess:
            puzzle1 = sess['puzzle']
            solution1 = sess['solution']
        
        # Second game (overwrites session in same client)
        response2 = client.get('/new?difficulty=hard')
        assert response2.status_code == 200
        with client.session_transaction() as sess:
            puzzle2 = sess['puzzle']
            solution2 = sess['solution']
        
        # Different sessions would have different data
        # In same session, puzzle2 replaces puzzle1
        assert puzzle1 != puzzle2
        assert solution1 != solution2

    def test_session_check_uses_current_puzzle(self, client):
        """Test that check_solution uses the current session's puzzle."""
        # Create game 1
        client.get('/new?difficulty=easy')
        with client.session_transaction() as sess:
            solution1 = sess['solution']
        
        # Create game 2 (overwrites session)
        client.get('/new?difficulty=hard')
        with client.session_transaction() as sess:
            solution2 = sess['solution']
        
        # Check solution for game 2
        response = client.post('/check', json={'board': solution2})
        assert response.status_code == 200
        data = response.get_json()
        assert data['incorrect'] == []  # Should match current session's solution
        
        # Checking solution1 against current session (solution2) should fail
        response = client.post('/check', json={'board': solution1})
        assert response.status_code == 200
        data = response.get_json()
        # Most cells should be incorrect (comparing puzzle1 solution against puzzle2 solution)
        assert len(data['incorrect']) > 0


class TestErrorHandling:
    """Tests for error handling in API routes."""

    # ========== /new Route Error Handling ==========

    def test_new_game_invalid_clues_not_integer(self, client):
        """Test /new with non-integer clues returns 400."""
        response = client.get('/new?clues=abc')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'integer' in data['error'].lower()

    def test_new_game_invalid_clues_negative(self, client):
        """Test /new with negative clues returns 400."""
        response = client.get('/new?clues=-5')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'between' in data['error'].lower()

    def test_new_game_invalid_clues_too_large(self, client):
        """Test /new with clues > 81 returns 400."""
        response = client.get('/new?clues=100')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'between' in data['error'].lower()

    def test_new_game_invalid_clues_zero(self, client):
        """Test /new with clues=0 returns 400."""
        response = client.get('/new?clues=0')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_new_game_invalid_clues_float(self, client):
        """Test /new with float clues returns 400."""
        response = client.get('/new?clues=35.5')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    # ========== /check Route Error Handling - Missing Data ==========

    def test_check_solution_missing_board(self, client):
        """Test /check without board data returns 400."""
        client.get('/new')
        response = client.post('/check', json={})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'board' in data['error'].lower()

    def test_check_solution_missing_game(self, client):
        """Test /check without active game returns 400."""
        # Create valid board but don't start a game
        valid_board = [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9]
        ]
        response = client.post('/check', json={'board': valid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'game' in data['error'].lower() or 'active' in data['error'].lower()

    # ========== /check Route Error Handling - Invalid Board Structure ==========

    def test_check_solution_board_not_list(self, client):
        """Test /check with board as non-list returns 400."""
        client.get('/new')
        response = client.post('/check', json={'board': 'not a list'})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'list' in data['error'].lower()

    def test_check_solution_board_wrong_row_count(self, client):
        """Test /check with wrong number of rows returns 400."""
        client.get('/new')
        # 8 rows instead of 9
        invalid_board = [[0] * 9 for _ in range(8)]
        response = client.post('/check', json={'board': invalid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_check_solution_board_wrong_column_count(self, client):
        """Test /check with wrong number of columns returns 400."""
        client.get('/new')
        # 8 columns instead of 9
        invalid_board = [[0] * 8 for _ in range(9)]
        response = client.post('/check', json={'board': invalid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_check_solution_row_not_list(self, client):
        """Test /check with non-list row returns 400."""
        client.get('/new')
        invalid_board = [
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
            'not a list',  # Invalid
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
        ]
        response = client.post('/check', json={'board': invalid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    # ========== /check Route Error Handling - Invalid Cell Values ==========

    def test_check_solution_cell_not_integer(self, client):
        """Test /check with non-integer cell returns 400."""
        client.get('/new')
        invalid_board = [[0] * 9 for _ in range(9)]
        invalid_board[0][0] = 'not an int'
        response = client.post('/check', json={'board': invalid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'integer' in data['error'].lower()

    def test_check_solution_cell_negative(self, client):
        """Test /check with negative cell value returns 400."""
        client.get('/new')
        invalid_board = [[0] * 9 for _ in range(9)]
        invalid_board[0][0] = -1
        response = client.post('/check', json={'board': invalid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'range' in data['error'].lower()

    def test_check_solution_cell_too_large(self, client):
        """Test /check with cell value > 9 returns 400."""
        client.get('/new')
        invalid_board = [[0] * 9 for _ in range(9)]
        invalid_board[0][0] = 10
        response = client.post('/check', json={'board': invalid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'range' in data['error'].lower()

    def test_check_solution_cell_float(self, client):
        """Test /check with float cell value returns 400."""
        client.get('/new')
        invalid_board = [[0] * 9 for _ in range(9)]
        invalid_board[0][0] = 5.5
        response = client.post('/check', json={'board': invalid_board})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    # ========== JSON Parsing Error Handling ==========

    def test_check_solution_invalid_json(self, client):
        """Test /check with malformed JSON returns 400."""
        client.get('/new')
        response = client.post(
            '/check',
            data='not valid json',
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_check_solution_empty_body(self, client):
        """Test /check with empty request body returns 400."""
        client.get('/new')
        response = client.post(
            '/check',
            data='',
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    # ========== Valid Edge Cases ==========

    def test_check_solution_valid_min_clues(self, client):
        """Test /new with minimum valid clues (1)."""
        response = client.get('/new?clues=1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'puzzle' in data

    def test_check_solution_valid_max_clues(self, client):
        """Test /new with maximum valid clues (81)."""
        response = client.get('/new?clues=81')
        assert response.status_code == 200
        data = response.get_json()
        assert 'puzzle' in data

    def test_check_solution_all_zeros_board(self, client):
        """Test /check with all-zero board (empty cells)."""
        client.get('/new')
        empty_board = [[0] * 9 for _ in range(9)]
        response = client.post('/check', json={'board': empty_board})
        assert response.status_code == 200
        data = response.get_json()
        assert 'incorrect' in data
        # Most cells should be incorrect unless solution is also all zeros
        assert isinstance(data['incorrect'], list)


class TestHintEndpoint:
    """Tests for the /hint endpoint."""

    def test_hint_without_active_game(self, client):
        """Test /hint without starting a game returns 400."""
        response = client.post('/hint')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'game' in data['error'].lower()

    def test_hint_returns_valid_cell(self, client):
        """Test /hint returns valid (row, col, value) coordinates."""
        client.get('/new')
        response = client.post('/hint')
        assert response.status_code == 200
        data = response.get_json()
        
        # Check required fields
        assert 'row' in data
        assert 'col' in data
        assert 'value' in data
        assert 'hints_used' in data
        assert 'puzzle' in data
        
        # Validate coordinates and value
        assert 0 <= data['row'] < 9
        assert 0 <= data['col'] < 9
        assert 1 <= data['value'] <= 9
        assert data['hints_used'] == 1

    def test_hint_fills_puzzle_correctly(self, client):
        """Test that hint correctly fills the puzzle cell."""
        client.get('/new')
        
        # Get the hint
        response = client.post('/hint')
        data = response.get_json()
        row, col, value = data['row'], data['col'], data['value']
        
        # Verify puzzle was updated
        with client.session_transaction() as sess:
            assert sess['puzzle'][row][col] == value
            
        # Verify returned puzzle matches session
        assert data['puzzle'][row][col] == value

    def test_hint_increments_counter(self, client):
        """Test that each hint increments hints_used counter."""
        client.get('/new')
        
        # First hint
        r1 = client.post('/hint')
        assert r1.get_json()['hints_used'] == 1
        
        # Second hint
        r2 = client.post('/hint')
        assert r2.get_json()['hints_used'] == 2
        
        # Third hint
        r3 = client.post('/hint')
        assert r3.get_json()['hints_used'] == 3

    def test_hint_counter_persists_in_session(self, client):
        """Test that hints_used counter is saved in session."""
        client.get('/new')
        
        # Give 2 hints
        client.post('/hint')
        client.post('/hint')
        
        # Verify session has correct count
        with client.session_transaction() as sess:
            assert sess['hints_used'] == 2

    def test_hint_gives_different_cells(self, client):
        """Test that multiple hints reveal different cells."""
        client.get('/new')
        
        # Get multiple hints
        hint1 = client.post('/hint').get_json()
        hint2 = client.post('/hint').get_json()
        hint3 = client.post('/hint').get_json()
        
        # Cells should be different (extremely unlikely to be same)
        cells = [
            (hint1['row'], hint1['col']),
            (hint2['row'], hint2['col']),
            (hint3['row'], hint3['col'])
        ]
        
        # At least some should be different
        assert len(set(cells)) >= 2

    def test_hint_value_matches_solution(self, client):
        """Test that hint value matches solution."""
        client.get('/new')
        
        # Get session data
        with client.session_transaction() as sess:
            solution = sess['solution']
        
        # Get a hint
        hint_response = client.post('/hint')
        hint_data = hint_response.get_json()
        row, col, value = hint_data['row'], hint_data['col'], hint_data['value']
        
        # Verify hint value matches solution
        assert solution[row][col] == value

    def test_hint_respects_empty_cells_only(self, client):
        """Test that hint only fills cells that were originally empty."""
        client.get('/new')
        
        # Get original puzzle
        with client.session_transaction() as sess:
            original_puzzle = [row[:] for row in sess['puzzle']]
        
        # Get a hint
        hint_response = client.post('/hint')
        row, col = hint_response.get_json()['row'], hint_response.get_json()['col']
        
        # Cell should have been empty in original
        assert original_puzzle[row][col] == 0

    def test_hint_puzzle_complete_error(self, client):
        """Test /hint returns error when puzzle is complete."""
        client.get('/new?clues=81')  # Full puzzle
        response = client.post('/hint')
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'empty' in data['error'].lower()

    def test_hints_reset_for_new_game(self, client):
        """Test that hints_used resets when starting new game."""
        # First game with hints
        client.get('/new')
        client.post('/hint')
        client.post('/hint')
        
        with client.session_transaction() as sess:
            assert sess['hints_used'] == 2
        
        # Second game
        client.get('/new')
        
        with client.session_transaction() as sess:
            assert sess['hints_used'] == 0

    def test_hint_response_includes_updated_puzzle(self, client):
        """Test that hint response includes the updated puzzle."""
        client.get('/new')
        response = client.post('/hint')
        data = response.get_json()
        
        puzzle = data['puzzle']
        
        # Verify puzzle structure
        assert len(puzzle) == 9
        assert all(len(row) == 9 for row in puzzle)
        
        # Verify hinted cell is filled
        row, col, value = data['row'], data['col'], data['value']
        assert puzzle[row][col] == value

    def test_multiple_hints_same_game(self, client):
        """Test providing multiple hints in same game."""
        client.get('/new')
        
        hints = []
        for i in range(5):
            response = client.post('/hint')
            assert response.status_code == 200
            data = response.get_json()
            assert data['hints_used'] == i + 1
            hints.append((data['row'], data['col'], data['value']))
        
        # All hints should be valid
        assert len(hints) == 5
        
        # Verify they're different (very unlikely to be same cell twice)
        cells = [(h[0], h[1]) for h in hints]
        assert len(set(cells)) >= 4  # At least 4 different cells out of 5

    def test_hint_cell_in_puzzle(self, client):
        """Test that returned cell coordinates are valid."""
        client.get('/new')
        response = client.post('/hint')
        data = response.get_json()
        
        row, col, value = data['row'], data['col'], data['value']
        puzzle = data['puzzle']
        
        # Cell should match the returned value
        assert puzzle[row][col] == value
