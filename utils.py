import re

def is_homework(message):
    """
    Heuristic-style AI filtering to guess if a message contains homework.
    """
    if not message or not message.text:
        return True  # Allow media by default

    text = message.text.lower()

    # Smart pattern matches
    keywords = [
        "homework", "hw", "h/w", "assignment", "workbook", "worksheet",
        "page", "pg", "exercise", "question", "read", "write", "solve",
        "submit", "due", "activity", "revision", "class work", "classwork"
    ]

    match_count = sum(1 for word in keywords if word in text)

    # Decision rule
    if match_count >= 2:
        return True
    if re.search(r"(pg|page)\s?\d+", text):
        return True
    if "home work" in text or "h.w" in text:
        return True

    return False  # Likely not homework
