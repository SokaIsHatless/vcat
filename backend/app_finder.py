"""
Windows application discovery and safe launch.

Only apps that Windows' own Start Menu app registry (Get-StartApps) lists as
installed, user-facing programs can be opened — this is the allowlist. A hard
denylist blocks system/scripting/admin tools even if they somehow surface in
that list. Requests that don't clearly match anything installed get "did you
mean" suggestions instead of silently failing or launching the wrong thing.
"""

import difflib
import json
import os
import re
import subprocess
import sys

_DENYLIST = [
    "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "wt",
    "windows terminal", "regedit", "regedit.exe", "regedt32", "netsh",
    "cmdkey", "psexec", "taskmgr", "task manager",
    "services", "services.msc",
    "gpedit", "gpedit.msc", "group policy",
    "diskmgmt", "diskmgmt.msc", "disk management",
    "devmgmt", "devmgmt.msc", "device manager",
    "eventvwr", "event viewer",
    "mmc", "microsoft management console",
    "msconfig", "system configuration",
    "compmgmt", "compmgmt.msc", "computer management",
    "secpol", "secpol.msc", "local security policy",
    "perfmon", "performance monitor",
    "taskschd", "task scheduler",
]

_FUZZY_CUTOFF = 0.6
_STRONG_MATCH_RATIO = 0.8


def _is_windows() -> bool:
    return sys.platform == "win32"


def _is_denylisted(name: str) -> bool:
    """Word-boundary, case-insensitive match against the hard denylist."""
    lowered = name.lower()
    return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in _DENYLIST)


def _fetch_installed_apps() -> list[dict]:
    """Query Windows' canonical Start Menu app list via PowerShell Get-StartApps."""
    if not _is_windows():
        return []

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Get-StartApps | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except ValueError:
        return []

    if isinstance(data, dict):
        data = [data]

    apps = []
    for entry in data:
        name = entry.get("Name")
        app_id = entry.get("AppID")
        if name and app_id:
            apps.append({"name": name, "app_id": app_id})
    return apps


_installed_apps: list[dict] = _fetch_installed_apps()


def refresh_installed_apps() -> list[dict]:
    """Force a re-scan of Windows' installed-apps list (e.g. after installing something new)."""
    global _installed_apps
    _installed_apps = _fetch_installed_apps()
    return _installed_apps


def _get_installed_apps() -> list[dict]:
    global _installed_apps
    if not _installed_apps:
        _installed_apps = _fetch_installed_apps()
    return _installed_apps


def _find_best_match(query: str, apps: list[dict]):
    """Fuzzy-match query against installed app names. Returns (best app or None, top suggestions)."""
    names = [a["name"] for a in apps]
    close = difflib.get_close_matches(query, names, n=3, cutoff=_FUZZY_CUTOFF)
    if not close:
        return None, []

    query_lower = query.lower()
    top = close[0]
    top_lower = top.lower()
    is_strong = (
        query_lower in top_lower
        or top_lower in query_lower
        or difflib.SequenceMatcher(None, query_lower, top_lower).ratio() >= _STRONG_MATCH_RATIO
    )
    if not is_strong:
        return None, close

    by_name = {a["name"]: a for a in apps}
    return by_name[top], close


def _launch_app(app_id: str) -> None:
    """Launch a Start Menu app by its Windows AppID."""
    if re.match(r"^[a-zA-Z]:\\", app_id) or app_id.lower().endswith((".lnk", ".exe")):
        os.startfile(app_id)
    else:
        subprocess.run(["explorer.exe", f"shell:AppsFolder\\{app_id}"], check=False)


def open_application(app_name: str) -> dict:
    """Open an installed Windows Start Menu app by name, with denylist and allowlist guardrails."""
    query = app_name.strip()
    if not query:
        return {"error": "I need an application name to open."}

    if _is_denylisted(query):
        return {"error": "That's a system tool, not a normal app — refusing to open. Ask a grown-up."}

    apps = _get_installed_apps()
    if not apps:
        return {"error": "I couldn't read the list of installed apps."}

    match, suggestions = _find_best_match(query, apps)
    if not match:
        if suggestions:
            return {"error": f"I don't see '{query}' installed. Did you mean: {', '.join(suggestions[:3])}?"}
        return {"error": f"I don't see '{query}' installed."}

    if _is_denylisted(match["name"]):
        return {"error": "That's a system tool, not a normal app — refusing to open. Ask a grown-up."}

    try:
        _launch_app(match["app_id"])
    except OSError as exc:
        return {"error": f"Found {match['name']}, but couldn't launch it: {exc}"}

    return {"opened": match["name"]}
