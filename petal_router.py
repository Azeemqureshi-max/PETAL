
import re


def classify(text):
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)

    # 1. EXPLICIT WEB RESEARCH
    web_phrases = [
        "search the web", "search online",
        "search the internet", "search internet",
        "look up online", "find online",
        "latest news", "latest version",
        "search for", "browse the web",
        "research online", "look it up",
        "check online", "verify online",
    ]

    if any(phrase in text for phrase in web_phrases):
        return "web"

    # 2. PYTHON CODE GENERATION
    python_phrases = [
        "python code", "python program",
        "python function", "write code",
        "write a program", "create a program",
        "program to ", "write a script",
        "algorithm",
    ]

    if any(phrase in text for phrase in python_phrases):
        return "python"

    # File Explorer is a Windows application.
    if re.match(
        r"^(please\s+)?(open|launch|start|run)\s+"
        r"(file explorer|explorer|this pc|computer)\s*$",
        text,
    ):
        return "windows"

    # 3. FILE OPERATIONS
    file_phrases = [
        "read file", "read the file", "read my file",
        "open file", "open the file", "open my file",
        "write file", "write to file", "save to file",
        "save file", "create file", "create a file",
        "make a file",
    ]

    file_extension = re.search(
        r"\b[\w.-]+\.(txt|json|csv|md|py|log)\b",
        text,
    )

    if any(phrase in text for phrase in file_phrases) or file_extension:
        return "file"

    # 4. MATH AND EQUATIONS
    math_phrases = [
        "calculate", "solve", "equation",
        "square root", "percentage", "percent",
        "factorial", "what is", "how much is",
    ]

    has_math_symbol = bool(
        re.search(r"\d\s*[\+\*/\^%=]\s*\d", text)
    )
    has_subtraction = bool(re.search(r"\d\s*-\s*\d", text))
    has_equation = "=" in text and bool(re.search(r"\d|[a-z]", text))

    if (
        (
            any(phrase in text for phrase in math_phrases)
            and (
                has_math_symbol
                or has_subtraction
                or has_equation
                or any(word in text for word in [
                    "square root", "percentage", "percent", "factorial"
                ])
            )
        )
        or has_math_symbol
        or has_subtraction
    ):
        return "math"

    # 5. WRITING
    writing_phrases = [
        "write an email", "write a email",
        "write a message", "write a paragraph",
        "write a letter", "write a story",
        "write a caption", "write a speech",
        "rewrite", "rephrase",
    ]

    if any(phrase in text for phrase in writing_phrases):
        return "writing"

    # 6. WINDOWS APPS, FOLDERS, DRIVES AND PATHS
    windows_phrases = [
        "open calculator", "launch calculator",
        "open notepad", "launch notepad",
        "open paint", "launch paint",
        "open chrome", "launch chrome",
        "open google chrome", "launch google chrome",
        "open browser", "launch browser",
        "open my browser", "launch my browser",
        "open default browser",
        "open file explorer", "launch file explorer",
        "open explorer", "launch explorer",
        "open this pc", "open computer",
        "open desktop", "open documents",
        "open downloads", "open pictures",
        "open music", "open videos",
        "open task manager", "open settings",
        "open command prompt", "open powershell",
        "shutdown computer", "shut down computer",
        "restart computer", "restart my pc",
    ]

    if any(phrase in text for phrase in windows_phrases):
        return "windows"

    drive_command = re.search(
        r"\b[a-z]\s*:\s*(?:\\.*)?$|\b[a-z]\s+drive\b",
        text,
    )

    if drive_command:
        return "windows"

    path_command = re.search(r"[a-z]:\\|\\\\", text)

    if path_command and re.match(
        r"^(please\s+)?(open|launch|start|run|show|go to|navigate to)\b",
        text,
    ):
        return "windows"

    folder_verbs = r"(open|launch|show|go to|navigate to)"
    folder_names = (
        r"(desktop|documents?|downloads?|pictures?|photos?|"
        r"music|videos?|this pc|computer)"
    )

    if re.match(
        rf"^(please\s+)?{folder_verbs}\s+(the\s+|my\s+)?"
        rf"{folder_names}(\s+folder)?$",
        text,
    ):
        return "windows"

    app_command = re.match(
        r"^(please\s+)?(open|launch|start|run)\s+(.+)$",
        text,
    )

    if app_command:
        target = app_command.group(3).strip()

        if target and not target.endswith(
            (".txt", ".json", ".csv", ".md", ".py", ".log")
        ):
            return "windows"

    # 7. AUTOMATIC WEB RESEARCH FOR CURRENT OR SPECIFIC FACTS
    current_fact_phrases = [
        "today", "right now", "currently",
        "current", "latest", "recent",
        "this week", "this month", "this year",
        "as of now", "still alive", "is he alive",
        "is she alive", "is it available",
        "release date", "price today",
        "who won", "who is the ceo",
        "who is the founder",
    ]

    if any(phrase in text for phrase in current_fact_phrases):
        return "web"

    # Questions about named people, products, organisations,
    # AI models and unfamiliar terms often need verification.
    factual_question = re.match(
        r"^(who is|who was|what is|what was|"
        r"when did|when was|where is|where was|"
        r"does .+ exist|is .+ real|"
        r"tell me about)\b",
        text,
    )

    if factual_question:
        # Avoid sending common educational definitions and
        # simple conversational questions to web unnecessarily.
        known_general_topics = [
            "what is photosynthesis",
            "what is gravity",
            "what is an atom",
            "what is a variable",
            "what is a loop",
            "what is a function",
            "what is python",
            "what is html",
            "what is css",
        ]

        if not any(topic in text for topic in known_general_topics):
            return "web"

    # 8. DEFAULT: NORMAL CONVERSATION OR REASONING
    return "reasoning"


if __name__ == "__main__":
    tests = [
        "Open File Explorer",
        "Open Brave",
        "Open Pictures",
        "Open Music folder",
        "Open This PC",
        "Open D drive",
        r"Open D:\Petal",
        "Search the web for Python news",
        "What is 25 + 17?",
        "Solve 2*x + 5 = 15",
        "Calculate 144 / 12",
        "Read my notes.txt file",
        "Write an email to my teacher",
        "Write a Python program to add two numbers",
        "Is Ratan Tata alive?",
        "What is GPT-6 Astra?",
        "Who is the current CEO of Microsoft?",
        "Explain photosynthesis",
    ]

    for item in tests:
        print(f"{item} -> {classify(item)}")
