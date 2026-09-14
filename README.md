<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=32&duration=3000&pause=1000&color=6C63FF&center=true&vCenter=true&width=600&lines=Hi%2C+I'm+PYROS;Your+Personal+AI+Companion;Built+by+Aashish+Yadav" alt="Typing SVG" />

<br/>

<img src="https://img.shields.io/badge/Python-3.11-6C63FF?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/PyQt6-Desktop%20App-FF6B9D?style=for-the-badge&logo=qt&logoColor=white" />
<img src="https://img.shields.io/badge/Status-In%20Development-FFD166?style=for-the-badge" />
<img src="https://img.shields.io/badge/License-Personal%20Project-06D6A0?style=for-the-badge" />

<br/><br/>

**P**ersonalised **Y**ield **R**esearch **O**rchestration **S**ystem

*A personal AI assistant with memory, a voice, a 3D solar system, and a mind of her own.*

</div>

---

##  What is PYROS?

PYROS is a personal AI desktop companion — built from scratch, piece by piece — that remembers you, talks to you, keeps up with real news and weather, and lives inside her own custom window complete with a fully real, textured, rotating 3D solar system in the corner.

She's not a chatbot in a browser tab. She's a standalone Windows application with her own personality, her own memory that persists across sessions, and the beginnings of real autonomy — self-talk when you go quiet, self-awareness of her own source code, and a roadmap toward full task automation.

<div align="center">
<img src="https://user-images.githubusercontent.com/74038190/212284158-e840e285-664b-44d7-b79b-e264b5e54825.gif" width="500">
</div>

---

##  Features

###  Core Intelligence
- **Multi-provider LLM brain** — Groq, Mistral, Cerebras, OpenAI, with automatic key rotation on rate limits
- **Persistent memory** — numbered, permanent chat archive + a rolling recent-context window + long-term semantic fact storage via ChromaDB
- **Real personality** — warm, cheerful, professional, concise by design — not a chatty robot
- **Self-talk** — speaks up on her own after a few minutes of silence, instead of just waiting
- **Self-awareness** — can read her own source code and crash logs to explain what went wrong, with zero terminal needed

###  Real-World Grounding
- **Live news** — Currents API + RSS fallback, with region/country-specific filtering ("news from Japan")
- **Real weather** — live current conditions for any city via Weatherstack
- **Date, time, and location awareness** — always grounded in the actual present moment
- **Strict honesty rules** — never invents current events or facts she doesn't actually have

###  The Solar System
- Fully custom-built 3D solar system rendered with Three.js, embedded directly in her window
- **Real NASA-based textures** for Earth; real equirectangular maps for every other planet
- **Real orbital & rotation physics** — Mercury genuinely orbits fastest, Venus and Uranus rotate retrograde, exactly like real astronomy
- **288 moons** — matching the real known-moon counts of Jupiter, Saturn, Uranus, and Neptune
- Chat-controlled camera — say *"take me to Saturn"* or *"let me float free"* and watch it happen live
- Real rock-particle asteroid belt and Saturn ring, real Milky Way skybox

###  Voice
- **Speech-to-text** via OpenAI Whisper — talk to her, don't just type
- **Swappable text-to-speech engines** — edge-tts (works today, zero GPU) → Chatterbox-Turbo or VibeVoice (studio-quality, GPU required, remote-callable via Google Colab)
- Fully interruptible — a real Stop button, no more talking over herself

###  Under the Hood
- Clean, single-purpose files — `brain.py`, `memory.py`, `personality.py`, `voice.py`, `news.py`, `weather.py` — each does exactly one job
- Crash-proof threading — background errors get logged and shown, never silently kill the app
- Secure by design — `.env`-based secrets, never committed, authenticated remote API calls

---

##  Architecture

```mermaid
graph TD
    A[main.py<br/>GUI + Globe + News Panel] --> B[brain.py<br/>LLM Router]
    A --> C[voice.py<br/>Speech In/Out]
    A --> D[globe.html<br/>3D Solar System]
    B --> E[memory.py<br/>Persistent Memory]
    B --> F[personality.py<br/>Behavior Rules]
    B --> G[identity.py<br/>Creator + Self Facts]
    B --> H[news.py<br/>Live News]
    B --> I[weather.py<br/>Live Weather]
    B --> J[awareness.py<br/>Date/Time/Location]
    B --> K[self_awareness.py<br/>Own Code + Crash Logs]
    C --> L[Whisper<br/>Speech-to-Text]
    C --> M[edge-tts / Chatterbox / VibeVoice<br/>Text-to-Speech]
    E --> N[(ChromaDB<br/>Long-term Facts)]
    E --> O[(full_log.txt<br/>Permanent Archive)]
```

---

##  Getting Started

```bash
git clone https://github.com/Aashish-Yadav7/PYROS.git
cd PYROS
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your own API keys:

```dotenv
GROQ_API_KEY_1=your_key_here
GROQ_API_KEY_2=your_backup_key_here
CURRENTS_API_KEY=your_key_here
WEATHERSTACK_API_KEY=your_key_here
TTS_ENGINE=edge_tts
CREATOR_NAME=Your Name
```

Then launch her:

```bash
python main.py
```

First run will ask your name and what you'd like to be called — after that, she remembers.

---

##  Screenshots

<div align="center">
<i>Add your own screenshots here — the chat window, the solar system in action, a voice conversation mid-flow.</i>

<br/><br/>

<img src="https://via.placeholder.com/800x450/05060a/6C63FF?text=Add+a+screenshot+of+PYROS+here" width="800">
</div>

---

##  Roadmap

- [x] Core brain with multi-provider fallback
- [x] Persistent memory (archive + semantic recall)
- [x] Personality + identity system
- [x] Real-time news, weather, date/time/location
- [x] 3D solar system with real physics and textures
- [x] Voice input (Whisper) and output (edge-tts / Chatterbox / VibeVoice)
- [x] Self-awareness (reads own code + crash logs)
- [ ] Background research agent
- [ ] Full task automation (email, WhatsApp, Notepad, and beyond)
- [ ] Face recognition
- [ ] PDF reading and summarization
- [ ] Text-to-image and text-to-video generation

---

<div align="center">

### Built with persistence, a lot of debugging, and zero shortcuts.

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=18&duration=2500&pause=800&color=FF6B9D&center=true&vCenter=true&width=500&lines=Made+by+Aashish+Yadav;Creator+of+PYROS" alt="Footer Typing SVG" />

</div>
