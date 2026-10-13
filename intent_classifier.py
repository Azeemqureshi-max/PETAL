
import re
from shared_llm import generate


VALID_INTENTS = {
    "reasoning", "web", "python", "writing",
    "math", "windows", "file",
}


def classify_with_ai(request):
    text = request.strip().lower()

    # Obvious coding requests
    if re.search(
        r"\b(write|create|make|generate)\b.*\b"
        r"(python|program|script|function|code|algorithm)\b",
        text,
    ):
        return "python"

    # Obvious writing requests
    if re.search(
        r"\b(write|draft|compose|rewrite|rephrase)\b.*\b"
        r"(email|e-mail|message|paragraph|letter|story|"
        r"caption|speech|essay|poem|post)\b",
        text,
    ):
        return "writing"

    # Obvious Windows application commands
    if re.match(
        r"^(please\s+)?(open|launch|start|run)\s+"
        r"(calculator|notepad|paint|chrome|google chrome|"
        r"browser|file explorer|explorer|this pc|"
        r"computer|task manager|settings)\s*$",
        text,
    ):
        return "windows"

        # Explicit web requests and current facts
    if any(phrase in text for phrase in [
        "search the web", "search online", "look up online",
        "latest news", "latest version", "currently",
        "right now", "today", "this week", "this month",
        "this year", "as of now", "current price",
        "still alive", "is he alive", "is she alive",
        "who won", "who is the ceo", "who is the president",
    ]):
        return "web"

        # Broad factual questions about specific entities.
    # Arithmetic and explicit educational explanations should
    # be handled before this rule.
    if re.search(r"\d\s*[\+\*/\^%=]\s*\d", text) or re.search(
        r"\d\s*-\s*\d", text
    ):
        return "math"

    if text.startswith(("explain ", "teach me ", "help me understand ")):
        return "reasoning"

    factual_starts = (
        "who is ", "who was ", "what is ", "what was ",
        "when did ", "when was ", "where is ", "where was ",
        "does ", "is ", "are ", "tell me about ",
    )

    general_topics = (
        "what is photosynthesis",
        "what is gravity",
        "what is an atom",
        "what is a variable",
        "what is a loop",
        "what is a function",
        "what is python",
        "what is html",
        "what is css",
    )

    if text.startswith(factual_starts):
        if not any(topic in text for topic in general_topics):
            return "web"
    messages = [
        {
            "role": "system",
            "content": (
                "Classify the user's request into exactly one category.\n"
                "python = create or modify Python code\n"
                "writing = compose or rewrite text\n"
                "math = solve a calculation or equation\n"
                "windows = operate a Windows app or folder\n"
                "file = read, write, or manage a file\n"
                "web = verify current facts or unfamiliar specific entities\n"
                "reasoning = conversation, explanations, learning, or ideas\n"
                "Return only one category name."
            ),
        },
        {"role": "user", "content": request},
    ]

    try:
        result = generate(
            messages,
            max_new_tokens=12,
            temperature=0.1,
        ).strip().lower()

        match = re.search(
            r"\b(reasoning|web|python|writing|math|windows|file)\b",
            result,
        )

        if match and match.group(1) in VALID_INTENTS:
            return match.group(1)

    except Exception as error:
        print("AI intent classification failed:", error)

    return "reasoning"
