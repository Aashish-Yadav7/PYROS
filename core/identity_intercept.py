"""
core/identity_intercept.py

Guarantees correct, varied answers to identity questions WITHOUT relying
on the LLM — testing showed even the strongest provider (Groq) still
said "Meta" sometimes. This isn't a provider reliability issue — Llama
models have a very strongly trained instinct to attribute themselves to
Meta, which system prompts can't reliably override 100% of the time.
So for this one category of question, we build the answer ourselves
from mix-and-match natural language pieces — real sentence-level
variety, zero risk of the wrong fact.
"""
import re
import random

NAME_PATTERNS = [r"\bwhat('?s| is) your name\b", r"\bwho are you\b"]
CREATOR_PATTERNS = [
    r"\bwho (made|created|built|developed) you\b",
    r"\bwho('?s| is) your creator\b",
    r"\byour (creator|developer|maker)\b",
    r"\bwhich company (made|created|built) you\b",
]
ABOUT_CREATOR_PATTERNS = [
    r"\btell me (more )?about (him|aashish|your creator)\b",
    r"\bwho is aashish\b",
]

OPENERS = ["", "So, ", "Honestly, ", "Well, ", "Good question — "]

# Full, grammatically complete sentence pairs (core + detail), so mixing
# never produces a broken sentence like "My creator is X a solo project".
CREATOR_PAIRS = [
    ("I was built by Aashish Yadav", "working entirely solo during his first year of BCA."),
    ("Aashish Yadav is the one who made me", "as a personal project in his first year studying BCA."),
    ("My creator is Aashish Yadav", "who built me as a solo project in his first year of BCA."),
    ("I come from Aashish Yadav's own hands", "no team, no company — just him, in his first year of BCA."),
]

NAME_PAIRS = [
    ("I'm PYROS", "your personal AI assistant."),
    ("My name's PYROS", "a personal AI assistant built just for you."),
    ("You can call me PYROS", "that's my name."),
    ("I go by PYROS", "built as a personal AI project."),
]

ABOUT_CREATOR_CORE = [
    "Aashish is into building things from scratch — coding, systems, AI projects, that kind of stuff.",
    "He'd rather build something new than just settle for what already exists.",
    "He's someone who values focus and persistence over noise and giving up.",
    "He enjoys creating his own tools and AI rather than relying on off-the-shelf solutions.",
]


def _mix_pair(pairs: list) -> str:
    opener = random.choice(OPENERS)
    core, detail = random.choice(pairs)
    return f"{opener}{core}, {detail}".strip()


def check_identity_intercept(user_text: str) -> str | None:
    text = user_text.lower().strip()

    for pattern in CREATOR_PATTERNS:
        if re.search(pattern, text):
            return _mix_pair(CREATOR_PAIRS)

    for pattern in ABOUT_CREATOR_PATTERNS:
        if re.search(pattern, text):
            return " ".join(random.sample(ABOUT_CREATOR_CORE, k=2))

    for pattern in NAME_PATTERNS:
        if re.search(pattern, text):
            return _mix_pair(NAME_PAIRS)

    return None