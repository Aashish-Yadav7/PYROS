"""
main.py
Pyros's GUI entry point. Run this instead of brain.py from now on.

Wraps the same logic from brain.py + memory.py + personality.py, but in a
proper window instead of the terminal. The LLM call runs in a background
thread so the window never freezes while she's thinking.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel,
)
from PyQt6.QtCore import QThread, pyqtSignal

import memory
import brain
from identity import CREATOR


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
        self.resize(600, 700)

        self.history = memory.load_history()
        self.user_name = memory.get_user_name()
        self.preferred_address = memory.get_preferred_address()

        # --- Layout ---
        layout = QVBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        input_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type a message...")
        self.input_box.returnPressed.connect(self.handle_send)
        input_row.addWidget(self.input_box)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.handle_send)
        input_row.addWidget(self.send_button)

        layout.addLayout(input_row)
        self.setLayout(layout)

        # --- Onboarding, if first run ---
        if not self.user_name or not self.preferred_address:
            self._run_onboarding()
        else:
            self._show_pyros(f"Got it, {self.preferred_address}. What's on your mind?")

    def _run_onboarding(self):
        """Very simple onboarding using the chat display itself."""
        if not self.user_name:
            self._show_pyros("Hey! Before we start, what's your name?")
            self._onboarding_stage = "name"
        elif not self.preferred_address:
            self._show_pyros("What would you like me to call you going forward?")
            self._onboarding_stage = "address"

    def _show_user(self, text: str):
        self.chat_display.append(f"<b>You:</b> {text}")

    def _show_pyros(self, text: str):
        self.chat_display.append(f"<b>Pyros:</b> {text}<br>")

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