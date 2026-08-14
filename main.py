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
import traceback
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
import voice
from identity import CREATOR


class LoggingWebPage(QWebEnginePage):
    """Forwards the globe's browser console messages to our own terminal,
    so we can actually see JS/WebGL errors instead of a silent black screen."""
    def javaScriptConsoleMessage(self, level, message, line, source):
        print(f"[globe console] {message} (line {line})")

GLOBE_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "globe.html")
NEWS_REFRESH_MS = 20 * 60 * 1000  # match news.py's cache window (20 minutes)

import difflib

_PLANET_NAMES = (
    "mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune", "sun",
    "moon", "phobos", "deimos", "io", "europa", "ganymede", "callisto",
    "titan", "titania", "triton", "enceladus", "mimas", "oberon", "miranda",
    "pluto", "ceres",
)
_ZOOM_OUT_PHRASES = ("zoom out", "solar system", "show all planets", "whole system", "zoom all the way out")
_FREE_FLOAT_PHRASES = (
    "free float", "let me float", "float free", "free camera", "stop following",
    "release camera", "let me move freely", "unlock the camera", "unlock view",
)
_ACTION_VERBS = (
    "zoom", "show", "go to", "focus", "take me to", "navigate to", "fly to",
    "warp to", "look at", "move to", "head to", "bring me to",
)


def _fuzzy_match_planet(word: str) -> str | None:
    """Catches typos like 'satrun' -> 'saturn' using fuzzy string matching."""
    matches = difflib.get_close_matches(word, _PLANET_NAMES, n=1, cutoff=0.7)
    return matches[0] if matches else None


def _detect_zoom_command(user_message: str) -> str | None:
    """
    Check if the user's message is a zoom command.
    Returns 'zoom_out', 'free_float', a planet/moon name, or None.
    Tolerates common typos (e.g. 'satrun' -> 'saturn').
    """
    lowered = user_message.lower()

    if any(phrase in lowered for phrase in _FREE_FLOAT_PHRASES):
        return "free_float"
    if any(phrase in lowered for phrase in _ZOOM_OUT_PHRASES):
        return "zoom_out"

    words = lowered.replace(",", " ").replace(".", " ").split()

    if any(verb in lowered for verb in _ACTION_VERBS):
        # Exact match first
        for planet in _PLANET_NAMES:
            if planet in lowered:
                return planet
        # Fall back to fuzzy match against each word (catches typos)
        for word in words:
            match = _fuzzy_match_planet(word)
            if match:
                return match
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
    error_occurred = pyqtSignal(str)

    def __init__(self, user_message, history, preferred_address):
        super().__init__()
        self.user_message = user_message
        self.history = history
        self.preferred_address = preferred_address

    def run(self):
        try:
            reply = brain.ask_pyros(self.user_message, self.history, self.preferred_address)
            self.reply_ready.emit(reply)
        except Exception:
            err = traceback.format_exc()
            print(f"[ThinkingThread] CRASH:\n{err}")
            self.error_occurred.emit(err)


class NewsFetchThread(QThread):
    """Fetches news in the background so the UI doesn't freeze."""
    news_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            result = news.get_headlines_for_display(target_count=200)
            self.news_ready.emit(result)
        except Exception:
            err = traceback.format_exc()
            print(f"[NewsFetchThread] CRASH:\n{err}")
            self.error_occurred.emit(err)


class ListenThread(QThread):
    """Records mic + transcribes via Whisper in the background."""
    heard_text = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            text = voice.listen(duration_seconds=5)
            self.heard_text.emit(text)
        except Exception:
            err = traceback.format_exc()
            print(f"[ListenThread] CRASH:\n{err}")
            self.error_occurred.emit(err)


class SpeakThread(QThread):
    """Speaks text out loud in the background so playback doesn't freeze the UI."""
    finished_speaking = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            voice.speak(self.text)
            self.finished_speaking.emit()
        except Exception:
            err = traceback.format_exc()
            print(f"[SpeakThread] CRASH:\n{err}")
            self.error_occurred.emit(err)


class PyrosWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PYROS")
        self.resize(1150, 720)
        self.setStyleSheet(SPACE_STYLESHEET)

        self.history = memory.load_history()
        self.user_name = memory.get_user_name()
        self.preferred_address = memory.get_preferred_address()
        self._active_threads = []  # keeps thread objects alive until they finish (fixes audio cutoff bug)

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

        self.mic_button = QPushButton("🎤")
        self.mic_button.setFixedWidth(44)
        self.mic_button.clicked.connect(self.handle_mic_click)
        input_row.addWidget(self.mic_button)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.handle_send)
        input_row.addWidget(self.send_button)

        chat_panel.addLayout(input_row)

        voice_toggle_row = QHBoxLayout()
        self.voice_enabled = False
        self.voice_toggle_button = QPushButton("🔇 Voice replies: OFF")
        self.voice_toggle_button.clicked.connect(self.toggle_voice)
        voice_toggle_row.addWidget(self.voice_toggle_button)

        self.stop_button = QPushButton("⏹ Stop speaking")
        self.stop_button.clicked.connect(self.handle_stop_speaking)
        voice_toggle_row.addWidget(self.stop_button)

        chat_panel.addLayout(voice_toggle_row)

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

        # --- Idle self-talk: if you go quiet for a while, she speaks up on
        # her own (checking in, sharing a thought) instead of just waiting ---
        IDLE_TRIGGER_MS = 4 * 60 * 1000  # 4 minutes of no activity
        self.idle_timer = QTimer()
        self.idle_timer.setSingleShot(True)
        self.idle_timer.timeout.connect(self._trigger_idle_speech)
        self.idle_timer.start(IDLE_TRIGGER_MS)

    def _reset_idle_timer(self):
        self.idle_timer.stop()
        self.idle_timer.start(4 * 60 * 1000)

    def _trigger_idle_speech(self):
        """Called when there's been no user activity for a while - Pyros
        speaks up on her own instead of just sitting silently."""
        if not self.user_name or not self.preferred_address:
            self._reset_idle_timer()
            return  # don't self-talk during onboarding

        idle_prompt = (
            "(No input from the user for a few minutes. Say something short and "
            "natural on your own initiative - a quick observation, a check-in, "
            "or picking up on something from earlier. Keep it brief.)"
        )
        thread = ThinkingThread(idle_prompt, self.history, self.preferred_address)
        thread.reply_ready.connect(self._on_idle_reply)
        thread.error_occurred.connect(self._on_thread_error)
        self._track_thread(thread)
        thread.start()

    def _on_idle_reply(self, reply: str):
        self._show_pyros(reply)
        memory.log_exchange("(idle)", reply)
        self.history.append({"role": "assistant", "content": reply})
        if self.voice_enabled:
            speak_thread = SpeakThread(reply)
            speak_thread.error_occurred.connect(self._on_thread_error)
            self._track_thread(speak_thread)
            speak_thread.start()
        self._reset_idle_timer()

    def refresh_news(self):
        self.news_thread = NewsFetchThread()
        self.news_thread.news_ready.connect(self._populate_news)
        self.news_thread.error_occurred.connect(self._on_thread_error)
        self._track_thread(self.news_thread)
        self.news_thread.start()

    def _on_thread_error(self, error_text: str):
        """A background thread crashed - show it instead of silently dying."""
        print(f"[main] Background thread error:\n{error_text}")
        self._show_pyros(f"(Something went wrong in the background — check the terminal for details. I'm still here though.)")

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

    def _track_thread(self, thread):
        """
        Keep a real reference to this thread until it finishes, instead of
        overwriting self.xxx_thread (which let Python garbage-collect and
        kill still-running threads mid-task - the actual cause of audio
        cutting off mid-sentence).
        """
        self._active_threads.append(thread)
        thread.finished.connect(lambda: self._active_threads.remove(thread) if thread in self._active_threads else None)

    def toggle_voice(self):
        self.voice_enabled = not self.voice_enabled
        label = "🔊 Voice replies: ON" if self.voice_enabled else "🔇 Voice replies: OFF"
        self.voice_toggle_button.setText(label)

    def handle_stop_speaking(self):
        voice.stop_speaking()

    def handle_mic_click(self):
        self._reset_idle_timer()
        self.mic_button.setEnabled(False)
        self.mic_button.setText("🎙️...")
        self.listen_thread = ListenThread()
        self.listen_thread.heard_text.connect(self._on_heard)
        self.listen_thread.error_occurred.connect(self._on_thread_error)
        self._track_thread(self.listen_thread)
        self.listen_thread.start()

    def _on_heard(self, text: str):
        self.mic_button.setEnabled(True)
        self.mic_button.setText("🎤")
        if text:
            self.input_box.setText(text)
        else:
            self._show_pyros("(Didn't catch that, Boss — mic might be silent or unavailable.)")

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
        self._reset_idle_timer()
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
            elif zoom_target == "free_float":
                self.globe_view.page().runJavaScript("window.releaseFocus();")
                self._show_pyros("You're free to float anywhere now, Boss — drag, pan, and zoom wherever you like.")
            else:
                self.globe_view.page().runJavaScript(f"window.zoomToPlanet('{zoom_target}');")
                self._show_pyros(f"Zooming in on {zoom_target.title()}.")
            return

        # Disable input while she's thinking
        self.input_box.setEnabled(False)
        self.send_button.setEnabled(False)

        self.thread = ThinkingThread(user_text, self.history, self.preferred_address)
        self.thread.reply_ready.connect(lambda reply: self._on_reply(user_text, reply))
        self.thread.error_occurred.connect(self._on_thread_error)
        self._track_thread(self.thread)
        self.thread.start()

    def _on_reply(self, user_text: str, reply: str):
        self._show_pyros(reply)

        memory.log_exchange(user_text, reply)
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})

        if "remember" in user_text.lower():
            memory.remember_fact(user_text)

        if self.voice_enabled:
            speak_thread = SpeakThread(reply)
            speak_thread.error_occurred.connect(self._on_thread_error)
            self._track_thread(speak_thread)
            speak_thread.start()

        self.input_box.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_box.setFocus()


if __name__ == "__main__":
    def _log_uncaught_exception(exc_type, exc_value, exc_traceback):
        """
        Catches ANY error that would otherwise silently close the app.
        Writes full details to crash_log.txt so we can actually diagnose
        what happened, instead of the app just vanishing.
        """
        error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"[FATAL] Uncaught exception:\n{error_text}")
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- Crash ---\n{error_text}\n")

    sys.excepthook = _log_uncaught_exception

    app = QApplication(sys.argv)
    window = PyrosWindow()
    window.show()
    sys.exit(app.exec())