import sys
import sqlite3
from datetime import datetime
import json
import re
import textwrap
import html as _html
from ai import generate_roadmap

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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
        created_at TEXT
    )
"""
)

conn.commit()



# =========================
# MAIN PAGE
# =========================

class MainPage(QWidget):
    def __init__(self, dashboard_page):
        super().__init__()

        self.dashboard_page = dashboard_page

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
        self.topic_input.setPlaceholderText("What's the topic to learn today?")
        self.topic_input.setFixedHeight(36)
        left_col.addWidget(self.topic_input)

        # Generate Button
        self.generate_button = QPushButton("Generate Roadmap")
        self.generate_button.setFixedHeight(36)
        self.generate_button.clicked.connect(self.generate_learning_plan)
        left_col.addWidget(self.generate_button)

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

    def _refresh_checklist_colors(self, item):
        state = item.checkState(0)
        color = QColor('#7f8c8d') if state == Qt.Checked else QColor('white')
        item.setForeground(0, color)

        for i in range(item.childCount()):
            self._refresh_checklist_colors(item.child(i))

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

        cursor.execute(
            "INSERT INTO learning_sessions (topic, roadmap, created_at) VALUES (?, ?, ?)",
            (topic, roadmap_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )

        conn.commit()
        self.dashboard_page.load_sessions()


# =========================
# DASHBOARD PAGE
# =========================

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-size: 14px;
            }

            QListWidget {
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
        """)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)

        self.title = QLabel("Learning Dashboard")
        self.layout.addWidget(self.title)

        self.sessions_list = QListWidget()
        self.layout.addWidget(self.sessions_list)

        self.setLayout(self.layout)

        self.load_sessions()

    def load_sessions(self):
        self.sessions_list.clear()

        cursor.execute(
            "SELECT topic, created_at FROM learning_sessions ORDER BY id DESC"
        )

        sessions = cursor.fetchall()

        for topic, date in sessions:
            self.sessions_list.addItem(f"{topic}  •  {date}")


# =========================
# MAIN WINDOW
# =========================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AI Learning Tracker")
        self.resize(1000, 700)

        self.stacked_widget = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.main_page = MainPage(self.dashboard_page)

        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.addWidget(self.dashboard_page)

        self.setCentralWidget(self.stacked_widget)

        # Button Navigation
        self.main_page.dashboard_button.clicked.connect(self.open_dashboard)

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