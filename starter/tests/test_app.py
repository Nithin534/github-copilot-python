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
    """Tests for the /check solution route."""

    def test_check_solution_without_active_game(self, client):
        """Test /check without an active game returns 400."""
        # Don't create a new game, session has no solution
        response = client.post('/check', json={'board': []})
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_check_solution_with_correct_board(self, client):
        """Test /check with correct solution."""
        # Create a new game
        client.get('/new')
        
        # Get solution from session
        with client.session_transaction() as sess:
            solution = sess['solution']
        
        response = client.post('/check', json={'board': solution})
        assert response.status_code == 200
        data = response.get_json()
        assert 'incorrect' in data
        assert data['incorrect'] == []  # No incorrect cells

    def test_check_solution_with_incorrect_cells(self, client):
        """Test /check detects incorrect cells."""
        # Create a new game
        client.get('/new')
        
        # Get solution from session
        with client.session_transaction() as sess:
            solution = sess['solution']
        
        # Create incorrect board (change first cell)
        incorrect_board = [row[:] for row in solution]
        incorrect_board[0][0] = (incorrect_board[0][0] % 9) + 1  # Change to different number
        
        response = client.post('/check', json={'board': incorrect_board})
        assert response.status_code == 200
        data = response.get_json()
        assert 'incorrect' in data
        assert len(data['incorrect']) > 0
        assert [0, 0] in data['incorrect']


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
