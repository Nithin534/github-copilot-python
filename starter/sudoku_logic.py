import copy
import random
from typing import List, Tuple, Literal

SIZE = 9
EMPTY = 0

# ============================================================================
# DIFFICULTY LEVELS - Control puzzle difficulty via clue count
# ============================================================================

DIFFICULTY_LEVELS = {
    'easy': 45,      # More clues = less to solve = easier
    'medium': 35,    # Standard difficulty
    'hard': 25       # Fewer clues = more to solve = harder
}

# ============================================================================
# BOARD UTILITIES
# ============================================================================

def deep_copy(board: List[List[int]]) -> List[List[int]]:
    """Create an independent copy of a board."""
    return copy.deepcopy(board)

def create_empty_board() -> List[List[int]]:
    """Create a 9x9 empty Sudoku board filled with zeros."""
    return [[EMPTY for _ in range(SIZE)] for _ in range(SIZE)]

# ============================================================================
# SUDOKU VALIDATION - ROW, COLUMN, BOX CONFLICTS
# ============================================================================

def is_safe(board: List[List[int]], row: int, col: int, num: int) -> bool:
    """
    Check if placing num at (row, col) violates Sudoku rules.
    
    Returns False if num already exists in row, column, or 3x3 box.
    """
    # Check row and column
    for x in range(SIZE):
        if board[row][x] == num or board[x][col] == num:
            return False
    # Check 3x3 box
    start_row = row - row % 3
    start_col = col - col % 3
    for i in range(3):
        for j in range(3):
            if board[start_row + i][start_col + j] == num:
                return False
    return True

def find_conflicts(board: List[List[int]]) -> List[Tuple[int, int]]:
    """
    Find all cells that violate Sudoku rules (duplicates in row/col/box).
    
    Checks each non-empty cell to see if it conflicts with another cell
    in its row, column, or 3x3 box. Multiple conflicts of the same number
    in a region all return True (all duplicates are marked as conflicts).
    
    Args:
        board: 9x9 Sudoku board
        
    Returns:
        List of (row, col) tuples where board[row][col] violates Sudoku rules.
        Returns empty list if no conflicts found.
        
    Example:
        If row 0 has two 5's at columns 2 and 7, both (0,2) and (0,7) returned.
    """
    conflicts = []
    
    for row in range(SIZE):
        for col in range(SIZE):
            cell_value = board[row][col]
            
            # Skip empty cells (0 is never a conflict)
            if cell_value == EMPTY:
                continue
            
            is_conflict = False
            
            # Check for duplicate in the same row
            for x in range(SIZE):
                if x != col and board[row][x] == cell_value:
                    is_conflict = True
                    break
            
            if is_conflict:
                conflicts.append((row, col))
                continue
            
            # Check for duplicate in the same column
            for x in range(SIZE):
                if x != row and board[x][col] == cell_value:
                    is_conflict = True
                    break
            
            if is_conflict:
                conflicts.append((row, col))
                continue
            
            # Check for duplicate in the same 3x3 box
            start_row = row - row % 3
            start_col = col - col % 3
            for i in range(3):
                for j in range(3):
                    box_row = start_row + i
                    box_col = start_col + j
                    if (box_row, box_col) != (row, col) and board[box_row][box_col] == cell_value:
                        is_conflict = True
                        break
                if is_conflict:
                    break
            
            if is_conflict:
                conflicts.append((row, col))
    
    return conflicts

# ============================================================================
# PUZZLE GENERATION - FILL COMPLETE BOARD
# ============================================================================

def fill_board(board: List[List[int]]) -> bool:
    """
    Fill board with valid Sudoku solution using backtracking.
    
    Modifies board in-place. Returns True if successfully filled.
    """
    for row in range(SIZE):
        for col in range(SIZE):
            if board[row][col] == EMPTY:
                possible = list(range(1, SIZE + 1))
                random.shuffle(possible)
                for candidate in possible:
                    if is_safe(board, row, col, candidate):
                        board[row][col] = candidate
                        if fill_board(board):
                            return True
                        board[row][col] = EMPTY
                return False
    return True

# ============================================================================
# PUZZLE VALIDATION - SOLUTION UNIQUENESS
# ============================================================================

def count_solutions(board: List[List[int]], max_count: int = 2) -> int:
    """
    Count number of solutions for a puzzle. Stops early at max_count.
    
    Args:
        board: Partially filled Sudoku puzzle (0 = empty cell)
        max_count: Stop counting after finding this many solutions (default 2)
    
    Returns:
        Number of solutions found (0, 1, or max_count if more exist)
        
    Purpose:
        Used to verify puzzle uniqueness. Early termination optimizes speed—
        we only need to know if 0, 1, or 2+ solutions exist.
    """
    board_copy = deep_copy(board)
    count = [0]
    
    def backtrack():
        if count[0] >= max_count:
            return
        
        for row in range(SIZE):
            for col in range(SIZE):
                if board_copy[row][col] == EMPTY:
                    for num in range(1, SIZE + 1):
                        if is_safe(board_copy, row, col, num):
                            board_copy[row][col] = num
                            backtrack()
                            board_copy[row][col] = EMPTY
                    return
        
        count[0] += 1
    
    backtrack()
    return count[0]

def is_valid_puzzle(board: List[List[int]]) -> bool:
    """
    Verify that puzzle has exactly one unique solution.
    
    Returns True only if count_solutions() == 1.
    """
    return count_solutions(board) == 1

# ============================================================================
# PUZZLE GENERATION - INTELLIGENT CELL REMOVAL
# ============================================================================

def remove_cells_safely(puzzle: List[List[int]], target_clues: int) -> List[List[int]]:
    """
    Remove cells from a complete solution to create a puzzle with unique solution.
    
    Args:
        puzzle: Complete filled Sudoku board (solution)
        target_clues: Desired number of clues in final puzzle
    
    Returns:
        Puzzle with exactly target_clues cells, guaranteed unique solution
        
    Algorithm:
        1. Start with complete solution
        2. Randomly select cells to remove
        3. After each removal, verify puzzle still has 1 solution
        4. If multiple solutions found → restore cell and try another
        5. Continue until reaching target_clues
    """
    puzzle_copy = deep_copy(puzzle)
    cells_to_remove = SIZE * SIZE - target_clues
    removed = 0
    
    # Create list of all cell coordinates, shuffle for randomness
    cells = [(i, j) for i in range(SIZE) for j in range(SIZE)]
    random.shuffle(cells)
    
    for row, col in cells:
        if removed >= cells_to_remove:
            break
        
        if puzzle_copy[row][col] != EMPTY:
            saved_value = puzzle_copy[row][col]
            puzzle_copy[row][col] = EMPTY
            
            # Check if puzzle still has unique solution
            if is_valid_puzzle(puzzle_copy):
                removed += 1
            else:
                # Multiple solutions found, restore cell
                puzzle_copy[row][col] = saved_value
    
    return puzzle_copy

# ============================================================================
# PUBLIC API - MAIN PUZZLE GENERATION
# ============================================================================

def generate_puzzle(
    clues: int = None,
    difficulty: Literal['easy', 'medium', 'hard'] = None
) -> Tuple[List[List[int]], List[List[int]]]:
    """
    Generate a Sudoku puzzle with guaranteed unique solution.
    
    Args:
        clues: Number of given cells in puzzle (optional)
        difficulty: Puzzle difficulty level (optional)
                   - 'easy': 45 clues (less to solve)
                   - 'medium': 35 clues (standard)
                   - 'hard': 25 clues (more to solve)
        
        If both clues and difficulty are provided, clues takes precedence.
        If neither provided, defaults to medium (35 clues).
    
    Returns:
        Tuple of (puzzle, solution)
        - puzzle: Partially filled board with target clues
        - solution: Complete filled board
    """
    # Determine clue count from difficulty or use explicit clues parameter
    if clues is not None:
        target_clues = clues
    elif difficulty is not None:
        if difficulty not in DIFFICULTY_LEVELS:
            raise ValueError(
                f"Invalid difficulty '{difficulty}'. "
                f"Must be one of: {', '.join(DIFFICULTY_LEVELS.keys())}"
            )
        target_clues = DIFFICULTY_LEVELS[difficulty]
    else:
        target_clues = DIFFICULTY_LEVELS['medium']  # Default: medium
    
    board = create_empty_board()
    fill_board(board)
    solution = deep_copy(board)
    puzzle = remove_cells_safely(board, target_clues)
    return puzzle, solution
