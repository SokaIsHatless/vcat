"""
Windows application discovery and safe launch.

Searches installed applications without a hardcoded whitelist by combining:
  - Start Menu shortcuts (.lnk)
  - Registry uninstall entries (DisplayName / InstallLocation / DisplayIcon)
  - Executables on PATH
  - Common install roots (Program Files, Program Files (x86), LocalAppData\\Programs)

Only discovered .exe or .lnk paths are launched — never arbitrary shell commands.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

MIN_MATCH_SCORE = 0.55
PROGRAM_FILES_MAX_DEPTH = 4
ALLOWED_LAUNCH_EXTENSIONS = {".exe", ".lnk"}


@dataclass(frozen=True)
class AppMatch:
    path: str
    label: str
    source: str
    score: float


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _tokens(name: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", name.lower()) if token}


def match_score(query: str, candidate: str) -> float:
    """Case-insensitive fuzzy score between a query and a candidate app name."""
    if not query or not candidate:
        return 0.0

    query_norm = normalize_name(query)
    candidate_norm = normalize_name(candidate)
    if not query_norm or not candidate_norm:
        return 0.0

    if query_norm == candidate_norm:
        return 1.0

    if query_norm in candidate_norm:
        return 0.92 - min(0.1, (len(candidate_norm) - len(query_norm)) * 0.002)

    if candidate_norm in query_norm:
        return 0.82

    query_token_set = _tokens(query)
    candidate_token_set = _tokens(candidate)
    if query_token_set and query_token_set <= candidate_token_set:
        return 0.88

    overlap = len(query_token_set & candidate_token_set)
    if overlap and query_token_set:
        token_ratio = overlap / len(query_token_set)
        if token_ratio >= 0.5:
            return 0.7 + token_ratio * 0.15

    return SequenceMatcher(None, query_norm, candidate_norm).ratio()


def _is_windows() -> bool:
    return sys.platform == "win32"


def _search_roots() -> list[Path]:
    roots: list[Path] = []
    for env_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value))
    local_programs = os.environ.get("LOCALAPPDATA")
    if local_programs:
        roots.append(Path(local_programs) / "Programs")
    return roots


def _start_menu_dirs() -> list[Path]:
    dirs: list[Path] = []
    for env_name in ("APPDATA", "PROGRAMDATA"):
        base = os.environ.get(env_name)
        if base:
            dirs.append(Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    return dirs


def _read_registry_value(key, name: str) -> str | None:
    import winreg

    try:
        value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _clean_display_icon(value: str) -> str | None:
    path = value.split(",", 1)[0].strip().strip('"')
    if path.lower().endswith(".exe") and os.path.isfile(path):
        return path
    return None


def _find_exe_in_dir(directory: str, preferred_names: list[str]) -> str | None:
    if not directory or not os.path.isdir(directory):
        return None

    for name in preferred_names:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate

    try:
        entries = os.listdir(directory)
    except OSError:
        return None

    exe_files = [entry for entry in entries if entry.lower().endswith(".exe")]
    if len(exe_files) == 1:
        return os.path.join(directory, exe_files[0])

    for entry in exe_files:
        stem = Path(entry).stem.lower()
        for preferred in preferred_names:
            preferred_stem = Path(preferred).stem.lower()
            if stem == preferred_stem:
                return os.path.join(directory, entry)

    return None


@lru_cache(maxsize=1)
def _collect_static_candidates() -> tuple[AppMatch, ...]:
    """Collect Start Menu, registry, and PATH candidates once per process."""
    seen_paths: set[str] = set()
    matches: list[AppMatch] = []

    def add(path: str, label: str, source: str) -> None:
        if not path or not label:
            return
        normalized_path = os.path.normcase(os.path.normpath(path))
        if normalized_path in seen_paths:
            return
        if not os.path.isfile(normalized_path):
            return
        ext = os.path.splitext(normalized_path)[1].lower()
        if ext not in ALLOWED_LAUNCH_EXTENSIONS:
            return
        seen_paths.add(normalized_path)
        matches.append(AppMatch(path=normalized_path, label=label, source=source, score=0.0))

    if not _is_windows():
        return tuple(matches)

    for start_dir in _start_menu_dirs():
        if not start_dir.is_dir():
            continue
        for shortcut in start_dir.rglob("*.lnk"):
            add(str(shortcut), shortcut.stem, "start_menu")

    import winreg

    registry_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, key_path in registry_roots:
        try:
            with winreg.OpenKey(hive, key_path) as root_key:
                subkey_count = winreg.QueryInfoKey(root_key)[0]
                for index in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(root_key, index)
                        with winreg.OpenKey(root_key, subkey_name) as subkey:
                            display_name = _read_registry_value(subkey, "DisplayName")
                            if not display_name:
                                continue

                            display_icon = _read_registry_value(subkey, "DisplayIcon")
                            install_location = _read_registry_value(subkey, "InstallLocation")

                            preferred = [
                                f"{display_name}.exe",
                                f"{Path(display_name).stem}.exe",
                            ]

                            exe_path = None
                            if display_icon:
                                exe_path = _clean_display_icon(display_icon)
                            if not exe_path and install_location:
                                exe_path = _find_exe_in_dir(install_location, preferred)
                            if exe_path:
                                add(exe_path, display_name, "registry")
                    except OSError:
                        continue
        except OSError:
            continue

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    for directory in path_entries:
        if not directory or not os.path.isdir(directory):
            continue
        try:
            for entry in os.listdir(directory):
                if entry.lower().endswith(".exe"):
                    add(os.path.join(directory, entry), Path(entry).stem, "path")
        except OSError:
            continue

    return tuple(matches)


def _collect_program_file_candidates(query: str) -> list[AppMatch]:
    """Search install roots for executables whose folder or file name matches the query."""
    if not _is_windows():
        return []

    seen_paths: set[str] = set()
    matches: list[AppMatch] = []

    for root in _search_roots():
        if not root.is_dir():
            continue

        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth > PROGRAM_FILES_MAX_DEPTH:
                dirnames.clear()
                continue

            folder_name = os.path.basename(dirpath)
            folder_score = match_score(query, folder_name)

            for filename in filenames:
                if not filename.lower().endswith(".exe"):
                    continue

                file_stem = Path(filename).stem
                file_score = match_score(query, file_stem)
                combined_score = max(folder_score, file_score)
                if combined_score < MIN_MATCH_SCORE:
                    continue

                full_path = os.path.normcase(os.path.normpath(os.path.join(dirpath, filename)))
                if full_path in seen_paths:
                    continue
                seen_paths.add(full_path)
                label = file_stem if file_score >= folder_score else folder_name
                matches.append(
                    AppMatch(
                        path=full_path,
                        label=label,
                        source="program_files",
                        score=combined_score,
                    )
                )

    return matches


def find_application(app_name: str) -> AppMatch | None:
    """Return the best installed application match for a natural-language app name."""
    query = app_name.strip()
    if not query:
        return None

    if not _is_windows():
        return None

    scored: list[AppMatch] = []

    for candidate in _collect_static_candidates():
        score = match_score(query, candidate.label)
        if score >= MIN_MATCH_SCORE:
            scored.append(
                AppMatch(
                    path=candidate.path,
                    label=candidate.label,
                    source=candidate.source,
                    score=score,
                )
            )

    for candidate in _collect_program_file_candidates(query):
        score = max(candidate.score, match_score(query, candidate.label))
        if score >= MIN_MATCH_SCORE:
            scored.append(
                AppMatch(
                    path=candidate.path,
                    label=candidate.label,
                    source=candidate.source,
                    score=score,
                )
            )

    if not scored:
        return None

    scored.sort(key=lambda item: (item.score, len(normalize_name(item.label))), reverse=True)
    return scored[0]


def launch_application(match: AppMatch) -> None:
    """Launch a previously discovered application path safely."""
    path = os.path.normpath(match.path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Application not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOWED_LAUNCH_EXTENSIONS:
        raise ValueError(f"Unsupported application type: {ext}")

    if ext == ".lnk":
        os.startfile(path)
        return

    subprocess.Popen([path], shell=False, cwd=os.path.dirname(path) or None)


def open_application(app_name: str) -> dict:
    """Find and open an installed Windows application by name."""
    query = app_name.strip()
    if not query:
        return {
            "opened": False,
            "app_name": app_name,
            "message": "I need an application name to open.",
        }

    if not _is_windows():
        return {
            "opened": False,
            "app_name": query,
            "message": "Opening applications is only supported on Windows.",
        }

    match = find_application(query)
    if not match:
        return {
            "opened": False,
            "app_name": query,
            "message": f"I couldn't find an installed application matching '{query}'.",
        }

    try:
        launch_application(match)
    except OSError as exc:
        return {
            "opened": False,
            "app_name": query,
            "message": f"I found {match.label}, but couldn't launch it: {exc}",
        }

    return {
        "opened": True,
        "app_name": query,
        "launched": match.label,
        "source": match.source,
        "message": f"Opened {match.label}.",
    }
