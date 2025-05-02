import os
import re
from dotenv import load_dotenv

def load_env():
    """Load environment variables from .env file."""
    load_dotenv()

def is_homework(message) -> bool:
    """Heuristically determine if a message is likely a homework task."""
    if not message.text:
        return True  # allow media like photos, videos, PDFs, etc.

    text = message.text.lower()

    # ⛔️ Spammy link/URL check
    if re.search(r"(https?://|www\.)", text):
        return False

    # ✅ Keywords that usually indicate homework or academic tasks
    keywords = [
        "homework", "classwork", "assignment", "exercise", "chapter", "worksheet",
        "question", "write", "draw", "solve", "submit", "deadline", "pages",
        "read", "math", "science", "english", "dzongkha", "project", "notes", "copy",
        "home task", "task", "topic", "prepare", "revise", "answer"
    ]

    # ✅ Look for at least one keyword
    return any(word in text for word in keywords)
