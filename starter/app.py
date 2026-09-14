from flask import Flask, render_template, jsonify, request, session
import sudoku_logic
import os

app = Flask(__name__)

# Configure session security
# Use environment variable in production, fallback to dev key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# ============================================================================
# ERROR HANDLING HELPERS
# ============================================================================

def validate_board(board):
    """
    Validate board structure and values.
    
    Args:
        board: Data to validate as Sudoku board
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if valid, False otherwise
        - error_message: Human-readable error message if invalid, None if valid
    """
    # Check if board is provided
    if board is None:
        return False, "Missing 'board' data in request"
    
    # Check if board is a list
    if not isinstance(board, list):
        return False, "Board must be a list"
    
    # Check board has 9 rows
    if len(board) != sudoku_logic.SIZE:
        return False, f"Board must have {sudoku_logic.SIZE} rows, got {len(board)}"
    
    # Validate each row
    for i, row in enumerate(board):
        # Check if row is a list
        if not isinstance(row, list):
            return False, f"Row {i} must be a list, got {type(row).__name__}"
        
        # Check row has 9 columns
        if len(row) != sudoku_logic.SIZE:
            return False, f"Row {i} must have {sudoku_logic.SIZE} columns, got {len(row)}"
        
        # Validate each cell
        for j, cell in enumerate(row):
            # Check if cell is an integer
            if not isinstance(cell, int):
                return False, f"Cell ({i},{j}) must be an integer, got {type(cell).__name__}"
            
            # Check if cell value is in valid range
            if cell < 0 or cell > sudoku_logic.SIZE:
                return False, f"Cell ({i},{j}) value {cell} is out of range [0-{sudoku_logic.SIZE}]"
    
    return True, None


@app.errorhandler(400)
def bad_request(error):
    """Handle malformed JSON requests."""
    return jsonify({'error': 'Malformed request data'}), 400


@app.errorhandler(500)
def internal_error(error):
    """Handle unexpected server errors."""
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new')
def new_game():
    """
    Generate new puzzle for current player's session.
    
    Query Parameters:
        difficulty: 'easy', 'medium', or 'hard' (optional)
        clues: integer 1-81 (optional, overrides difficulty)
    
    Returns:
        JSON: {'puzzle': [[...]]} on success
        JSON: {'error': 'message'} on error (400)
    """
    try:
        difficulty = request.args.get('difficulty', None)
        clues = request.args.get('clues', None)
        
        # Validate and convert clues parameter
        if clues is not None:
            try:
                clues = int(clues)
            except (ValueError, TypeError):
                return jsonify({'error': 'Parameter "clues" must be an integer'}), 400
            
            # Validate clues range
            if clues < 1 or clues > 81:
                return jsonify({'error': 'Parameter "clues" must be between 1 and 81'}), 400
        
        # Generate puzzle (may raise ValueError for invalid difficulty)
        puzzle, solution = sudoku_logic.generate_puzzle(clues=clues, difficulty=difficulty)
        
    except ValueError as e:
        # Invalid difficulty
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Unexpected error
        return jsonify({'error': 'Failed to generate puzzle'}), 500
    
    # Store puzzle and solution in this player's session
    session['puzzle'] = puzzle
    session['solution'] = solution
    session.modified = True
    
    return jsonify({'puzzle': puzzle})

@app.route('/check', methods=['POST'])
def check_solution():
    """
    Check player's solution against their session's solution.
    
    Request JSON:
        board: 9x9 list of integers (0-9, where 0 = empty)
    
    Returns:
        JSON: {'incorrect': [[row, col], ...]} on success
        JSON: {'error': 'message'} on error (400)
    """
    try:
        # Parse JSON (may raise ValueError if malformed)
        data = request.get_json(force=True)
        
    except Exception as e:
        return jsonify({'error': 'Malformed JSON in request body'}), 400
    
    if data is None:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    # Extract and validate board
    board = data.get('board')
    is_valid, error_msg = validate_board(board)
    
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Check if player has an active game
    solution = session.get('solution')
    
    if solution is None:
        return jsonify({'error': 'No active game. Start a new game with /new'}), 400
    
    # Check solution
    try:
        incorrect = []
        for i in range(sudoku_logic.SIZE):
            for j in range(sudoku_logic.SIZE):
                if board[i][j] != solution[i][j]:
                    incorrect.append([i, j])
        
        return jsonify({'incorrect': incorrect})
        
    except Exception as e:
        return jsonify({'error': 'Error checking solution'}), 500

if __name__ == '__main__':
    app.run(debug=True)