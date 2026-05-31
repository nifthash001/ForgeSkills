# Code Structure

## Overview

The AI Learning Tracker is organized into two main modules:

- **`ai.py`** - AI roadmap generation and text parsing
- **`tracking.py`** - Checklist progress calculation and formatting
- **`main.py`** - PySide6 GUI application with database integration

## Module Details

### ai.py

Handles all AI-related functionality for generating learning roadmaps.

### tracking.py

Handles checklist progress calculation for the main UI.

#### Functions

**`compute_checklist_progress(tree_widget: QTreeWidget) -> int`**
- Computes total and completed checklist items from a hierarchical `QTreeWidget`
- Returns an integer percent complete

**`format_progress(total_percent: int) -> str`**
- Formats a progress percentage for display in the UI

#### Behavior
- Counts every checkable task including parent and child items
- Returns `0` when the checklist is empty


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
- **Input**: `QLineEdit` for entering a learning skill/topic only
- **Generate Button**: Triggers roadmap generation from the topic
- **Active Session Status**: Shows the current active roadmap and focus status
- **Output**: `QTextEdit` displaying the AI-generated roadmap with HTML styling
- **Checklist**: `QTreeWidget` hierarchical task list with checkboxes for tracking progress
- **Progress Label**: Live percent complete, calculated from checked items
- **Navigation**: Button to open the dashboard

**Features:**
- Single topic input (no upfront focus skill fields)
- Parent-child checkbox propagation and partial state tracking
- Color dimming (gray) for completed items
- Automatic active session loading on app startup
- Checklist state and progress persistence to database
- Post-generation prompts to set as active and optionally add side quests
- Automatic session saving to database

**`DashboardPage` (QWidget)**
- **Title**: "Learning Dashboard" header
- **Session Table**: `QTreeWidget` showing topic, primary/secondary focus, creation date, and progress
  - Active session is highlighted in blue (#3A7AFE)
- **Session Details**: Select a session to preview roadmap and focus details
- **Charts**: `QChartView` widgets show progress trends and focus skill distribution
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
  primary_focus TEXT,  -- Primary skill/focus area
  secondary_focus TEXT,  -- Optional side quest
  progress INTEGER DEFAULT 0,  -- Completion percent (0-100)
  is_active INTEGER DEFAULT 0,  -- Flag for active session (0 or 1)
  checklist_state TEXT,  -- JSON serialization of all item check states
  created_at TEXT,
  last_updated TEXT  -- Timestamp of last progress update
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
- Validates topic input (must not be empty)
- Calls `generate_roadmap()` from ai module
- Builds tree widget items from roadmap steps
- Generates formatted HTML output
- Prompts user: "Set as active plan?" (Yes/No)
- If yes: optionally prompts for side quest, marks as `is_active=1`, clears other active sessions
- If no: saves as regular session with `is_active=0`
- Saves session to database with serialized checklist state

#### Data Flow

1. User enters skill/topic → `MainPage.topic_input`
2. Click "Generate" → `generate_learning_plan()`
3. Call `ai.generate_roadmap(topic)` → receives roadmap list
4. Build checklist items recursively from roadmap
5. Display HTML-formatted output
6. Prompt "Set as active?" → if yes, mark as `is_active=1` and optionally add side quest
7. Serialize checklist state to JSON and save to SQLite database
8. Update dashboard page
9. On next app startup, `MainWindow.__init__` calls `_load_active_session()` to restore

#### Session Persistence Methods

**`_serialize_checklist()` → str (JSON)**
- Converts all tree widget item check states to nested JSON structure
- Recursively processes parent and child items
- Stores both checked state and tree structure

**`_deserialize_checklist(state_json)` → None**
- Reconstructs tree widget item check states from JSON
- Recursively applies check states to match saved state
- Called by `_load_active_session()` to restore on app startup

**`_save_active_session_state(session_id)` → None**
- Updates active session in database with current progress and checklist state
- Triggered by `_on_check_changed()` every time a checkbox is checked/unchecked
- Saves: progress percent, checklist_state JSON, last_updated timestamp

**`_load_active_session()` → None**
- Called on app startup by `MainWindow.__init__`
- Queries database for session with `is_active=1`
- If found: loads roadmap, deserializes checklist state, displays session info
- If not found: clears UI for new session

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
