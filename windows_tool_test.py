from pathlib import Path
code = r'''"""
Petal Windows Tools — safe, discovery-based implementation.

Required by petal_engine.py:
    open_application(application)
    close_application(application)
    open_folder(folder)

Additional helpers:
    list_installed_apps()
    list_windows()
    control_window(name, action)
    minimize_window(name), maximize_window(name), restore_window(name), focus_window(name)
    get_known_folders(), get_available_drives(), list_available_drives(), get_system_info()
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

IS_WINDOWS = os.name == "nt"
WM_CLOSE = 0x0010
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9


def normalize(value: str) -> str:
    """Normalize names for tolerant matching."""
    value = str(value or "").strip().lower()
    value = re.sub(r"\.(exe|lnk|url|appref-ms)$", "", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def _require_windows() -> None:
    if not IS_WINDOWS:
        raise OSError("Petal Windows tools can only run on Windows.")


def run_hidden(command: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    """Run a subprocess without displaying a console window."""
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "check": False,
    }
    if IS_WINDOWS:
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(command, **kwargs)


def _clean_name(value: str, verbs: tuple[str, ...] = ()) -> str:
    name = str(value or "").strip().strip("\"'")
    for verb in sorted(verbs, key=len, reverse=True):
        name = re.sub(
            rf"^\s*(?:please\s+)?{re.escape(verb)}\s+",
            "", name, flags=re.IGNORECASE
        )
    return re.sub(r"[.!?]+$", "", name).strip().strip("\"'")


def start_menu_directories() -> list[Path]:
    roots = []
    for variable in ("APPDATA", "PROGRAMDATA"):
        base = os.environ.get(variable)
        if base:
            root = Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            if root.is_dir():
                roots.append(root)
    return roots


def find_start_menu_shortcuts(app_name: str) -> list[Path]:
    """Find shortcuts by exact or partial display name."""
    wanted = normalize(app_name)
    if not wanted:
        return []
    matches: list[tuple[int, Path]] = []
    try:
        for root in start_menu_directories():
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in {".lnk", ".url", ".appref-ms"}:
                    continue
                candidate = normalize(path.stem)
                if candidate == wanted:
                    matches.append((0, path))
                elif len(wanted) >= 3 and (wanted in candidate or candidate in wanted):
                    matches.append((1, path))
    except (OSError, PermissionError):
        pass
    matches.sort(key=lambda item: (item[0], len(item[1].stem), str(item[1]).lower()))
    return [path for _, path in matches]


def _registered_app_paths() -> dict[str, str]:
    """Discover applications registered under Windows App Paths."""
    _require_windows()
    result: dict[str, str] = {}
    try:
        import winreg
        locations = (
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths"),
        )
        for hive, key_path in locations:
            try:
                with winreg.OpenKey(hive, key_path) as root:
                    count = winreg.QueryInfoKey(root)[0]
                    for i in range(count):
                        try:
                            sub_name = winreg.EnumKey(root, i)
                            with winreg.OpenKey(root, sub_name) as subkey:
                                exe, _ = winreg.QueryValueEx(subkey, None)
                            exe = os.path.expandvars(str(exe)).strip().strip('"')
                            if exe:
                                result[normalize(Path(sub_name).stem)] = exe
                        except (OSError, ValueError):
                            continue
            except OSError:
                continue
    except (ImportError, OSError):
        pass
    return result


def list_installed_apps() -> list[str]:
    """List app names discovered from Start Menu shortcuts and App Paths."""
    names: set[str] = set()
    try:
        for root in start_menu_directories():
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".lnk", ".url", ".appref-ms"}:
                    names.add(path.stem)
    except (OSError, PermissionError):
        pass
    names.update(name for name in _registered_app_paths() if name)
    return sorted(names, key=str.casefold)


def find_start_app_id(app_name: str) -> tuple[str, str] | None:
    """Find a packaged Windows app by its Start Menu name."""
    _require_windows()
    wanted = normalize(app_name)
    if not wanted:
        return None
    try:
        result = run_hidden([
            "powershell.exe", "-NoProfile", "-Command",
            "Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress"
        ])
        if result.returncode != 0 or not result.stdout.strip():
            return None
        import json
        entries = json.loads(result.stdout)
        if isinstance(entries, dict):
            entries = [entries]
        candidates = []
        for item in entries:
            title = str(item.get("Name", ""))
            app_id = str(item.get("AppID", ""))
            key = normalize(title)
            if not key or not app_id:
                continue
            if key == wanted:
                return title, app_id
            if len(wanted) >= 3 and (key.startswith(wanted) or wanted in key):
                candidates.append((abs(len(key) - len(wanted)), title, app_id))
        if candidates:
            candidates.sort()
            _, title, app_id = candidates[0]
            return title, app_id
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        pass
    return None


def open_application(application: str) -> str:
    """Open a URL, executable, discovered shortcut, or packaged Windows app."""
    _require_windows()
    name = _clean_name(application, ("open", "launch", "start", "run"))
    if not name:
        return "Please specify an application to open."

    if re.match(r"^(https?://|www\.)", name, re.IGNORECASE):
        url = name if name.lower().startswith(("http://", "https://")) else "https://" + name
        try:
            webbrowser.open(url)
            return f"Opened {url}."
        except OSError as exc:
            return f"Could not open the web address: {exc}"

    expanded = os.path.expandvars(os.path.expanduser(name))
    path = Path(expanded)
    if path.exists():
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
            return f"Opened {path}."
        except OSError as exc:
            return f"Could not open '{name}': {exc}"

    executable = shutil.which(name)
    if executable:
        try:
            subprocess.Popen([executable], close_fds=True)
            return f"Opened {name}."
        except OSError as exc:
            return f"Could not launch '{name}': {exc}"

    registered = _registered_app_paths()
    wanted = normalize(name)
    app_path = registered.get(wanted)
    if not app_path:
        near = [path for key, path in registered.items()
                if wanted and len(wanted) >= 3 and (wanted in key or key in wanted)]
        if near:
            app_path = near[0]
    if app_path and Path(app_path).exists():
        try:
            os.startfile(app_path)  # type: ignore[attr-defined]
            return f"Opened {name}."
        except OSError:
            pass

    shortcuts = find_start_menu_shortcuts(name)
    if shortcuts:
        try:
            os.startfile(str(shortcuts[0]))  # type: ignore[attr-defined]
            return f"Opened {shortcuts[0].stem}."
        except OSError:
            pass

    app_entry = find_start_app_id(name)
    if app_entry:
        title, app_id = app_entry
        try:
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"], close_fds=True)
            return f"Opened {title}."
        except OSError:
            pass

    return (
        f"I couldn't find an application matching '{name}'. "
        "Try its full Start Menu name or the full path to its executable."
    )


def _window_api() -> dict[str, Any]:
    """Load the Win32 APIs used for window enumeration and control."""
    _require_windows()
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return {"ctypes": ctypes, "wintypes": wintypes, "user32": user32,
            "kernel32": kernel32, "callback_type": callback_type}


def _process_executable(pid: int, api: dict[str, Any]) -> str:
    from ctypes import wintypes
    kernel32 = api["kernel32"]
    handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not handle:
        return ""
    try:
        buffer = api["ctypes"].create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, api["ctypes"].byref(size)):
            return buffer.value
    except OSError:
        pass
    finally:
        kernel32.CloseHandle(handle)
    return ""


def _enumerate_windows() -> list[dict[str, Any]]:
    """Return visible, titled windows and process metadata."""
    api = _window_api()
    ctypes = api["ctypes"]
    wintypes = api["wintypes"]
    user32 = api["user32"]
    found: list[dict[str, Any]] = []

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = _process_executable(pid.value, api)
        found.append({
            "hwnd": int(hwnd), "title": title, "pid": int(pid.value),
            "exe": exe, "process": Path(exe).stem if exe else ""
        })
        return True

    callback_ref = api["callback_type"](callback)
    user32.EnumWindows(callback_ref, 0)
    return found


def list_windows() -> list[dict[str, Any]]:
    """Return visible windows; an error is represented as a result item."""
    try:
        return _enumerate_windows()
    except (OSError, AttributeError) as exc:
        return [{"error": str(exc)}]


def _matching_windows(name: str) -> list[dict[str, Any]]:
    wanted = normalize(_clean_name(
        name, ("close", "quit", "exit", "minimize", "maximize", "restore", "focus", "switch to")
    ))
    if not wanted:
        return []
    matches = []
    for window in _enumerate_windows():
        title = normalize(window["title"])
        process = normalize(window["process"])
        exe = normalize(Path(window["exe"]).name if window["exe"] else "")
        if any(key and (key == wanted or (len(wanted) >= 3 and wanted in key) or
                        (len(key) >= 3 and key in wanted))
               for key in (title, process, exe)):
            matches.append(window)
    return matches


def close_application(application: str) -> str:
    """Request a normal close by posting WM_CLOSE; never force-kill a process."""
    _require_windows()
    name = _clean_name(application, ("close", "quit", "exit", "stop"))
    if not name:
        return "Please specify an application to close."
    try:
        matches = _matching_windows(name)
        if not matches:
            return f"I couldn't find a visible window matching '{name}'."
        api = _window_api()
        closed = 0
        seen = set()
        for item in matches:
            hwnd = item["hwnd"]
            if hwnd in seen:
                continue
            seen.add(hwnd)
            if api["user32"].PostMessageW(hwnd, WM_CLOSE, 0, 0):
                closed += 1
        if closed:
            return f"Sent a normal close request to {closed} window(s) matching '{name}'."
        return f"Windows did not accept the close request for '{name}'."
    except (OSError, AttributeError) as exc:
        return f"Could not close '{name}': {exc}"


def control_window(application: str, action: str) -> str:
    """Minimize, maximize, restore, or focus a matching window."""
    _require_windows()
    action_key = normalize(action)
    actions = {
        "minimize": SW_MINIMIZE, "minimized": SW_MINIMIZE,
        "maximize": SW_MAXIMIZE, "maximized": SW_MAXIMIZE,
        "restore": SW_RESTORE, "normal": SW_RESTORE,
    }
    try:
        matches = _matching_windows(application)
        if not matches:
            return f"I couldn't find a visible window matching '{application}'."
        api = _window_api()
        user32 = api["user32"]
        item = matches[0]
        if action_key in actions:
            user32.ShowWindow(item["hwnd"], actions[action_key])
            return f"{action_key.title()} requested for '{item['title']}'."
        if action_key in {"focus", "activate", "switch"}:
            user32.ShowWindow(item["hwnd"], SW_RESTORE)
            user32.SetForegroundWindow(item["hwnd"])
            return f"Focus requested for '{item['title']}'."
        return "Unknown action. Use minimize, maximize, restore, or focus."
    except (OSError, AttributeError) as exc:
        return f"Could not control that window: {exc}"


def minimize_window(application: str) -> str:
    return control_window(application, "minimize")


def maximize_window(application: str) -> str:
    return control_window(application, "maximize")


def restore_window(application: str) -> str:
    return control_window(application, "restore")


def focus_window(application: str) -> str:
    return control_window(application, "focus")


def get_known_folders() -> dict[str, Path]:
    """Discover common user folders, respecting Windows redirected locations."""
    home = Path.home()
    folders: dict[str, Path] = {
        "home": home, "user": home,
        "desktop": home / "Desktop",
        "documents": home / "Documents", "document": home / "Documents",
        "downloads": home / "Downloads", "download": home / "Downloads",
        "pictures": home / "Pictures", "picture": home / "Pictures",
        "photos": home / "Pictures", "music": home / "Music",
        "videos": home / "Videos", "video": home / "Videos",
    }
    if IS_WINDOWS:
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            aliases = {
                "Desktop": ("desktop",),
                "Personal": ("documents", "document"),
                "{374DE290-123F-4565-9164-39C4925E467B}": ("downloads", "download"),
                "My Pictures": ("pictures", "picture", "photos"),
                "My Music": ("music",),
                "My Video": ("videos", "video"),
            }
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                for index in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        value_name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        continue
                    for alias in aliases.get(value_name, ()):
                        folders[alias] = Path(os.path.expandvars(value)).expanduser()
        except (ImportError, OSError):
            pass
    return folders


def get_available_drives() -> list[Path]:
    """Return accessible Windows drive roots."""
    if not IS_WINDOWS:
        return [Path("/")]
    return [Path(f"{letter}:\\") for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            if Path(f"{letter}:\\").exists()]


def list_available_drives() -> str:
    drives = get_available_drives()
    if not drives:
        return "No accessible drives were found."
    details = []
    for drive in drives:
        try:
            usage = shutil.disk_usage(drive)
            details.append(f"{drive} ({usage.free / 1024**3:.1f} GB free)")
        except OSError:
            details.append(str(drive))
    return "Available drives: " + ", ".join(details)


def open_folder(folder: str) -> str:
    """Open a known user folder, absolute path, drive, or This PC."""
    _require_windows()
    raw = _clean_name(folder, ("open folder", "open", "show", "browse", "go to", "navigate to"))
    if not raw:
        return "Please specify a folder or drive."
    raw = os.path.expandvars(os.path.expanduser(raw.strip('"')))
    key = raw.lower().strip()
    if key in {"this pc", "my computer", "computer", "file explorer", "explorer", "file manager"}:
        try:
            subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            return "Opened This PC in File Explorer."
        except OSError as exc:
            return f"Could not open File Explorer: {exc}"

    folders = get_known_folders()
    folder_lookup = {normalize(alias): path for alias, path in folders.items()}
    target: Path | str
    if normalize(key) in folder_lookup:
        target = folder_lookup[normalize(key)]
    elif re.fullmatch(r"[a-zA-Z]\s*(?:drive|disk)", key):
        drive_letter = key[0].upper()
        target = Path(f"{drive_letter}:\\")
    elif re.fullmatch(r"[a-zA-Z]:?", raw):
        target = Path(raw[0].upper() + ":\\")
    else:
        target = Path(raw)

    try:
        path = Path(target)
        if not path.exists():
            return f"I couldn't find that folder or drive: {path}"
        if not path.is_dir():
            return f"That path is a file, not a folder: {path}"
        os.startfile(str(path))  # type: ignore[attr-defined]
        return f"Opened folder: {path}"
    except (OSError, ValueError) as exc:
        return f"Could not open that folder: {exc}"


def get_system_info() -> dict[str, str]:
    """Return basic system details."""
    return {
        "operating_system": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "computer_name": platform.node(),
        "architecture": platform.machine(),
        "python_version": sys.version.split()[0],
        "home_directory": str(Path.home()),
    }


if __name__ == "__main__":
    print("Petal Windows Tools test")
    print("=" * 28)
    print("Drives:", list_available_drives())
    print("Visible windows:")
    for window in list_windows():
        if "error" in window:
            print("  Error:", window["error"])
        else:
            print(f"  {window['title']} — {window['process'] or 'unknown process'}")
'''
path = Path("/mnt/data/windows_tool_test.py")
path.write_text(code, encoding="utf-8")
compile(code, str(path), "exec")
print("Created and Python syntax-check passed:", path, "lines:", len(code.splitlines()))
