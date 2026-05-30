# Code Structure

## Overview

The AI Learning Tracker is organized into two main modules:

- **`ai.py`** - AI roadmap generation and text parsing
- **`main.py`** - PySide6 GUI application with database integration

## Module Details

### ai.py

Handles all AI-related functionality for generating learning roadmaps.

#### Functions

**`generate_roadmap(topic: str) -> list`**
- Main entry point for roadmap generation
- Accepts a topic string (e.g., "Python programming")
- Returns a list of roadmap step dictionaries

#### Roadmap Format

Each roadmap is a list of step objects:
```python
[
  {
    "title": "Step title",
    "estimate": "2 hours",  # Optional time estimate
    "subtasks": [
      "Subtask 1",
      "Subtask 2",
      ...
    ]
  },
  ...
]
```

#### Parsing Logic

When Ollama is available:
1. Sends prompt to qwen:4b model requesting JSON format
2. Attempts to parse JSON response directly
3. Falls back to extracting JSON array from text if needed
4. If response is plain text (numbered/bulleted), parses it into structured steps
5. Detects and expands raw text blocks containing numbered sections

When Ollama is unavailable:
- Returns a hardcoded demo roadmap with 3 steps

#### Helper Functions

- `_try_parse_json(content)` - Attempts JSON and literal_eval parsing
- `_extract_json_array(content)` - Extracts JSON array substring from text
- `_parse_plain_text_to_roadmap(content, topic)` - Converts plain text to roadmap structure
- `_is_raw_text_step(item)` - Detects single-subtask dicts containing formatted text
- `_explode_raw_text_step(item, topic)` - Splits raw text into multiple steps
- `_normalize_roadmap(parsed, topic)` - Normalizes mixed parsed output into standard format

### main.py

PySide6 desktop application with two pages and SQLite backend.

#### Components

**`MainPage` (QWidget)**
- **Title**: "AI Learning Tracker" header
- **Input**: `QLineEdit` for entering learning topic
- **Button**: "Generate Roadmap" to trigger roadmap generation
- **Output**: `QTextEdit` displaying formatted roadmap with HTML styling
- **Checklist**: `QTreeWidget` hierarchical task list with checkboxes
- **Navigation**: Button to open dashboard page

**Features:**
- Parent-child checkbox propagation
- Partial check state for parents with mixed children
- Color dimming (gray) for completed items
- HTML formatting for roadmap output
- Automatic session saving to database

**`DashboardPage` (QWidget)**
- **Title**: "Learning Dashboard" header
- **Sessions List**: `QListWidget` showing all past learning sessions
- Displays topic and creation timestamp for each session
- Sessions ordered by most recent first

**`MainWindow` (QMainWindow)**
- Top-level application window (1000x700)
- `QStackedWidget` for page switching
- Contains MainPage and DashboardPage
- Handles navigation between pages

#### Database Schema

**Table: `learning_sessions`**
```sql
CREATE TABLE learning_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT,
  roadmap TEXT,  -- JSON string of roadmap steps
  created_at TEXT
)
```

#### Styling

- **Background**: Dark theme (#121212)
- **Text**: White text with gray accents
- **Inputs**: Dark gray (#1E1E1E) with subtle borders
- **Buttons**: Blue (#3A7AFE) with hover effect (#5B92FF)
- **Borders**: Subtle gray (#333) with 10px border-radius
- **Completed Items**: Gray (#7f8c8d) text

#### Signal Handling

**`_on_check_changed(item, column)`**
- Triggered when any checkbox state changes
- Propagates state to all children
- Updates parent state based on children (all/partial/none checked)
- Blocks signals during updates to prevent recursion
- Refreshes colors recursively for visual feedback

**`generate_learning_plan()`**
- Validates topic input
- Calls `generate_roadmap()` from ai module
- Builds tree widget items from roadmap steps
- Generates formatted HTML output
- Saves session to database

#### Data Flow

1. User enters topic → `MainPage.topic_input`
2. Click "Generate" → `generate_learning_plan()`
3. Call `ai.generate_roadmap(topic)` → receives roadmap list
4. Build checklist items recursively from roadmap
5. Display HTML-formatted output
6. Save to SQLite database
7. Update dashboard page

## Dependencies

- **PySide6**: GUI framework (Qt6 Python bindings)
- **sqlite3**: Built-in Python database module
- **ollama**: Optional, for AI roadmap generation
- **json, re, html, datetime**: Standard library modules

## Error Handling

- **Fallback Roadmap**: If Ollama unavailable, demo roadmap is returned
- **Text Parsing Fallback**: If JSON parsing fails, plain text parsing is attempted
- **Empty Topic**: User is warned if topic input is empty
- **Database Errors**: Gracefully handle DB inserts with implicit rollback

## File I/O

- **Database**: `database.db` (created on first run in working directory)
- **PyCompile Cache**: `__pycache__/` directories auto-created
