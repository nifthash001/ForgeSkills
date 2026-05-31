import sys
import sqlite3
from datetime import datetime
import json
import re
import textwrap
import html as _html
from ai import generate_roadmap
from tracking import compute_checklist_progress, format_progress

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QCategoryAxis,
    QValueAxis,
    QPieSeries,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QListWidget,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QStackedWidget,
    QMessageBox,
)

# =========================
# DATABASE SETUP
# =========================

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS learning_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT,
        roadmap TEXT,
        primary_focus TEXT,
        secondary_focus TEXT,
        progress INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 0,
        checklist_state TEXT DEFAULT '[]',
        created_at TEXT,
        last_updated TEXT
    )
"""
)

conn.commit()

cursor.execute("PRAGMA table_info(learning_sessions)")
columns = [row[1] for row in cursor.fetchall()]
if "primary_focus" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN primary_focus TEXT DEFAULT ''")
if "secondary_focus" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN secondary_focus TEXT DEFAULT ''")
if "progress" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN progress INTEGER DEFAULT 0")


cursor.execute("PRAGMA table_info(learning_sessions)")
columns = [row[1] for row in cursor.fetchall()]
if "primary_focus" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN primary_focus TEXT DEFAULT ''")
if "secondary_focus" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN secondary_focus TEXT DEFAULT ''")
if "progress" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN progress INTEGER DEFAULT 0")
if "is_active" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN is_active INTEGER DEFAULT 0")
if "checklist_state" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN checklist_state TEXT DEFAULT '[]'")
if "last_updated" not in columns:
    cursor.execute("ALTER TABLE learning_sessions ADD COLUMN last_updated TEXT")

conn.commit()

# =========================
# MAIN PAGE
# =========================

class MainPage(QWidget):
    def __init__(self, dashboard_page):
        super().__init__()

        self.dashboard_page = dashboard_page
        self.active_session_id = None

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-size: 14px;
            }

            QLineEdit {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 10px;
                color: white;
            }

            QTextEdit {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 10px;
                color: white;
            }

            QListWidget {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 10px;
                color: white;
            }

            QPushButton {
                background-color: #3A7AFE;
                border: none;
                border-radius: 10px;
                padding: 10px;
                color: white;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #5B92FF;
            }
        """)

        # Main horizontal split: left = input/output, right = checklist
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(20)

        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        left_col.setContentsMargins(0, 0, 0, 0)

        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        right_col.setContentsMargins(0, 0, 0, 0)

        # Title
        self.title = QLabel("AI Learning Tracker")
        self.title.setStyleSheet("font-size: 26px; font-weight: 700; margin-bottom:8px;")
        left_col.addWidget(self.title)

        # Input Topic
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("What skill do you want to learn?")
        self.topic_input.setFixedHeight(36)
        left_col.addWidget(self.topic_input)

        # Generate Button
        self.generate_button = QPushButton("Generate Roadmap")
        self.generate_button.setFixedHeight(36)
        self.generate_button.clicked.connect(self.generate_learning_plan)
        left_col.addWidget(self.generate_button)

        # Active session status
        self.active_label = QLabel("No active plan")
        self.active_label.setStyleSheet("font-size:12px; color:#9aa7c6;")
        left_col.addWidget(self.active_label)

        # Roadmap Output
        self.output_box = QTextEdit()
        self.output_box.setPlaceholderText("AI roadmap output will appear here...")
        self.output_box.setReadOnly(True)
        self.output_box.setAcceptRichText(True)
        self.output_box.setMinimumWidth(520)
        self.output_box.setStyleSheet("QTextEdit { font-size: 13px; }")
        left_col.addWidget(self.output_box, 1)

        # Checklist
        # Checklist (right column)
        checklist_label = QLabel("Checklist")
        checklist_label.setStyleSheet("font-size:18px; font-weight:600; margin-bottom:6px;")
        right_col.addWidget(checklist_label)

        self.progress_label = QLabel("Progress: 0%")
        self.progress_label.setStyleSheet("font-size:13px; color:#9aa7c6; margin-bottom:6px;")
        right_col.addWidget(self.progress_label)

        self.checklist = QTreeWidget()
        self.checklist.setHeaderHidden(True)
        self.checklist.setRootIsDecorated(True)
        self.checklist.setItemsExpandable(True)
        self.checklist.setWordWrap(True)
        self.checklist.setUniformRowHeights(False)
        self.checklist.setTextElideMode(Qt.ElideNone)
        self.checklist.setStyleSheet(
            "QTreeView::item { padding: 10px 8px; } QTreeWidget { min-width: 360px; }")
        self.checklist.itemChanged.connect(self._on_check_changed)
        right_col.addWidget(self.checklist, 1)

        # Dashboard Button
        self.dashboard_button = QPushButton("Open Dashboard")
        self.dashboard_button.setFixedHeight(36)
        right_col.addWidget(self.dashboard_button)

        # assemble columns
        self.layout.addLayout(left_col, 2)
        self.layout.addLayout(right_col, 1)

        self.setLayout(self.layout)

    def _on_check_changed(self, item, column):
        if column != 0 or item is None:
            return

        state = item.checkState(column)

        # Prevent recursion while updating related items.
        self.checklist.blockSignals(True)

        # propagate parent state to children
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)

        # if child changed, update parent state
        parent = item.parent()
        if parent is not None:
            all_checked = True
            any_checked = False
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.checkState(0) == Qt.Checked:
                    any_checked = True
                else:
                    all_checked = False

            if all_checked:
                parent.setCheckState(0, Qt.Checked)
            elif any_checked:
                parent.setCheckState(0, Qt.PartiallyChecked)
            else:
                parent.setCheckState(0, Qt.Unchecked)

        self.checklist.blockSignals(False)

        self._refresh_checklist_colors(item)
        if parent is not None:
            self._refresh_checklist_colors(parent)

        self._refresh_progress_label()

        if self.active_session_id:
            self._save_active_session_state(self.active_session_id)

    def _refresh_checklist_colors(self, item):
        state = item.checkState(0)
        color = QColor('#7f8c8d') if state == Qt.Checked else QColor('white')
        item.setForeground(0, color)

        for i in range(item.childCount()):
            self._refresh_checklist_colors(item.child(i))

    def _refresh_progress_label(self):
        progress_percent = compute_checklist_progress(self.checklist)
        self.progress_label.setText(format_progress(progress_percent))

    def _save_active_session_state(self, session_id):
        """Save the current checklist state and progress to the active session."""
        progress_percent = compute_checklist_progress(self.checklist)
        checklist_state = self._serialize_checklist()
        cursor.execute(
            "UPDATE learning_sessions SET progress = ?, checklist_state = ?, last_updated = ? WHERE id = ?",
            (progress_percent, checklist_state, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session_id),
        )
        conn.commit()

    def _serialize_checklist(self):
        """Serialize the current checklist state to JSON."""
        state = []
        for idx in range(self.checklist.topLevelItemCount()):
            item = self.checklist.topLevelItem(idx)
            state.append(self._serialize_item(item))
        return json.dumps(state)

    def _serialize_item(self, item):
        """Recursively serialize a checklist item and its children."""
        checked = item.checkState(0) == Qt.Checked
        children = []
        for idx in range(item.childCount()):
            child = item.child(idx)
            children.append(self._serialize_item(child))
        return {"checked": checked, "children": children}

    def _deserialize_checklist(self, state_json):
        """Recursively restore checklist item state from JSON."""
        try:
            state = json.loads(state_json)
        except Exception:
            return

        if isinstance(state, list) and len(state) > 0:
            for idx, item_state in enumerate(state):
                if idx < self.checklist.topLevelItemCount():
                    item = self.checklist.topLevelItem(idx)
                    self._deserialize_item(item, item_state)

    def _deserialize_item(self, item, state):
        """Recursively restore an item's checked state."""
        if state.get("checked"):
            item.setCheckState(0, Qt.Checked)
        else:
            item.setCheckState(0, Qt.Unchecked)

        children = state.get("children", [])
        for idx, child_state in enumerate(children):
            if idx < item.childCount():
                child = item.child(idx)
                self._deserialize_item(child, child_state)

    def _load_active_session(self):
        """Load the active session from the database."""
        cursor.execute(
            "SELECT id, topic, roadmap, primary_focus, secondary_focus, progress, checklist_state FROM learning_sessions WHERE is_active = 1 LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            self.active_label.setText("No active plan")
            return

        session_id, topic, roadmap_json, primary_focus, secondary_focus, progress, checklist_state = row
        self.active_session_id = session_id
        self.topic_input.setText(topic)

        try:
            steps = json.loads(roadmap_json)
        except Exception:
            steps = []

        self.checklist.clear()
        self.checklist.blockSignals(True)

        for step_data in steps:
            if isinstance(step_data, dict):
                title = str(step_data.get('title', 'Untitled step'))
                estimate = str(step_data.get('estimate', '')).strip()
                subtasks = step_data.get('subtasks', []) or []
            else:
                title = str(step_data)
                estimate = ''
                subtasks = []

            display_text = title
            if estimate:
                display_text += f"  •  {estimate}"
            display_text = textwrap.fill(display_text, width=45)

            parent = QTreeWidgetItem([display_text])
            parent.setFlags(parent.flags() | Qt.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.Unchecked)
            self.checklist.addTopLevelItem(parent)

            for subtask in subtasks:
                child_text = textwrap.fill(str(subtask), width=45)
                child = QTreeWidgetItem([child_text])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                parent.addChild(child)

            parent.setExpanded(False)

        self.checklist.blockSignals(False)
        self._deserialize_checklist(checklist_state)
        self.progress_label.setText(format_progress(progress))

        focus_text = f"Active: {primary_focus}"
        if secondary_focus:
            focus_text += f" + {secondary_focus}"
        self.active_label.setText(focus_text)

        html_parts = ['<div style="font-family:system-ui, sans-serif; color: #ecf0f1;">']
        if primary_focus:
            html_parts.append(f"<div style='margin-bottom:8px; color:#9aa7c6;'><strong>Primary:</strong> {_html.escape(primary_focus)}</div>")
        if secondary_focus:
            html_parts.append(f"<div style='margin-bottom:8px; color:#9aa7c6;'><strong>Side quest:</strong> {_html.escape(secondary_focus)}</div>")
        for i, step_data in enumerate(steps, 1):
            if isinstance(step_data, dict):
                title = _html.escape(str(step_data.get('title', '')))
                estimate = _html.escape(str(step_data.get('estimate', '')))
                subtasks = step_data.get('subtasks', []) or []
                html_parts.append(f"<div style='margin-bottom:12px;'><div style='font-weight:700; color:#dcdcdc;'>Step {i}. {title}</div>")
                if estimate:
                    html_parts.append(f"<div style='color:#9aa7c6; font-size:12px; margin-bottom:6px;'>Estimate: {estimate}</div>")
                if subtasks:
                    html_parts.append("<ul style='margin-top:4px; margin-bottom:10px; color:#bdc3c7; padding-left:18px;'>")
                    for sub in subtasks:
                        html_parts.append(f"<li>{_html.escape(str(sub))}</li>")
                    html_parts.append("</ul>")
                html_parts.append("</div>")
        html_parts.append('</div>')
        self.output_box.setHtml('\n'.join(html_parts))

    def _build_secondary_focus_section(self, focus):
        if not focus:
            return None

        return {
            'title': f"Side quest: {focus}",
            'estimate': 'Optional',
            'subtasks': [
                f"Explore {focus} concepts as a supporting skill",
                f"Build one small side project or exercise using {focus}",
                f"Link this skill back to the main roadmap tasks",
            ],
        }

    def generate_learning_plan(self):
        topic = self.topic_input.text().strip()

        if not topic:
            QMessageBox.warning(self, "Missing Topic", "Please enter a learning topic.")
            return

        roadmap = generate_roadmap(topic)

        self.checklist.clear()
        self.checklist.blockSignals(True)

        steps = []
        if isinstance(roadmap, list):
            steps = roadmap
        else:
            try:
                steps = json.loads(roadmap)
            except Exception:
                steps = []

        if not isinstance(steps, list):
            steps = []

        for step_data in steps:
            if isinstance(step_data, dict):
                title = str(step_data.get('title', 'Untitled step'))
                estimate = str(step_data.get('estimate', '')).strip()
                subtasks = step_data.get('subtasks', []) or []
            else:
                title = str(step_data)
                estimate = ''
                subtasks = []

            display_text = title
            if estimate:
                display_text += f"  •  {estimate}"
            display_text = textwrap.fill(display_text, width=45)

            parent = QTreeWidgetItem([display_text])
            parent.setFlags(parent.flags() | Qt.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.Unchecked)
            self.checklist.addTopLevelItem(parent)

            for subtask in subtasks:
                child_text = textwrap.fill(str(subtask), width=45)
                child = QTreeWidgetItem([child_text])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                parent.addChild(child)

            parent.setExpanded(False)

        self.checklist.blockSignals(False)

        progress_percent = compute_checklist_progress(self.checklist)
        self.progress_label.setText(format_progress(progress_percent))

        if steps:
            html_parts = ['<div style="font-family:system-ui, sans-serif; color: #ecf0f1;">']
            for i, step_data in enumerate(steps, 1):
                if isinstance(step_data, dict):
                    title = _html.escape(str(step_data.get('title', '')))
                    estimate = _html.escape(str(step_data.get('estimate', '')))
                    subtasks = step_data.get('subtasks', []) or []
                    html_parts.append(f"<div style='margin-bottom:12px;'><div style='font-weight:700; color:#dcdcdc;'>Step {i}. {title}</div>")
                    if estimate:
                        html_parts.append(f"<div style='color:#9aa7c6; font-size:12px; margin-bottom:6px;'>Estimate: {estimate}</div>")
                    if subtasks:
                        html_parts.append("<ul style='margin-top:4px; margin-bottom:10px; color:#bdc3c7; padding-left:18px;'>")
                        for sub in subtasks:
                            html_parts.append(f"<li>{_html.escape(str(sub))}</li>")
                        html_parts.append("</ul>")
                    html_parts.append("</div>")
                else:
                    safe = _html.escape(str(step_data))
                    html_parts.append(f"<div style='margin-bottom:10px;'><span style='font-weight:700; color:#dcdcdc;'>Step {i}.</span> <span style='color:#bdc3c7'>{safe}</span></div>")
            html_parts.append('</div>')
            self.output_box.setHtml('\n'.join(html_parts))
        else:
            self.output_box.setPlainText(str(roadmap))

        try:
            roadmap_json = json.dumps(steps)
        except Exception:
            roadmap_json = str(roadmap)

        set_active = QMessageBox.question(
            self,
            "Set as active plan?",
            "Would you like to set this roadmap as your active primary plan? You can resume this anytime you restart the app.",
            QMessageBox.Yes | QMessageBox.No,
        )

        primary_focus = ""
        secondary_focus = ""

        if set_active == QMessageBox.Yes:
            if steps:
                first_step = steps[0]
                primary_focus = first_step.get('title', 'Core focus') if isinstance(first_step, dict) else str(first_step)

            add_side_quest = QMessageBox.question(
                self,
                "Add side quest?",
                "Would you like to add a side quest / secondary skill to this roadmap?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if add_side_quest == QMessageBox.Yes:
                secondary_focus_text, ok = QInputDialog.getText(
                    self,
                    "Side quest skill",
                    "Enter a secondary skill or side quest:",
                )
                if ok and secondary_focus_text.strip():
                    secondary_focus = secondary_focus_text.strip()
                    secondary_section = self._build_secondary_focus_section(secondary_focus)
                    steps.append(secondary_section)
                    roadmap_json = json.dumps(steps)

            cursor.execute("UPDATE learning_sessions SET is_active = 0")
            cursor.execute(
                "INSERT INTO learning_sessions (topic, roadmap, primary_focus, secondary_focus, progress, is_active, checklist_state, created_at, last_updated) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
                (
                    topic,
                    roadmap_json,
                    primary_focus,
                    secondary_focus,
                    progress_percent,
                    self._serialize_checklist(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            new_session_id = cursor.lastrowid
            self.active_session_id = new_session_id

            focus_text = f"Active: {primary_focus}"
            if secondary_focus:
                focus_text += f" + {secondary_focus}"
            self.active_label.setText(focus_text)
        else:
            cursor.execute(
                "INSERT INTO learning_sessions (topic, roadmap, primary_focus, secondary_focus, progress, is_active, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
                (
                    topic,
                    roadmap_json,
                    primary_focus,
                    secondary_focus,
                    progress_percent,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()

        self.dashboard_page.load_sessions()


# =========================
# DASHBOARD PAGE
# =========================

class DashboardPage(QWidget):
    def __init__(self, back_callback=None):
        super().__init__()
        self.back_callback = back_callback

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-size: 14px;
            }

            QTreeWidget {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 10px;
                color: white;
            }

            QLabel {
                font-size: 24px;
                font-weight: bold;
            }

            QPushButton {
                background-color: #3A7AFE;
                border: none;
                border-radius: 10px;
                padding: 10px;
                color: white;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #5B92FF;
            }

            QTextEdit {
                background-color: #1E1E1E;
                border: 1px solid #333;
                border-radius: 10px;
                color: white;
            }
        """)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(20)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel("Learning Dashboard")
        header_layout.addWidget(self.title, stretch=1)

        self.back_button = QPushButton("Back to Planner")
        self.back_button.setFixedHeight(36)
        self.back_button.clicked.connect(self._handle_back)
        header_layout.addWidget(self.back_button)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(20)
        self.layout.addLayout(header_layout)

        self.body_layout = QHBoxLayout()
        self.body_layout.setSpacing(16)

        self.sessions_grid = QTreeWidget()
        self.sessions_grid.setHeaderLabels(["Topic", "Primary", "Secondary", "Created", "Progress"])
        self.sessions_grid.setRootIsDecorated(False)
        self.sessions_grid.setItemsExpandable(False)
        self.sessions_grid.setAllColumnsShowFocus(True)
        self.sessions_grid.setAlternatingRowColors(True)
        self.sessions_grid.setSelectionMode(QTreeWidget.SingleSelection)
        self.sessions_grid.setIndentation(0)
        self.sessions_grid.currentItemChanged.connect(self._on_session_selected)

        header = self.sessions_grid.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        self.body_layout.addWidget(self.sessions_grid, 3)

        details_layout = QVBoxLayout()
        details_layout.setSpacing(12)

        self.details_title = QLabel("Session details")
        self.details_title.setStyleSheet("font-size:18px; font-weight:600;")
        details_layout.addWidget(self.details_title)

        self.details_view = QTextEdit()
        self.details_view.setReadOnly(True)
        self.details_view.setAcceptRichText(True)
        self.details_view.setMinimumWidth(320)
        details_layout.addWidget(self.details_view, 1)

        self.body_layout.addLayout(details_layout, 2)
        self.layout.addLayout(self.body_layout, 1)

        self.session_count_label = QLabel("")
        self.session_count_label.setStyleSheet("color:#9aa7c6;")
        self.layout.addWidget(self.session_count_label)

        self.chart_layout = QHBoxLayout()
        self.chart_layout.setSpacing(16)
        self.layout.addLayout(self.chart_layout, 1)

        self.setLayout(self.layout)

        self.load_sessions()

    def set_back_callback(self, callback):
        self.back_callback = callback

    def _handle_back(self):
        if callable(self.back_callback):
            self.back_callback()

    def _on_session_selected(self, current, previous):
        if current is None:
            self.details_view.clear()
            return

        session_id = current.data(0, Qt.UserRole)
        if session_id is None:
            self.details_view.clear()
            return

        cursor.execute(
            "SELECT topic, primary_focus, secondary_focus, roadmap, progress, created_at FROM learning_sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if not row:
            self.details_view.clear()
            return

        topic, primary, secondary, roadmap_json, progress, created_at = row
        try:
            steps = json.loads(roadmap_json)
        except Exception:
            steps = []

        html = [f"<div style='font-family:system-ui, sans-serif; color:#ecf0f1;'>"]
        html.append(f"<div style='font-size:16px; margin-bottom:10px;'><strong>{_html.escape(topic)}</strong></div>")
        html.append(f"<div style='margin-bottom:10px; color:#9aa7c6;'>Primary: {_html.escape(primary)} • Secondary: {_html.escape(secondary)}</div>")
        html.append(f"<div style='margin-bottom:12px; color:#bdc3c7;'>Progress: {progress}% • Created: {_html.escape(created_at)}</div>")
        if isinstance(steps, list):
            for i, step in enumerate(steps, 1):
                title = _html.escape(str(step.get('title', '')))
                estimate = _html.escape(str(step.get('estimate', '')))
                html.append(f"<div style='margin-bottom:10px;'><strong>Step {i}:</strong> {title}</div>")
                if estimate:
                    html.append(f"<div style='color:#9aa7c6; font-size:12px;margin-bottom:6px;'>Estimate: {estimate}</div>")
                subtasks = step.get('subtasks', []) or []
                if subtasks:
                    html.append("<ul style='margin-left:18px; color:#bdc3c7;'>")
                    for sub in subtasks:
                        html.append(f"<li>{_html.escape(str(sub))}</li>")
                    html.append("</ul>")
        html.append("</div>")
        self.details_view.setHtml(''.join(html))

    def load_sessions(self):
        self.sessions_grid.clear()
        self.chart_layout_parent = []
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        cursor.execute(
            "SELECT id, topic, primary_focus, secondary_focus, created_at, progress, is_active FROM learning_sessions ORDER BY id DESC"
        )

        sessions = cursor.fetchall()
        self.session_count_label.setText(f"{len(sessions)} saved session(s)")

        progress_series = QBarSet("Progress")
        focus_counts = {}
        categories = []

        for session_id, topic, primary, secondary, date, progress, is_active in sessions:
            item = QTreeWidgetItem([topic, primary, secondary, date, f"{progress}%"])
            item.setData(0, Qt.UserRole, session_id)
            if is_active:
                item.setForeground(0, QColor('#3A7AFE'))
                item.setForeground(1, QColor('#3A7AFE'))
                item.setForeground(2, QColor('#3A7AFE'))
                item.setForeground(3, QColor('#3A7AFE'))
                item.setForeground(4, QColor('#3A7AFE'))
            self.sessions_grid.addTopLevelItem(item)
            progress_series.append(progress)
            categories.append(topic if len(topic) <= 16 else topic[:13] + '...')
            focus_counts[primary or 'General'] = focus_counts.get(primary or 'General', 0) + 1
            if secondary:
                focus_counts[secondary] = focus_counts.get(secondary, 0) + 1

        chart = QChart()
        chart.setTitle("Session Progress")
        series = QBarSeries()
        series.append(progress_series)
        chart.addSeries(series)
        axis_x = QCategoryAxis()
        for index, label in enumerate(categories):
            axis_x.append(label, index)
        axis_x.setLabelsAngle(-45)
        axis_x.setRange(0, max(len(categories) - 1, 0))
        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setLabelFormat("%d")
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        chart.legend().setVisible(False)
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_layout.addWidget(chart_view, 2)

        pie = QPieSeries()
        for label, count in sorted(focus_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                slice_ = pie.append(label, count)
                slice_.setLabelVisible(True)

        pie_chart = QChart()
        pie_chart.setTitle("Focus Skill Distribution")
        pie_chart.addSeries(pie)
        pie_chart.legend().setVisible(True)
        pie_chart_view = QChartView(pie_chart)
        pie_chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_layout.addWidget(pie_chart_view, 1)

        if sessions:
            self.sessions_grid.setCurrentItem(self.sessions_grid.topLevelItem(0))
# =========================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AI Learning Tracker")
        self.resize(1000, 700)

        self.stacked_widget = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.main_page = MainPage(self.dashboard_page)
        self.dashboard_page.set_back_callback(self.open_main_page)

        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.addWidget(self.dashboard_page)

        self.setCentralWidget(self.stacked_widget)

        # Button Navigation
        self.main_page.dashboard_button.clicked.connect(self.open_dashboard)

        # Load active session on startup
        self.main_page._load_active_session()

    def open_main_page(self):
        self.stacked_widget.setCurrentWidget(self.main_page)

    def open_dashboard(self):
        self.dashboard_page.load_sessions()
        self.stacked_widget.setCurrentWidget(self.dashboard_page)


# =========================
# APPLICATION START
# =========================

app = QApplication(sys.argv)

window = MainWindow()
window.show()
print(sys.executable)

sys.exit(app.exec())