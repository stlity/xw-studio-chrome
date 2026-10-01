#!/usr/bin/env python3
"""XW Studio text launcher.

A small interactive CLI for Windows, macOS and Linux. It starts bridge.py in
this terminal, keeps the bridge output visible, and does not require PyQt5 or
open another control window.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRIDGE = ROOT / "bridge.py"
PORT = int(os.environ.get("ZS_BRIDGE_PORT", "17613"))
VERSION = "1.7"


def _windows_no_window_flags() -> int:
    """Hide helper console windows without hiding this launcher console."""
    if sys.platform != "win32":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _clear():
    os.system("cls" if os.name == "nt" else "clear")


def _banner():
    print("=" * 68)
    print(f"  XW Studio Bridge v{VERSION} - text launcher")
    print("  Roblox Studio | Godot Engine | Local Terminal")
    print("=" * 68)


def _status(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def _read_output(proc: subprocess.Popen[str], log_path: Path, stop: threading.Event):
    log_path.parent.mkdir(exist_ok=True)
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            line = line.rstrip("\r\n")
            if not line:
                continue
            print(line, flush=True)
            log.write(line + "\n")
            log.flush()
    stop.set()


def _choose_mode() -> tuple[str, str]:
    print("\nSelect target mode:")
    print("  [1] Roblox Studio")
    print("  [2] Godot Engine")
    print("  [3] Local Terminal")
    while True:
        choice = input("\nTarget [1/2/3]: ").strip().lower()
        if choice in {"1", "r", "roblox"}:
            return "roblox", ""
        if choice in {"2", "g", "godot"}:
            while True:
                value = input("Godot project folder (contains project.godot): ").strip().strip('"')
                path = Path(os.path.expandvars(os.path.expanduser(value))).resolve()
                if (path / "project.godot").is_file():
                    return "godot", str(path)
                print(f"  Not a Godot project: {path}")
                print("  Enter another folder or type 'back' to return to the mode menu.")
                if value.lower() == "back":
                    break
        if choice in {"3", "t", "terminal"}:
            return "terminal", ""
        print("  Choose 1, 2 or 3.")


def _python_executable() -> str:
    configured = os.environ.get("XW_PYTHON", "").strip()
    if configured and Path(configured).exists():
        return configured
    return sys.executable


def _start_bridge(mode: str, project: str, port: int):
    env = os.environ.copy()
    env["XW_MODE"] = mode
    env["ZS_BRIDGE_PORT"] = str(port)
    if project:
        env["XW_GODOT_PROJECT"] = project
    else:
        env.pop("XW_GODOT_PROJECT", None)
    flags = _windows_no_window_flags()
    command = [_python_executable(), str(BRIDGE)]
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=None,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=flags,
        )
    except OSError as exc:
        print(f"\nERROR: bridge could not start: {exc}")
        return None
    return proc


def _stop_bridge(proc: subprocess.Popen[str]):
    """Stop bridge and its MCP child tree, including hidden StudioMCP.exe."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
        except (OSError, subprocess.TimeoutExpired):
            proc.kill()
    else:
        proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def _print_help():
    print("\nCommands while bridge is running:")
    print("  s  status       check the local WebSocket")
    print("  l  log          show the last 30 bridge log lines")
    print("  r  restart      stop and start with the same mode")
    print("  m  mode         stop and choose another target")
    print("  q  quit         stop bridge and exit")
    print("  h  help")


def _show_log():
    path = ROOT / "logs" / "bridge_debug.log"
    if not path.exists():
        print("No bridge log yet.")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    print("\n" + "\n".join(lines[-30:]))


def main() -> int:
    if not BRIDGE.is_file():
        print(f"ERROR: bridge.py not found next to launcher.py: {BRIDGE}")
        return 1
    _clear()
    _banner()
    print("This is the only launcher window. Keep it open or minimize it.")
    print("No PyQt5 is required. Roblox helper windows are hidden automatically.")
    mode, project = _choose_mode()
    port = PORT
    while True:
        custom = input(f"Bridge port [{port}] (Enter to keep): ").strip()
        if not custom:
            break
        try:
            port = int(custom)
            if 1024 <= port <= 65535:
                break
        except ValueError:
            pass
        print("  Port must be a number between 1024 and 65535.")

    log_path = ROOT / "logs" / "launcher.log"
    stop_reader = threading.Event()
    proc = None
    reader = None

    while True:
        _clear()
        _banner()
        print(f"Mode: {mode}")
        if project:
            print(f"Godot project: {project}")
        print(f"WebSocket: ws://127.0.0.1:{port}")
        print("Starting bridge...\n")
        proc = _start_bridge(mode, project, port)
        if proc is None:
            input("Press Enter to exit...")
            return 1
        stop_reader.clear()
        reader = threading.Thread(target=_read_output, args=(proc, log_path, stop_reader), daemon=True)
        reader.start()
        time.sleep(1.0)
        print("\n" + ("Bridge socket is listening." if _status(port) else "Waiting for bridge socket..."))
        _print_help()

        changed_mode = False
        while proc.poll() is None:
            try:
                command = input("\nxw> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                command = "q"
            if command in {"s", "status"}:
                print(f"WebSocket: {'online' if _status(port) else 'offline'}; process pid={proc.pid}")
            elif command in {"l", "log"}:
                _show_log()
            elif command in {"h", "help", "?"}:
                _print_help()
            elif command in {"r", "restart"}:
                print("Restarting bridge...")
                _stop_bridge(proc)
                break
            elif command in {"m", "mode"}:
                print("Stopping bridge and returning to mode selection...")
                _stop_bridge(proc)
                mode, project = _choose_mode()
                changed_mode = True
                break
            elif command in {"q", "quit", "exit"}:
                print("Stopping bridge...")
                _stop_bridge(proc)
                return 0
            elif command:
                print("Unknown command. Type h for help.")
        else:
            print(f"\nBridge stopped with exit code {proc.returncode}.")
            if not changed_mode:
                answer = input("Press Enter to restart, or type q to quit: ").strip().lower()
                if answer in {"q", "quit", "exit"}:
                    return 0
        if not changed_mode and proc.poll() is not None:
            continue


if __name__ == "__main__":
    raise SystemExit(main())
