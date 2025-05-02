import re
from telegram import Message

# Define your homework-related keywords
HOMEWORK_KEYWORDS = [
    "homework", "submit", "worksheet", "activity", "assignment",
    "task", "question", "due", "work", "exercise", "date line", "deadline"
]

def is_homework(message: Message) -> bool:
    """
    AI-style smart filter: checks if the message text or caption looks like homework.
    """
    content = message.text or message.caption
    if not content:
        return False

    # Normalize and lowercase
    content = content.lower()

    # Keyword match
    for keyword in HOMEWORK_KEYWORDS:
        if keyword in content:
            return True

    # Regex fallback: e.g., date line patterns like "submit by 3rd May"
    date_line_pattern = r"(submit(ed)?|due)\s+(on\s+)?\d{1,2}(st|nd|rd|th)?\s+\w+"
    if re.search(date_line_pattern, content):
        return True

    return False
