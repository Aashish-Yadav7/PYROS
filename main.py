"""
main.py
Pyros's GUI entry point.

Layout: chat on the left. On the right, our OWN local globe (Three.js,
no Bolt dependency, no logos, transparent background blending into the
space theme) on top, with a bordered/structured news panel below it,
populated from news.py with real fetched, clickable headlines.
"""

import os
import re
import sys
import webbrowser

# Must be set before QApplication is created - fixes black WebGL screen on
# systems where Chromium's GPU blocklist or drivers block hardware rendering.
# --use-gl=angle --use-angle=d3d11warp forces a pure-software renderer that
# works on any Windows machine regardless of GPU/driver support.
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--ignore-gpu-blocklist --disable-gpu-sandbox --disable-gpu-driver-bug-workarounds "
    "--use-gl=angle --use-angle=d3d11"
)

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import QThread, pyqtSignal, QUrl, QTimer, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

import memory
import brain
import news
from identity import CREATOR


class LoggingWebPage(QWebEnginePage):
    """Forwards the globe's browser console messages to our own terminal,
    so we can actually see JS/WebGL errors instead of a silent black screen."""
    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"[globe console] {message} (line {line})")

GLOBE_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "globe.html")
NEWS_REFRESH_MS = 20 * 60 * 1000  # match news.py's cache window (20 minutes)

_PLANET_NAMES = (
    "mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "sun",
    "moon", "phobos", "deimos", "io", "europa", "ganymede", "callisto",
    "titan", "titania", "triton",
)
_ZOOM_OUT_PHRASES = ("zoom out", "solar system", "show all planets", "whole system", "zoom all the way out")
_ACTION_VERBS = (
    "zoom", "show", "go to", "focus", "take me to", "navigate to", "fly to",
    "warp to", "look at", "move to", "head to", "bring me to",
)


def _detect_zoom_command(user_message: str) -> str | None:
    """
    Check if the user's message is a zoom command.
    Returns 'zoom_out', a planet/moon name, or None.
    """
    lowered = user_message.lower()
    if any(phrase in lowered for phrase in _ZOOM_OUT_PHRASES):
        return "zoom_out"
    for planet in _PLANET_NAMES:
        if planet in lowered and any(verb in lowered for verb in _ACTION_VERBS):
            return planet
    return None

SPACE_STYLESHEET = """
QWidget {
    background-color: #05060a;
    color: #e8e8ec;
    font-family: Segoe UI, sans-serif;
    font-size: 14px;
}
QTextEdit, QListWidget {
    background-color: #0d0f16;
    border: 1px solid #262a38;
    border-radius: 8px;
    padding: 8px;
}
QLineEdit {
    background-color: #0d0f16;
    border: 1px solid #2a2e3d;
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
    background-color: #2a2b38;
}
QListWidget::item {
    padding: 8px 4px;
    border-bottom: 1px solid #1c1f2b;
}
QScrollBar:vertical {
    background: #0d0f16;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #3a3d4d;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #4c4f63;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
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


class NewsFetchThread(QThread):
    """Fetches news in the background so the UI doesn't freeze."""
    news_ready = pyqtSignal(list)

    def run(self):
        result = news.get_headlines_for_display(target_count=200)
        self.news_ready.emit(result)


class PyrosWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PYROS")
        self.resize(1150, 720)
        self.setStyleSheet(SPACE_STYLESHEET)

        self.history = memory.load_history()
        self.user_name = memory.get_user_name()
        self.preferred_address = memory.get_preferred_address()

        # --- Overall layout: chat on the left, globe+news fixed on the right ---
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

        # Right: globe on top (no border, blends into space bg), news below (bordered)
        right_panel = QVBoxLayout()

        self.globe_view = QWebEngineView()
        self.globe_view.setPage(LoggingWebPage(self.globe_view))
        self.globe_view.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        self.globe_view.settings().setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        self.globe_view.setUrl(QUrl.fromLocalFile(GLOBE_HTML_PATH))
        self.globe_view.setFixedWidth(420)
        self.globe_view.setFixedHeight(360)
        self.globe_view.setStyleSheet("border: none; background: #05060a;")
        right_panel.addWidget(self.globe_view)

        self.news_list = QListWidget()
        self.news_list.setFixedWidth(420)
        self.news_list.setWordWrap(True)
        self.news_list.itemClicked.connect(self._open_article)
        right_panel.addWidget(self.news_list)

        refresh_button = QPushButton("Refresh News")
        refresh_button.clicked.connect(self.refresh_news)
        right_panel.addWidget(refresh_button)

        main_layout.addLayout(chat_panel, stretch=2)
        main_layout.addLayout(right_panel, stretch=1)

        self.setLayout(main_layout)

        # --- Onboarding, if first run ---
        if not self.user_name or not self.preferred_address:
            self._run_onboarding()
        else:
            self._show_pyros(f"Got it, {self.preferred_address}. What's on your mind?")

        # --- Load news on startup, then auto-refresh periodically ---
        self.refresh_news()
        self.news_timer = QTimer()
        self.news_timer.timeout.connect(self.refresh_news)
        self.news_timer.start(NEWS_REFRESH_MS)

    def refresh_news(self):
        self.news_thread = NewsFetchThread()
        self.news_thread.news_ready.connect(self._populate_news)
        self.news_thread.start()

    def _populate_news(self, articles: list):
        self.news_list.clear()
        for article in articles:
            title = article.get("title", "").strip()
            url = article.get("url", "").strip()
            category = article.get("category", "")
            if not title:
                continue
            item = QListWidgetItem(f"{title}\n{category}")
            item.setData(Qt.ItemDataRole.UserRole, url)
            self.news_list.addItem(item)

    def _open_article(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            webbrowser.open(url)

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

        # Check if this is a globe zoom command
        zoom_target = _detect_zoom_command(user_text)
        if zoom_target:
            if zoom_target == "zoom_out":
                self.globe_view.page().runJavaScript("window.zoomOutSolarSystem();")
                self._show_pyros("Zooming out to show the whole solar system.")
            else:
                self.globe_view.page().runJavaScript(f"window.zoomToPlanet('{zoom_target}');")
                self._show_pyros(f"Zooming in on {zoom_target.title()}.")
            return

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