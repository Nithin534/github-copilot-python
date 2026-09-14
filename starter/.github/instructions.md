# Copilot Instructions — Sudoku Project

Hey Copilot — a few things to keep in mind while helping me on this project.

- A Flask web app for playing Sudoku. I'm upgrading a simple version with difficulty levels, hints, a timer, dark mode, and a top-10 leaderboard.

- Do not disturb the code design which is alredy present while initializing the new features and keep it simple.

-  Split sudoku logic into three parts; generating puzzles, solving/checking uniqueness, and validating moves (row/column/box conflicts).

- Keep functions small and clearly named, If a chunk of code needs a comment to explain what it does, it should probably be its own function instead. Add type hints and docstrings on non-obvious functions.

- Use `const`/`let`, never `var`. Keep "what's the current game state" separate from "update the screen" logic. Use event delegation for the board (one listener on the grid, not 81 separate ones).

- Testing: I'm using pytest, Every new piece of logic needs a test — don't skip tests just because something "obviously works."

- Focus on what I actually asked for, don't quietly rewrite unrelated things. Don't add new dependencies without telling me. If a request is ambiguous, ask instead of guessing.