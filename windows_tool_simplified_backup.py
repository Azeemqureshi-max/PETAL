
import os
import re
import shutil
import subprocess
import ctypes
from pathlib import Path


# ==================================================
# PETAL WINDOWS TOOLS
# ==================================================

APPLICATIONS = {
    "calculator": ["calc.exe"],
    "notepad": ["notepad.exe"],
    "paint": ["mspaint.exe"],
    "file explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    "task manager": ["taskmgr.exe"],
    "command prompt": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "settings": ["explorer.exe", "ms-settings:"],
}

APP_ALIASES = {
    "google chrome": "chrome",
    "chrome browser": "chrome",
    "ms edge": "msedge",
    "microsoft edge": "msedge",
    "microsoft edge browser": "msedge",
    "file manager": "file explorer",
    "windows explorer": "file explorer",
    "browser": "browser",
    "default browser": "browser",
    "my browser": "browser",
}

FOLDER_ALIASES = {
    "desktop": "Desktop",
    "documents": "Documents",
    "document": "Documents",
    "downloads": "Downloads",
    "download": "Downloads",
    "pictures": "Pictures",
    "picture": "Pictures",
    "photos": "Pictures",
    "music": "Music",
    "videos": "Videos",
    "video": "Videos",
}


# ==================================================
# HELPERS
# ==================================================

def normalize(name):
    return re.sub(r"\s+", " ", str(name).lower()).strip()


def clean_command_name(value, verbs=()):
    value = str(value).strip().strip("\"'")
    for verb in verbs:
        value = re.sub(
            rf"^{re.escape(verb)}\s+",
            "",
            value,
            flags=re.IGNORECASE,
        )
    return value.strip().strip("\"'")


def run_hidden(command, timeout=20):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None


# ==================================================
# OPEN APPLICATIONS
# ==================================================

def open_application(application):
    name = clean_command_name(
        application,
        ("please open", "open", "launch", "start", "run"),
    )
    key = normalize(name)
    key = APP_ALIASES.get(key, key)

    if not key:
        return "Please specify an application to open."

    if key == "browser":
        try:
            os.startfile("https://www.google.com")
            return "Opened your default browser."
        except OSError as exc:
            return f"Couldn't open the browser: {exc}"

    if key in APPLICATIONS:
        command = APPLICATIONS[key]
        try:
            if len(command) == 2:
                subprocess.Popen(command)
            else:
                subprocess.Popen(command, shell=False)
            return f"Opened {name}."
        except OSError as exc:
            return f"Couldn't open {name}: {exc}"

    executable = shutil.which(name)
    if executable:
        try:
            subprocess.Popen([executable])
            return f"Opened {name}."
        except OSError as exc:
            return f"Couldn't open {name}: {exc}"

    return (
        f"I couldn't find an installed app matching '{name}'. "
        "Try its name as shown in the Windows Start menu."
    )


# ==================================================
# CLOSE APPLICATIONS SAFELY
# ==================================================

def close_application(application):
    name = clean_command_name(
        application,
        ("please close", "close", "quit", "exit", "stop"),
    )
    requested = normalize(name)

    if not requested:
        return "Please specify an application to close."

    # Ask Windows to close matching windows gracefully.
    user32 = ctypes.windll.user32
    matches = []
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)

        if requested in normalize(title.value):
            matches.append(hwnd)

        return True

    user32.EnumWindows(callback_type(callback), 0)

    if not matches:
        return f"Couldn't find an open window matching '{name}'."

    WM_CLOSE = 0x0010
    for hwnd in matches:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    return f"Asked Windows to close {name}."


# ==================================================
# WINDOW CONTROL
# ==================================================

def control_window(application, action):
    name = clean_command_name(application)
    requested = normalize(name)
    action = normalize(action)

    if not requested:
        return "Please specify an application."

    actions = {
        "minimize": 6,
        "minimise": 6,
        "maximize": 3,
        "maximise": 3,
        "restore": 9,
    }

    user32 = ctypes.windll.user32
    matches = []
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
    )

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)

        if requested in normalize(title.value):
            matches.append(hwnd)

        return True

    user32.EnumWindows(callback_type(callback), 0)

    if not matches:
        return f"Couldn't find an open window matching '{name}'."

    hwnd = matches[0]

    if action in actions:
        user32.ShowWindow(hwnd, actions[action])
        return f"Executed {action} for {name}."

    if action in ("focus", "activate", "switch to"):
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        return f"Focused {name}."

    return f"Unsupported window action: {action}"


# ==================================================
# OPEN FOLDERS AND DRIVES
# ==================================================

def get_known_folders():
    home = Path.home()
    return {
        "desktop": home / "Desktop",
        "documents": home / "Documents",
        "downloads": home / "Downloads",
        "pictures": home / "Pictures",
        "music": home / "Music",
        "videos": home / "Videos",
    }


def get_available_drives():
    import string
    drives = []
    for letter in string.ascii_uppercase:
        path = Path(f"{letter}:\\")
        if path.exists():
            drives.append(str(path))
    return drives


def list_available_drives():
    drives = get_available_drives()
    return "Available drives: " + ", ".join(drives) if drives else "No drives found."


def open_folder(folder):
    name = str(folder).strip().strip("\"'")
    key = normalize(name)

    if key in ("this pc", "computer"):
        try:
            subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            return "Opened This PC."
        except OSError as exc:
            return f"Couldn't open This PC: {exc}"

    if key.endswith(" drive"):
        key = key[:-6].strip()

    if re.fullmatch(r"[a-z]:?", key):
        path = key[0].upper() + ":\\"
    elif key in FOLDER_ALIASES:
        path = str(Path.home() / FOLDER_ALIASES[key])
    elif re.match(r"^[a-zA-Z]:\\", name) or name.startswith("\\\\"):
        path = name
    else:
        path = name

    if not os.path.exists(path):
        return f"Folder or drive not found: {path}"

    try:
        os.startfile(path)
        return f"Opened {path}."
    except OSError as exc:
        return f"Couldn't open {path}: {exc}"
