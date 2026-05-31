# AI Learning Tracker

A PySide6-based desktop application for generating and tracking personalized learning roadmaps using AI.

## Features

- **Single Topic Input**: Enter the skill you want to learn, generate a roadmap instantly
- **Active Session Tracking**: Mark a roadmap as your active primary plan and resume automatically when you restart the app
- **Side Quests**: Optionally add secondary skills as side quests to your active roadmap
- **Interactive Checklist**: Track progress with hierarchical parent-child task checklists
- **Progress Persistence**: Completed checklist items and progress percent are saved and restored automatically

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

1. **Enter a learning skill** in the input field (e.g., "Machine Learning")
2. **Click "Generate Roadmap"** to create a structured learning plan from AI
3. **Set as active** by confirming the prompt - your active roadmap will resume on next app restart
4. **Optionally add side quests** - secondary skills to explore alongside the main roadmap
5. **Check off completed items** in the checklist as you progress
6. **Progress is automatically saved** - close and restart the app to resume from where you left off
7. **Open Dashboard** to view all past learning sessions and charts of your learning journey

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
