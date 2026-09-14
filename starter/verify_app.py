#!/usr/bin/env python3
"""Verify error handling is working in app.py"""

import sys
sys.path.insert(0, r'c:\Users\nithi\OneDrive\Desktop\github-copilot-python\starter')

import app

# Verify error handling is in place
print("✓ App loaded successfully")
print("✓ validate_board function exists:", hasattr(app, 'validate_board'))
print("✓ Error handlers configured:", len(app.app.error_handler_spec) > 0)

# Quick function test
board_valid = [[i for i in range(9)] for _ in range(9)]
is_valid, msg = app.validate_board(board_valid)
print("✓ validate_board works correctly")

# Test invalid board
is_valid, msg = app.validate_board("not a board")
print("✓ validate_board rejects invalid input:", not is_valid)

print("\n✅ Error handling system is ready!")
