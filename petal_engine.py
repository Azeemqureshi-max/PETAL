import os
import sys
import re

# --------------------------------------------------
# PETAL ENGINE SETUP
# --------------------------------------------------

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ENGINE_DIR)
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")

for folder in [PROJECT_ROOT, ENGINE_DIR, TOOLS_DIR]:
    if folder not in sys.path:
        sys.path.insert(0, folder)

from petal_router import classify


# --------------------------------------------------
# WINDOWS FOLDER HANDLER
# --------------------------------------------------

def handle_folder(text):
    from windows_tool import open_folder

    text = text.strip()

    text = re.sub(
        r"^(please\s+)?(open|launch|show|go to|navigate to)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+folder$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^(the|my)\s+", "", text, flags=re.IGNORECASE).strip()

    normalized = text.lower()

    folder_aliases = {
        "desktop": "desktop",
        "documents": "documents",
        "document": "documents",
        "downloads": "downloads",
        "download": "downloads",
        "pictures": "pictures",
        "picture": "pictures",
        "photos": "pictures",
        "photo": "pictures",
        "music": "music",
        "videos": "videos",
        "video": "videos",
        "this pc": "this pc",
        "computer": "this pc",
    }

    if normalized in folder_aliases:
        return open_folder(folder_aliases[normalized])

    drive_match = re.fullmatch(
        r"([a-z])\s*(?::\\?|drive)",
        normalized,
    )

    if drive_match:
        return open_folder(drive_match.group(1).upper() + ":\\")

    if re.match(r"^[a-zA-Z]:\\", text) or text.startswith("\\\\"):
        return open_folder(text)

    return None


# --------------------------------------------------
# WINDOWS APP AND WINDOW HANDLER
# --------------------------------------------------

def handle_windows(text):
    from windows_tool import (
        open_application,
        close_application,
        control_window,
    )

    text = text.strip()

    # MINIMIZE, MAXIMIZE, RESTORE, AND FOCUS
    control_match = re.match(
        r"^(?:please\s+)?"
        r"(minimize|maximize|restore|focus|activate|switch to)"
        r"\s+(.+?)\s*[.!]?$",
        text,
        flags=re.IGNORECASE,
    )

    if control_match:
        action = control_match.group(1).lower().strip()
        app_name = control_match.group(2).strip().strip("\"'")

        if action == "switch to":
            action = "focus"

        if not app_name:
            return "Which application should I control?"

        return control_window(app_name, action)

    # CLOSE AN APPLICATION
    close_match = re.match(
        r"^(?:please\s+)?(?:close|quit|exit|stop)"
        r"\s+(.+?)\s*[.!]?$",
        text,
        flags=re.IGNORECASE,
    )

    if close_match:
        app_name = close_match.group(1).strip().strip("\"'")

        if not app_name:
            return "Which application should I close?"

        return control_window(app_name, "close")

    # OPEN KNOWN FOLDERS OR DRIVES
    folder_result = handle_folder(text)

    if folder_result is not None:
        return folder_result

    # OPEN AN APPLICATION
    open_match = re.match(
        r"^(?:please\s+)?"
        r"(?:open|launch|start|run|show|go to|navigate to)"
        r"\s+(.+?)\s*[.!]?$",
        text,
        flags=re.IGNORECASE,
    )

    if not open_match:
        return "[WINDOWS] Please specify an app, folder, or window-control command."

    app_name = open_match.group(1).strip().strip("\"'")

    if not app_name:
        return "What would you like me to open?"

    return open_application(app_name)


# --------------------------------------------------
# MATH EXPRESSION HANDLER
# --------------------------------------------------

def extract_math_expression(text):
    expression = text.lower().strip()

    prefixes = [
        "what is",
        "calculate",
        "solve",
        "compute",
        "evaluate",
    ]

    for prefix in prefixes:
        if expression.startswith(prefix):
            expression = expression[len(prefix):].strip()
            break

    return expression.replace("?", "").strip()


# --------------------------------------------------
# FILE HANDLER
# --------------------------------------------------

def handle_file(text):
    try:
        from file_tool import handle_file as file_handler
        return file_handler(text)
    except ImportError:
        pass

    try:
        from file_tool import process_file
        return process_file(text)
    except ImportError:
        pass

    return "[FILE] File handling is not configured yet."


# --------------------------------------------------
# MAIN PETAL FUNCTION
# --------------------------------------------------

def petal(text):
    if not isinstance(text, str) or not text.strip():
        return "Please enter a command."

    text = text.strip()

    # CREATOR IDENTITY
    creator_patterns = [
        r"\bwho (?:built|build|created|create|made|makes|developed|develops|programmed|coded) you\b",
        r"\bwho is your (?:creator|developer|builder|programmer|owner|father|dad)\b",
        r"\bwho (?:built|created|made|developed|programmed|coded) petal\b",
        r"\bwho is petal'?s? (?:creator|developer|builder|programmer)\b",
        r"\bwho owns you\b",
        r"\bwho is behind petal\b",
        r"\btell me about your (?:creator|developer|builder|programmer)\b",
        r"\btell me who (?:created|built|made|developed) you\b",
        r"\bwho is the person who (?:created|built|made|developed) you\b",
    ]

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in creator_patterns
    ):
        return "I was created by Qureshi Mohammed Azeem."

    # DIRECT WINDOWS ROUTING
    # Run explicit commands before intent classification.
    # This prevents Qwen from explaining a command instead of executing it.

    if re.match(
        r"^(please\s+)?"
        r"(minimize|maximize|restore|focus|activate|switch to)\s+.+",
        text,
        flags=re.IGNORECASE,
    ):
        try:
            return handle_windows(text)
        except Exception as error:
            return f"[WINDOWS] Window-control failed: {error}"

    if re.match(
        r"^(please\s+)?(close|quit|exit|stop)\s+.+",
        text,
        flags=re.IGNORECASE,
    ):
        try:
            return handle_windows(text)
        except Exception as error:
            return f"[WINDOWS] Close command failed: {error}"

    if re.match(
        r"^(please\s+)?"
        r"(open|launch|start|run|show|go to|navigate to)\s+.+",
        text,
        flags=re.IGNORECASE,
    ):
        try:
            result = handle_windows(text)

            if not (
                isinstance(result, str)
                and result.startswith("[WINDOWS] Please specify")
            ):
                return result

        except Exception as error:
            return f"[WINDOWS] Open command failed: {error}"

    # INTENT CLASSIFICATION
    try:
        intent = classify(text)
    except Exception as error:
        print("Petal routing failed:", error)
        intent = "reasoning"

    # AI CLASSIFIER FALLBACK
    if intent == "reasoning":
        try:
            from intent_classifier import classify_with_ai
            intent = classify_with_ai(text)
        except Exception as error:
            print("AI intent classification failed:", error)

    # MATH
    if intent == "math":
        try:
            from math_tool import calculate, solve_equation

            expression = extract_math_expression(text)

            if "=" in expression:
                return str(solve_equation(expression))

            return str(calculate(expression))

        except ImportError:
            try:
                from math_tool import calculate
                return str(calculate(extract_math_expression(text)))
            except Exception as error:
                return f"[MATH] Could not calculate: {error}"

        except Exception as error:
            return f"[MATH] Could not calculate: {error}"

    # PYTHON CODE GENERATION
    if intent == "python":
        try:
            from python_tool import generate_python
            return generate_python(text)
        except Exception as error:
            return f"[PYTHON] Could not generate code: {error}"

    # WINDOWS TOOLS
    if intent == "windows":
        try:
            return handle_windows(text)
        except Exception as error:
            return f"[WINDOWS] Command failed: {error}"

    # FILE OPERATIONS
    if intent == "file":
        try:
            return handle_file(text)
        except Exception as error:
            return f"[FILE] Command failed: {error}"

    # WEB RESEARCH
    if intent == "web":
        try:
            from web_pipeline import research_web
            result = research_web(text)

            if isinstance(result, dict):
                return str(result.get("answer", result))

            return str(result)

        except Exception as error:
            return f"[WEB] Research failed: {error}"

    # CONTENT WRITING
    if intent == "writing":
        try:
            from writing_tool import write_text
            return write_text(text)
        except Exception as error:
            return f"[WRITING] Could not write content: {error}"

    # GENERAL REASONING
    if intent == "reasoning":
        try:
            from reasoning_tool import reason
            return reason(text)
        except Exception as error:
            return f"[REASONING] Could not process request: {error}"

    return (
        "I'm not sure how to handle that yet. "
        "Try asking me to open an app or folder, control a window, "
        "solve a math problem, write Python code, or research a topic."
    )