
import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


# ==================================================
# PETAL PORTABLE WINDOWS TOOLS
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
    "ms edge": "edge",
    "microsoft edge browser": "edge",
    "file manager": "file explorer",
    "windows explorer": "file explorer",
    "default browser": "browser",
    "my browser": "browser",
}

# Alternative names used by Windows processes and app metadata.
CLOSE_ALIASES = {
    "ms word": "word",
    "microsoft word": "word",
    "winword": "word",
    "microsoft paint": "paint",
    "mspaint": "paint",
    "google chrome": "chrome",
    "chrome browser": "chrome",
    "microsoft edge": "edge",
    "ms edge": "edge",
    "brave browser": "brave",
    "bluestacks app player": "bluestacks",
    "bluestacks x": "bluestacks",
    "blue stacks": "bluestacks",
    "file manager": "file explorer",
    "windows explorer": "file explorer",
    "cmd": "command prompt",
    "command line": "command prompt",
}

CLOSE_PROCESS_HINTS = {
    "word": ["winword", "microsoftword"],
    "paint": ["mspaint", "microsoftpaint"],
    "chrome": ["chrome", "googlechrome"],
    "edge": ["msedge", "microsoftedge"],
    "brave": ["brave", "bravebrowser"],
    "bluestacks": [
        "bluestacks", "bluestacksappplayer", "hdplayer",
        "hdagent", "bstk", "bluestacksx",
    ],
    "file explorer": ["explorer", "fileexplorer"],
    "task manager": ["taskmgr", "taskmanager"],
    "command prompt": ["cmd", "windowsterminal"],
    "powershell": ["powershell", "pwsh"],
    "notepad": ["notepad"],
    "calculator": ["calculator", "calc"],
}


# ==================================================
# GENERAL HELPERS
# ==================================================

def normalize(name):
    return re.sub(r"[^a-z0-9]+", "", str(name).lower())


def run_hidden(command, timeout=20):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )


def clean_command_name(value, verbs):
    name = str(value).strip().strip('"').strip("'")
    pattern = "|".join(re.escape(verb) for verb in verbs)
    name = re.sub(
        rf"^(please\s+)?(?:{pattern})\s+",
        "",
        name,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[.!?]+$", "", name).strip()


# ==================================================
# WINDOWS USER FOLDERS AND DRIVES
# ==================================================

def get_known_folders():
    home = Path.home()

    folders = {
        "home": home,
        "user": home,
        "desktop": home / "Desktop",
        "documents": home / "Documents",
        "document": home / "Documents",
        "downloads": home / "Downloads",
        "download": home / "Downloads",
        "pictures": home / "Pictures",
        "picture": home / "Pictures",
        "photos": home / "Pictures",
        "music": home / "Music",
        "videos": home / "Videos",
        "video": home / "Videos",
    }

    try:
        import winreg

        key_path = (
            r"Software\Microsoft\Windows\CurrentVersion"
            r"\Explorer\User Shell Folders"
        )

        aliases = {
            "Desktop": ["desktop"],
            "Personal": ["documents", "document"],
            "{374DE290-123F-4565-9164-39C4925E467B}": [
                "downloads", "download"
            ],
            "My Pictures": ["pictures", "picture", "photos"],
            "My Music": ["music"],
            "My Video": ["videos", "video"],
        }

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            for index in range(winreg.QueryInfoKey(key)[1]):
                try:
                    value_name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    continue

                for alias in aliases.get(value_name, []):
                    folders[alias] = Path(
                        os.path.expandvars(value)
                    ).expanduser()

    except (ImportError, OSError):
        pass

    return folders


def get_available_drives():
    return [
        Path(f"{letter}:\\")
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if Path(f"{letter}:\\").exists()
    ]


def list_available_drives():
    drives = get_available_drives()
    if not drives:
        return "No accessible drives were found."
    return "Available drives: " + ", ".join(map(str, drives))


# ==================================================
# START MENU APP DISCOVERY
# ==================================================

def start_menu_directories():
    locations = []

    for variable in ("APPDATA", "PROGRAMDATA"):
        base = os.environ.get(variable)
        if base:
            locations.append(
                Path(base) / "Microsoft/Windows/Start Menu/Programs"
            )

    return [path for path in locations if path.is_dir()]


def find_start_menu_shortcuts(app_name):
    wanted = normalize(app_name)
    if not wanted:
        return []

    matches = []

    for root in start_menu_directories():
        try:
            for path in root.rglob("*.lnk"):
                candidate = normalize(path.stem)

                if candidate == wanted:
                    return [path]

                if candidate and len(wanted) >= 3 and wanted in candidate:
                    matches.append(path)

        except OSError:
            continue

    matches = list(dict.fromkeys(matches))
    matches.sort(
        key=lambda path: (
            len(normalize(path.stem)) != len(wanted),
            len(path.stem),
            str(path).lower(),
        )
    )
    return matches


def find_start_app_id(app_name):
    try:
        result = run_hidden([
            "powershell.exe",
            "-NoProfile",
            "-Command",
            (
                "Get-StartApps | Select-Object Name,AppID | "
                "ConvertTo-Json -Compress"
            ),
        ])

        if result.returncode != 0 or not result.stdout.strip():
            return None

        entries = json.loads(result.stdout)
        if isinstance(entries, dict):
            entries = [entries]

        wanted = normalize(app_name)
        matches = []

        for entry in entries:
            title = entry.get("Name", "")
            app_id = entry.get("AppID", "")
            candidate = normalize(title)

            if not candidate or not app_id:
                continue
            if candidate == wanted:
                return title, app_id
            if candidate.startswith(wanted):
                matches.append((title, app_id, 0))
            elif len(wanted) >= 3 and wanted in candidate:
                matches.append((title, app_id, 1))

        if matches:
            matches.sort(
                key=lambda item: (
                    item[2],
                    abs(len(normalize(item[0])) - len(wanted)),
                    len(item[0]),
                )
            )
            return matches[0][0], matches[0][1]

    except (
        OSError, subprocess.SubprocessError, ValueError, TypeError
    ):
        pass

    return None


# ==================================================
# APPLICATION LAUNCHING
# ==================================================

def open_application(application):
    name = clean_command_name(
        application, ("open", "launch", "start", "run")
    )
    name = APP_ALIASES.get(name.lower(), name.lower())

    if not name:
        return "Please specify an application to open."

    if name == "browser":
        try:
            os.startfile("https://www.google.com")
            return "Opened your default browser."
        except OSError as exc:
            return f"Could not open your default browser: {exc}"

    if name in APPLICATIONS:
        try:
            subprocess.Popen(APPLICATIONS[name])
            return f"Opened {name}."
        except OSError:
            pass

    shortcuts = find_start_menu_shortcuts(name)
    if shortcuts:
        try:
            os.startfile(str(shortcuts[0]))
            return f"Opened {shortcuts[0].stem}."
        except OSError:
            pass

    entry = find_start_app_id(name)
    if entry:
        title, app_id = entry
        try:
            subprocess.Popen([
                "explorer.exe", f"shell:AppsFolder\\{app_id}"
            ])
            return f"Opened {title}."
        except OSError:
            pass

    executable = shutil.which(name)
    if executable:
        try:
            subprocess.Popen([executable])
            return f"Opened {name}."
        except OSError as exc:
            return f"Found {name}, but could not launch it: {exc}"

    return (
        f"I couldn't find an installed app matching '{name}'. "
        "Check the app's name in the Windows Start menu."
    )


# ==================================================
# APPLICATION CLOSING
# ==================================================

def close_application(application):
    """
    Find app windows by title, process, executable metadata, and shortcuts.
    Send WM_CLOSE requests only; never force-terminate an application.
    """
    requested = clean_command_name(
        application, ("close", "quit", "exit", "stop")
    )
    requested_norm = normalize(requested)

    if not requested_norm:
        return "Please specify an application to close."

    canonical = CLOSE_ALIASES.get(requested.lower(), requested.lower())
    canonical_norm = normalize(canonical)

    hints = list(dict.fromkeys(
        [requested_norm, canonical_norm]
        + [
            normalize(item)
            for item in CLOSE_PROCESS_HINTS.get(canonical, [])
        ]
    ))
    hints = [item for item in hints if item]

    requested_b64 = base64.b64encode(
        requested.encode("utf-8")
    ).decode("ascii")
    canonical_b64 = base64.b64encode(
        canonical.encode("utf-8")
    ).decode("ascii")
    hints_b64 = base64.b64encode(
        json.dumps(hints).encode("utf-8")
    ).decode("ascii")

    # The app name is passed as Base64 so quotes or special characters
    # in a name cannot break the PowerShell script.
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'

$wanted = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String('__REQUESTED__')
)
$canonical = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String('__CANONICAL__')
)
$hintsText = [Text.Encoding]::UTF8.GetString(
    [Convert]::FromBase64String('__HINTS__')
)
$hints = @($hintsText | ConvertFrom-Json)

$wantedNorm = ($wanted -replace '[^a-zA-Z0-9]', '').ToLowerInvariant()
$canonicalNorm = ($canonical -replace '[^a-zA-Z0-9]', '').ToLowerInvariant()

# Match Start Menu shortcut names to their actual executable targets.
$shortcutTargets = @()
$roots = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
    "$env:ProgramData\Microsoft\Windows\Start Menu\Programs"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

try {
    $shell = New-Object -ComObject WScript.Shell

    foreach ($root in $roots) {
        Get-ChildItem -LiteralPath $root -Filter '*.lnk' -File -Recurse |
        ForEach-Object {
            $shortcutName = (
                $_.BaseName -replace '[^a-zA-Z0-9]', ''
            ).ToLowerInvariant()

            $nameMatches = (
                $shortcutName -eq $wantedNorm -or
                $shortcutName -eq $canonicalNorm -or
                ($wantedNorm.Length -ge 4 -and
                    $shortcutName.Contains($wantedNorm)) -or
                ($canonicalNorm.Length -ge 4 -and
                    $shortcutName.Contains($canonicalNorm))
            )

            if ($nameMatches) {
                $shortcut = $shell.CreateShortcut($_.FullName)
                if ($shortcut.TargetPath) {
                    $target = [IO.Path]::GetFileNameWithoutExtension(
                        $shortcut.TargetPath
                    )
                    $targetNorm = (
                        $target -replace '[^a-zA-Z0-9]', ''
                    ).ToLowerInvariant()

                    if ($targetNorm) {
                        $shortcutTargets += $targetNorm
                    }
                }
            }
        }
    }
} catch {}

# Enumerate visible top-level windows, including windows not exposed
# reliably by Get-Process.MainWindowHandle.
Add-Type @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class PetalWindowRecord {
    public IntPtr Handle { get; set; }
    public int ProcessId { get; set; }
    public string Title { get; set; }
}

public static class PetalWindowEnumerator {
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(
        EnumWindowsProc callback, IntPtr extra
    );

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowTextLength(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(
        IntPtr hWnd, StringBuilder text, int count
    );

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(
        IntPtr hWnd, out uint processId
    );

    public static List<PetalWindowRecord> GetVisibleWindows() {
        var result = new List<PetalWindowRecord>();

        EnumWindows(delegate(IntPtr hWnd, IntPtr lParam) {
            if (!IsWindowVisible(hWnd)) return true;

            int length = GetWindowTextLength(hWnd);
            if (length <= 0) return true;

            var text = new StringBuilder(length + 1);
            GetWindowText(hWnd, text, text.Capacity);

            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);

            if (pid != 0 && text.Length > 0) {
                result.Add(new PetalWindowRecord {
                    Handle = hWnd,
                    ProcessId = (int)pid,
                    Title = text.ToString()
                });
            }
            return true;
        }, IntPtr.Zero);

        return result;
    }
}
'@

$windows = [PetalWindowEnumerator]::GetVisibleWindows()
$matches = @()

foreach ($window in $windows) {
    $process = Get-Process -Id $window.ProcessId
    if (-not $process) { continue }

    $processName = [string]$process.ProcessName
    $processNorm = (
        $processName -replace '[^a-zA-Z0-9]', ''
    ).ToLowerInvariant()

    $title = [string]$window.Title
    $titleNorm = ($title -replace '[^a-zA-Z0-9]', '').ToLowerInvariant()

    $exePath = ''
    $productName = ''
    $fileDescription = ''

    try { $exePath = [string]$process.Path } catch {}

    if ($exePath) {
        try {
            $version = (Get-Item -LiteralPath $exePath).VersionInfo
            $productName = [string]$version.ProductName
            $fileDescription = [string]$version.FileDescription
        } catch {}
    }

    $exeName = $processName
    if ($exePath) {
        $candidateExe = [IO.Path]::GetFileNameWithoutExtension($exePath)
        if ($candidateExe) { $exeName = $candidateExe }
    }

    $exeNorm = ($exeName -replace '[^a-zA-Z0-9]', '').ToLowerInvariant()
    $productNorm = (
        $productName -replace '[^a-zA-Z0-9]', ''
    ).ToLowerInvariant()
    $descriptionNorm = (
        $fileDescription -replace '[^a-zA-Z0-9]', ''
    ).ToLowerInvariant()

    $fields = @(
        $processNorm, $exeNorm, $productNorm,
        $descriptionNorm, $titleNorm
    )
    $matched = $false

    foreach ($hint in $hints) {
        $hintNorm = (
            [string]$hint -replace '[^a-zA-Z0-9]', ''
        ).ToLowerInvariant()

        if (-not $hintNorm) { continue }

        foreach ($field in $fields) {
            if (-not $field) { continue }

            if ($field -eq $hintNorm) {
                $matched = $true
                break
            }

            if ($hintNorm.Length -ge 4 -and
                $field.Contains($hintNorm)) {
                $matched = $true
                break
            }
        }

        if ($matched) { break }
    }

    if (-not $matched -and $shortcutTargets.Count -gt 0) {
        if ($shortcutTargets -contains $processNorm -or
            $shortcutTargets -contains $exeNorm) {
            $matched = $true
        }
    }

    if ($matched) {
        $matches += [PSCustomObject]@{
            Handle = $window.Handle
            ProcessName = $processName
            Title = $title
        }
    }
}

if (-not $matches -or $matches.Count -eq 0) {
    Write-Output 'NO_MATCH'
    exit
}

Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class PetalCloseMessage {
    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool PostMessage(
        IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam
    );
}
'@

$sent = 0
$seen = @{}

foreach ($window in $matches) {
    $key = [string]$window.Handle
    if ($seen.ContainsKey($key)) { continue }
    $seen[$key] = $true

    # WM_CLOSE asks the app to close normally; it does not kill the process.
    $ok = [PetalCloseMessage]::PostMessage(
        [IntPtr]$window.Handle,
        0x0010,
        [IntPtr]::Zero,
        [IntPtr]::Zero
    )

    if ($ok) {
        $sent++
        Write-Output (
            "CLOSE_SENT:" + $window.ProcessName + ":" + $window.Title
        )
    }
}

if ($sent -eq 0) { Write-Output 'CLOSE_FAILED' }
"""

    script = script.replace("__REQUESTED__", requested_b64)
    script = script.replace("__CANONICAL__", canonical_b64)
    script = script.replace("__HINTS__", hints_b64)

    try:
        result = run_hidden([
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", script,
        ])

        output = result.stdout.strip()

        if "CLOSE_SENT:" in output:
            closed = []

            for line in output.splitlines():
                if line.startswith("CLOSE_SENT:"):
                    parts = line.split(":", 2)
                    if len(parts) == 3:
                        closed.append(f"{parts[1]} ({parts[2]})")

            details = "; ".join(closed[:4])
            extra = " and other matching windows" if len(closed) > 4 else ""

            return (
                f"Sent a normal close request for {requested}: "
                f"{details}{extra}."
            )

        if "NO_MATCH" in output:
            return (
                f"I couldn't identify an open window for '{requested}'. "
                "Make sure the app is open and try its Start menu name."
            )

        if result.returncode != 0 and result.stderr.strip():
            last_error = result.stderr.strip().splitlines()[-1]
            return (
                f"Windows couldn't inspect windows for '{requested}'. "
                f"Details: {last_error}"
            )

        return (
            f"I found no window I could safely close for '{requested}'. "
            "The app may be running without a visible window."
        )

    except subprocess.TimeoutExpired:
        return f"Timed out while looking for '{requested}'."
    except (OSError, subprocess.SubprocessError) as error:
        return f"Could not request closing {requested}: {error}"


# ==================================================
# UNIVERSAL FOLDER OPENING
# ==================================================

def open_folder(folder):
    raw = str(folder).strip().strip('"').strip("'")
    raw = re.sub(
        r"^(please\s+)?(open|show|launch|go to|navigate to)\s+",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()
    raw = re.sub(r"[.!?]+$", "", raw).strip()

    if not raw:
        return "Please specify a folder or drive."

    cleaned = re.sub(
        r"\s+folder$", "", raw, flags=re.IGNORECASE
    ).strip()
    normalized = cleaned.lower()

    if normalized in {
        "file explorer", "explorer", "file manager",
        "this pc", "computer", "my computer",
    }:
        try:
            subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            return "Opened This PC in File Explorer."
        except OSError as exc:
            return f"Could not open File Explorer: {exc}"

    drive_match = re.fullmatch(r"([a-z])\s*(?:drive|disk)", normalized)

    if drive_match:
        target = Path(drive_match.group(1).upper() + ":\\")
        if not target.exists():
            return f"Drive {target} is not available on this computer."
    else:
        target = get_known_folders().get(normalized)

        if target is None:
            target = Path(os.path.expandvars(cleaned)).expanduser()

            if not target.is_absolute():
                return (
                    f"I don't recognize the folder '{cleaned}'. "
                    "Try a known folder name or provide its full path."
                )

    try:
        target = Path(target)

        if not target.exists():
            return f"That folder or drive does not exist: {target}"
        if not target.is_dir():
            return f"That path is a file, not a folder: {target}"

        os.startfile(str(target))
        return f"Opened folder: {target}"

    except (OSError, ValueError) as exc:
        return f"Could not open that folder: {exc}"


# ==================================================
# DIRECT TEST
# ==================================================

if __name__ == "__main__":
    print("Petal Windows tools loaded.")
    print(list_available_drives())
