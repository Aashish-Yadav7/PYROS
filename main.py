"""
main.py
Pyros's GUI entry point. Run this instead of brain.py from now on.

Two-panel layout: chat on the left, live globe/news web view fixed on the
right (your Bolt project, embedded directly). Dark themed.

The LLM call runs in a background thread so the window never freezes
while she's thinking.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton,
)
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

import memory
import brain
from identity import CREATOR

# Change this if your Bolt project URL ever changes
GLOBE_URL = "https://rotating-earth-visua-bcxi.bolt.host"

DARK_STYLESHEET = """
QWidget {
    background-color: #1e1f26;
    color: #e8e8ec;
    font-family: Segoe UI, sans-serif;
    font-size: 14px;
}
QTextEdit {
    background-color: #26272f;
    border: 1px solid #33343d;
    border-radius: 8px;
    padding: 10px;
}
QLineEdit {
    background-color: #26272f;
    border: 1px solid #3a3b45;
    border-radius: 8px;
    padding: 8px;
}
QLineEdit:focus {
    border: 1px solid #6c63ff;
}
QPushButton {
    background-color: #6c63ff;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #7d75ff;
}
QPushButton:disabled {
    background-color: #44445a;
}
"""


class ThinkingThread(QThread):
    """Runs the LLM call in the background so the UI doesn't freeze."""
    reply_ready = pyqtSignal(str)

    def __init__(self, user_message, history, preferred_address):
        super().__init__()
        self.user_message = user_message
        self.history = history
        self.preferred_address = preferred_address

    def run(self):
        reply = brain.ask_pyros(self.user_message, self.history, self.preferred_address)
        self.reply_ready.emit(reply)


class PyrosWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PYROS")
        self.resize(1100, 700)
        self.setStyleSheet(DARK_STYLESHEET)

        self.history = memory.load_history()
        self.user_name = memory.get_user_name()
        self.preferred_address = memory.get_preferred_address()

        # --- Overall layout: chat on the left, globe fixed on the right ---
        main_layout = QHBoxLayout()

        # Left: chat panel
        chat_panel = QVBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_panel.addWidget(self.chat_display)

        input_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type a message...")
        self.input_box.returnPressed.connect(self.handle_send)
        input_row.addWidget(self.input_box)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.handle_send)
        input_row.addWidget(self.send_button)

        chat_panel.addLayout(input_row)

        # Right: live globe + news, fixed width
        globe_panel = QVBoxLayout()

        reload_button = QPushButton("Reload Globe")
        reload_button.clicked.connect(self._reload_globe)
        globe_panel.addWidget(reload_button)

        self.globe_view = QWebEngineView()
        self.globe_view.setUrl(QUrl(GLOBE_URL))
        self.globe_view.setFixedWidth(420)
        globe_panel.addWidget(self.globe_view)

        main_layout.addLayout(chat_panel, stretch=2)
        main_layout.addLayout(globe_panel, stretch=1)

        self.setLayout(main_layout)

        # --- Onboarding, if first run ---
        if not self.user_name or not self.preferred_address:
            self._run_onboarding()
        else:
            self._show_pyros(f"Got it, {self.preferred_address}. What's on your mind?")

    def _reload_globe(self):
        self.globe_view.setUrl(QUrl(GLOBE_URL))

    def _run_onboarding(self):
        """Very simple onboarding using the chat display itself."""
        if not self.user_name:
            self._show_pyros("Hey! Before we start, what's your name?")
        elif not self.preferred_address:
            self._show_pyros("What would you like me to call you going forward?")

    def _show_user(self, text: str):
        safe_text = text.replace("\n", "<br>")
        self.chat_display.append(f"<b style='color:#6c63ff'>You:</b> {safe_text}")

    def _show_pyros(self, text: str):
        safe_text = text.replace("\n", "<br>")
        self.chat_display.append(f"<b style='color:#ff6b9d'>Pyros:</b> {safe_text}<br>")

    def handle_send(self):
        user_text = self.input_box.text().strip()
        if not user_text:
            return
        self.input_box.clear()
        self._show_user(user_text)

        # Handle onboarding answers first
        if not self.user_name:
            self.user_name = user_text
            memory.set_user_name(user_text)
            if user_text.strip().lower() == CREATOR["name"].strip().lower():
                self._show_pyros(f"Recognized you as my creator, {user_text}. What would you like me to call you going forward?")
            else:
                self._show_pyros("Got it. What would you like me to call you going forward?")
            return

        if not self.preferred_address:
            self.preferred_address = user_text
            memory.set_preferred_address(user_text)
            self._show_pyros(f"Got it, {user_text}. What's on your mind?")
            return

        # Check if user wants to change address preference mid-chat
        new_preference = brain.detect_address_preference(user_text)
        if new_preference:
            memory.set_preferred_address(new_preference)
            self.preferred_address = new_preference

        # Disable input while she's thinking
        self.input_box.setEnabled(False)
        self.send_button.setEnabled(False)

        self.thread = ThinkingThread(user_text, self.history, self.preferred_address)
        self.thread.reply_ready.connect(lambda reply: self._on_reply(user_text, reply))
        self.thread.start()

    def _on_reply(self, user_text: str, reply: str):
        self._show_pyros(reply)

        memory.log_exchange(user_text, reply)
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})

        if "remember" in user_text.lower():
            memory.remember_fact(user_text)

        self.input_box.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_box.setFocus()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PyrosWindow()
    window.show()
    sys.exit(app.exec())