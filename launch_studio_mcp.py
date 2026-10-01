# SPDX-License-Identifier: GPL-3.0-or-later
# launch_studio_mcp.py
# ──────────────────────────────────────────────────────────────────────────
#  Robust launcher for Roblox's StudioMCP.exe (the Studio MCP studio server).
#
#  Roblox ships a %LOCALAPPDATA%\Roblox\mcp.bat, but it hard-codes ONE Studio
#  version path. When Studio auto-updates, that folder is eventually removed and
#  the .bat's fallback branch is broken batch syntax (`else` on its own line),
#  so StudioMCP.exe never launches -> the bridge sees 0 tools -> the extension
#  reports "Bridge or Studio offline".
#
#  This launcher sidesteps that entirely: it finds the NEWEST StudioMCP.exe
#  across all installed Studio versions and launches it, transparently forwarding
#  stdio and any CLI args. It also supports an explicit override path via
#  `ZS_STUDIO_MCP_PATH` when discovery is not enough.
# ──────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

ENV_OVERRIDE = "ZS_STUDIO_MCP_PATH"
WINDOWS_STUDIO_EXECUTABLES = ("RobloxStudioBeta.exe", "RobloxStudio.exe")
MAC_STUDIO_EXECUTABLES = ("RobloxStudio", "RobloxStudioBeta", "Roblox")


def _candidate_roots() -> list[Path]:
    """Directories that may contain Roblox Studio version folders (Windows)."""
    roots: list[Path] = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        roots.append(Path(local_appdata) / "Roblox" / "Versions")
    for env in ("ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(env)
        if value:
            roots.append(Path(value) / "Roblox" / "Versions")
    return roots


def _resolve_override_path(path_value: str) -> Optional[Path]:
    path = Path(path_value).expanduser()
    if path.is_file():
        return path
    if path.is_dir():
        if sys.platform == "darwin":
            candidate = path / "Contents" / "MacOS" / "StudioMCP"
        else:
            candidate = path / "StudioMCP.exe"
        if candidate.is_file():
            return candidate
    return None


def _newest_path(paths: Iterable[Path]) -> Optional[Path]:
    try:
        return max(paths, key=lambda p: p.stat().st_mtime)
    except (ValueError, OSError):
        return None


def _find_studio_mcp_windows() -> Optional[Path]:
    """Return the path to the StudioMCP.exe of the live Studio install, or None.

    Roblox leaves "zombie" version folders behind after an update: they still
    contain a StudioMCP.exe but no RobloxStudioBeta.exe / RobloxStudio.exe
    (the actual Studio is gone). Picking the newest StudioMCP.exe by mtime can
    land on such a zombie, which launches fine but has no Studio to attach to ->
    the bridge sees 0 tools.

    We only consider version folders that ALSO contain a current Studio
    executable, and prefer the newest of those. We keep zombie StudioMCP.exe
    paths only as a last-resort fallback if no paired install exists.
    """
    paired: list[Path] = []
    orphans: list[Path] = []
    for root in _candidate_roots():
        if not root.is_dir():
            continue
        try:
            for version_dir in root.iterdir():
                if not version_dir.is_dir():
                    continue
                studio_mcp = version_dir / "StudioMCP.exe"
                if not studio_mcp.is_file():
                    continue
                if any((version_dir / exe_name).is_file() for exe_name in WINDOWS_STUDIO_EXECUTABLES):
                    paired.append(studio_mcp)
                else:
                    orphans.append(studio_mcp)
        except OSError:
            continue
    return _newest_path(paired) or _newest_path(orphans)


def _mac_app_candidates() -> list[Path]:
    """Locations where Roblox Studio may be installed on macOS."""
    home = Path.home()
    return [
        Path("/Applications/RobloxStudio.app"),
        home / "Applications" / "RobloxStudio.app",
        Path("/Applications/Roblox.app"),
        home / "Applications" / "Roblox.app",
        Path("/Applications/RobloxStudioBeta.app"),
        home / "Applications" / "RobloxStudioBeta.app",
    ]


def _find_studio_mcp_mac() -> Optional[Path]:
    """Return the path to StudioMCP inside a Roblox Studio app bundle, or None."""
    for app in _mac_app_candidates():
        macos_dir = app / "Contents" / "MacOS"
        studio_mcp = macos_dir / "StudioMCP"
        if not studio_mcp.is_file():
            continue
        if any((macos_dir / exe_name).is_file() for exe_name in MAC_STUDIO_EXECUTABLES):
            return studio_mcp
    return None


def find_studio_mcp() -> Optional[Path]:
    override_value = os.environ.get(ENV_OVERRIDE)
    if override_value:
        override_path = _resolve_override_path(override_value)
        if override_path:
            return override_path
        sys.stderr.write(
            f"launch_studio_mcp: {ENV_OVERRIDE} is set but does not point to a valid StudioMCP binary: {override_value}\n"
        )
    if sys.platform == "darwin":
        return _find_studio_mcp_mac()
    return _find_studio_mcp_windows()


def _windows_mcp_command() -> Optional[list[str]]:
    """Use Roblox's official mcp.bat when present; it supplies current args."""
    if sys.platform != "win32":
        return None
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_appdata:
        return None
    batch = Path(local_appdata) / "Roblox" / "mcp.bat"
    if not batch.is_file():
        return None
    comspec = os.environ.get("ComSpec", "cmd.exe")
    # /d disables AutoRun hooks. CALL is important: it executes the batch file
    # and returns control to this wrapper instead of making cmd treat the path
    # as an invalid executable argument on some Windows/Python combinations.
    return [comspec, "/d", "/c", "call", str(batch)]


def main() -> int:
    # Roblox's generated mcp.bat is currently malformed on some Windows
    # installs, especially when LOCALAPPDATA contains a non-ASCII username.
    # Launch the paired StudioMCP.exe directly so cmd batch parsing cannot
    # corrupt the stdio MCP stream. find_studio_mcp prefers a version folder
    # that also contains the live RobloxStudio executable.
    exe = find_studio_mcp()
    if exe and sys.platform == "win32":
        sys.stderr.write(f"launch_studio_mcp: using direct StudioMCP.exe {exe}\n")
        sys.stderr.flush()
        kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        proc = subprocess.Popen([str(exe)] + sys.argv[1:], **kwargs)
        try:
            return proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            return proc.wait()
    official_command = _windows_mcp_command()
    if official_command:
        sys.stderr.write("launch_studio_mcp: using Roblox official mcp.bat\n")
        sys.stderr.flush()
        kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
        try:
            proc = subprocess.Popen(official_command, **kwargs)
            try:
                return proc.wait()
            except KeyboardInterrupt:
                proc.terminate()
                return proc.wait()
        except OSError as exc:
            sys.stderr.write(f"launch_studio_mcp: mcp.bat failed ({exc}); falling back to StudioMCP.exe\n")
            sys.stderr.flush()
    exe = find_studio_mcp()
    binary_name = "StudioMCP" if sys.platform == "darwin" else "StudioMCP.exe"
    if not exe:
        sys.stderr.write(
            f"launch_studio_mcp: no {binary_name} found. Open Roblox Studio and "
            "enable 'Studio as MCP server' (Assistant Settings > MCP Servers).\n"
        )
        return 1
    sys.stderr.write(f"launch_studio_mcp: using {exe}\n")
    sys.stderr.flush()
    kwargs = {}
    if sys.platform == "win32":
        # StudioMCP is a console executable. Without this flag Windows opens
        # a second black console window over Roblox Studio. Keep its inherited
        # stdio pipes for MCP, but suppress the separate console window.
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen([str(exe)] + sys.argv[1:], **kwargs)
    try:
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
