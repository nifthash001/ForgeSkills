# AI Learning Tracker

A PySide6-based desktop application for generating and tracking personalized learning roadmaps using AI.

## Features

- **AI-Powered Roadmaps**: Generate structured learning plans for any topic using Ollama (qwen:4b model)
- **Interactive Checklist**: Track progress with hierarchical parent-child task checklists
- **Learning Dashboard**: View history of all learning sessions with timestamps
- **Dark Theme UI**: Modern dark interface with blue accent colors
- **SQLite Storage**: Persistent storage of learning sessions and roadmaps

## Requirements

- Python 3.8+
- PySide6
- Ollama (with qwen:4b model running locally, optional fallback available)

## Installation

```bash
# Clone or navigate to project directory
cd ForgeSkills

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install PySide6 ollama
```

## Running the Application

```bash
source .venv/bin/activate
python main.py
```

## Usage

1. **Enter a learning topic** in the input field (e.g., "Python learning roadmap")
2. **Click "Generate Roadmap"** to create a structured learning plan
3. **Check off completed items** in the checklist as you progress
4. **Open Dashboard** to view all past learning sessions

## Project Structure

See [CODE_STRUCTURE.md](CODE_STRUCTURE.md) for detailed architecture and module documentation.

## Database

The application uses SQLite (`database.db`) to store:
- Learning session topics
- Generated roadmaps (as JSON)
- Creation timestamps

## Notes

- If Ollama is unavailable, the app falls back to a demo roadmap
- Checklist items can be expanded/collapsed by clicking on parent tasks
- Parent tasks show partial check state when some children are checked
