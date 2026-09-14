from flask import Flask, render_template, jsonify, request, session
import sudoku_logic
import os
import random

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


def get_empty_cells(board):
    """
    Find all empty cells (value = 0) in a Sudoku board.
    
    Args:
        board: 9x9 puzzle board
        
    Returns:
        List of (row, col) tuples for empty cells
        Example: [(0,1), (0,2), (1,4), ...]
        Returns empty list if no empty cells found
    """
    empty = []
    for i in range(sudoku_logic.SIZE):
        for j in range(sudoku_logic.SIZE):
            if board[i][j] == 0:  # 0 = empty cell
                empty.append((i, j))
    return empty


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
    session['hints_used'] = 0  # Initialize hint counter for new game
    session.modified = True
    
    return jsonify({'puzzle': puzzle})

@app.route('/check', methods=['POST'])
def check_solution():
    """
    Validate submitted board for Sudoku violations and correctness.
    
    Detects:
    - Sudoku rule violations (row/column/3x3 box conflicts)
    - Incorrect values vs solution
    - Puzzle completion status
    
    Request JSON:
        board: 9x9 list of integers (0-9, where 0 = empty)
    
    Returns (200):
        {
            'conflicts': [[row, col], ...],  # Cells violating Sudoku rules
            'incorrect': [[row, col], ...],  # Cells with wrong values
            'is_complete': bool,             # All cells filled?
            'is_solved': bool                # Puzzle solved correctly?
        }
    
    Errors (400):
        {'error': 'message'}
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
    
    # Check for Sudoku rule violations (conflicts)
    try:
        conflicts = sudoku_logic.find_conflicts(board)
        
        # Check for incorrect values against solution
        incorrect = []
        for i in range(sudoku_logic.SIZE):
            for j in range(sudoku_logic.SIZE):
                if board[i][j] != 0 and board[i][j] != solution[i][j]:
                    if [i, j] not in incorrect:
                        incorrect.append([i, j])
        
        # Check if puzzle is complete (no empty cells)
        is_complete = all(board[i][j] != 0 
                         for i in range(sudoku_logic.SIZE) 
                         for j in range(sudoku_logic.SIZE))
        
        # Check if puzzle is correctly solved
        is_solved = (is_complete and 
                    len(conflicts) == 0 and 
                    len(incorrect) == 0 and
                    board == solution)
        
        return jsonify({
            'conflicts': conflicts,
            'incorrect': incorrect,
            'is_complete': is_complete,
            'is_solved': is_solved
        })
        
    except Exception as e:
        return jsonify({'error': 'Error checking solution'}), 500

@app.route('/hint', methods=['POST'])
def hint():
    """
    Provide a hint by revealing one empty cell from the current puzzle.
    
    Returns:
        JSON: {
            'row': int,           # Row of hinted cell (0-8)
            'col': int,           # Column of hinted cell (0-8)
            'value': int,         # Correct value (1-9)
            'hints_used': int,    # Total hints used in this game
            'puzzle': [[...]]     # Updated puzzle with hint filled
        }
        
    Errors:
        400: No active game or no empty cells remaining
    """
    try:
        # Check if player has an active game
        puzzle = session.get('puzzle')
        solution = session.get('solution')
        
        if puzzle is None or solution is None:
            return jsonify({'error': 'No active game. Start a new game with /new'}), 400
        
        # Find all empty cells in current puzzle
        empty_cells = get_empty_cells(puzzle)
        
        if not empty_cells:
            return jsonify({'error': 'No empty cells remaining - puzzle complete!'}), 400
        
        # Pick a random empty cell
        row, col = random.choice(empty_cells)
        
        # Get correct value from solution
        correct_value = solution[row][col]
        
        # Fill the cell in the puzzle
        puzzle[row][col] = correct_value
        
        # Increment hint counter
        hints_used = session.get('hints_used', 0) + 1
        
        # Update session
        session['puzzle'] = puzzle
        session['hints_used'] = hints_used
        session.modified = True
        
        return jsonify({
            'row': row,
            'col': col,
            'value': correct_value,
            'hints_used': hints_used,
            'puzzle': puzzle
        })
        
    except Exception as e:
        return jsonify({'error': 'Error providing hint'}), 500

if __name__ == '__main__':
    app.run(debug=True)