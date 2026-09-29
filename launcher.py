#!/usr/bin/env python3
"""XW Studio desktop launcher.

Starts bridge.py with a visible PyQt5 control panel instead of requiring a
command prompt choice. The bridge remains a child process and its stdout and
stderr are streamed into the Console tab.
"""
from __future__ import annotations

import os
import platform
import socket
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path


def _set_qt_plugin_path(QtCore):
    """Point Qt at the PyQt5 plugins before QtWidgets is imported."""
    os.environ.pop("QT_PLUGIN_PATH", None)
    os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    try:
        plugins = Path(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.PluginsPath))
        platforms = plugins / "platforms"
        if platforms.is_dir():
            # Environment variables can be ignored after QtCore is loaded;
            # set the library path through Qt's own API as well.
            QtCore.QCoreApplication.setLibraryPaths([str(plugins)])
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
    except Exception:
        pass


def _ensure_pyqt5():
    try:
        from PyQt5 import QtCore  # type: ignore
        _set_qt_plugin_path(QtCore)
        from PyQt5 import QtGui, QtWidgets  # type: ignore
        return QtCore, QtGui, QtWidgets
    except ImportError:
        print("PyQt5 is not installed. Installing it for the current user...", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "PyQt5"],
            check=False,
        )
        if result.returncode:
            raise SystemExit(
                "Could not install PyQt5. Run: python -m pip install --user PyQt5"
            )
        from PyQt5 import QtCore  # type: ignore
        _set_qt_plugin_path(QtCore)
        from PyQt5 import QtGui, QtWidgets  # type: ignore
        return QtCore, QtGui, QtWidgets


QtCore, QtGui, QtWidgets = _ensure_pyqt5()

APP_NAME = "XW Studio Bridge"
ROOT = Path(__file__).resolve().parent
BRIDGE = ROOT / "bridge.py"
DEFAULT_PORT = 17613


def _configure_qt_plugins(QtCore):
    """Make PyQt5 find its bundled Windows platform plugin.

    A stale QT_PLUGIN_PATH inherited from another Qt application is a common
    cause of the Windows "platform plugin could not be initialized" dialog,
    especially when this file is opened with pythonw.exe.
    """
    _set_qt_plugin_path(QtCore)


class StreamSignals(QtCore.QObject):
    line = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)


class BridgeReader(threading.Thread):
    def __init__(self, process, signals):
        super().__init__(daemon=True)
        self.process = process
        self.signals = signals

    def run(self):
        try:
            for raw in iter(self.process.stdout.readline, b""):
                if not raw:
                    break
                self.signals.line.emit(raw.decode("utf-8", errors="replace").rstrip())
        finally:
            code = self.process.wait()
            self.signals.finished.emit(code)


class Launcher(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.process = None
        self.reader = None
        self.signals = StreamSignals()
        self.signals.line.connect(self.append_console)
        self.signals.finished.connect(self.bridge_finished)
        self.log_file = ROOT / "logs" / "launcher.log"
        self.log_file.parent.mkdir(exist_ok=True)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(900, 620)
        self.resize(1080, 720)
        self.build_ui()
        self.apply_theme()
        self.refresh_status()
        self.status_timer = QtCore.QTimer(self)
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(1000)

    def build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        header = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("XW Studio")
        title.setObjectName("title")
        subtitle = QtWidgets.QLabel("Bridge control center for Roblox, Godot and Terminal")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        self.status_badge = QtWidgets.QLabel("● Bridge offline")
        self.status_badge.setObjectName("statusBadge")
        header.addWidget(self.status_badge, alignment=QtCore.Qt.AlignTop)
        root_layout.addLayout(header)

        self.tabs = QtWidgets.QTabWidget()
        root_layout.addWidget(self.tabs, 1)
        self.dashboard_tab = QtWidgets.QWidget()
        self.console_tab = QtWidgets.QWidget()
        self.settings_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.console_tab, "Console")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.build_dashboard()
        self.build_console()
        self.build_settings()

        bottom_box = QtWidgets.QGroupBox("Live console")
        bottom_layout = QtWidgets.QVBoxLayout(bottom_box)
        bottom_layout.setContentsMargins(10, 18, 10, 8)
        self.bottom_console = QtWidgets.QPlainTextEdit()
        self.bottom_console.setReadOnly(True)
        self.bottom_console.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.bottom_console.setMaximumBlockCount(8)
        self.bottom_console.setFixedHeight(112)
        self.bottom_console.setFont(QtGui.QFont("Consolas", 9))
        bottom_layout.addWidget(self.bottom_console)
        root_layout.addWidget(bottom_box)

        footer = QtWidgets.QHBoxLayout()
        self.footer_label = QtWidgets.QLabel("Ready. Choose a target and start the bridge.")
        self.footer_label.setObjectName("footer")
        footer.addWidget(self.footer_label)
        footer.addStretch()
        clear_btn = QtWidgets.QPushButton("Clear console")
        clear_btn.clicked.connect(lambda: (self.console.clear(), self.bottom_console.clear()))
        footer.addWidget(clear_btn)
        root_layout.addLayout(footer)

    def build_dashboard(self):
        layout = QtWidgets.QVBoxLayout(self.dashboard_tab)
        layout.setContentsMargins(8, 14, 8, 8)
        layout.setSpacing(14)

        mode_group = QtWidgets.QGroupBox("Target mode")
        mode_layout = QtWidgets.QGridLayout(mode_group)
        mode_layout.setContentsMargins(16, 22, 16, 16)
        mode_layout.setHorizontalSpacing(14)
        self.mode = QtWidgets.QComboBox()
        self.mode.addItem("Roblox Studio", "roblox")
        self.mode.addItem("Godot Engine", "godot")
        self.mode.addItem("Local Terminal", "terminal")
        self.mode.currentIndexChanged.connect(self.mode_changed)
        mode_layout.addWidget(QtWidgets.QLabel("Run XW Studio for:"), 0, 0)
        mode_layout.addWidget(self.mode, 0, 1)
        self.mode_hint = QtWidgets.QLabel()
        self.mode_hint.setWordWrap(True)
        self.mode_hint.setObjectName("hint")
        mode_layout.addWidget(self.mode_hint, 1, 0, 1, 2)
        self.project_row = QtWidgets.QWidget()
        project_layout = QtWidgets.QHBoxLayout(self.project_row)
        project_layout.setContentsMargins(0, 6, 0, 0)
        self.project_path = QtWidgets.QLineEdit()
        self.project_path.setPlaceholderText("Select a folder containing project.godot")
        self.browse_btn = QtWidgets.QPushButton("Browse…")
        self.browse_btn.clicked.connect(self.browse_project)
        project_layout.addWidget(self.project_path, 1)
        project_layout.addWidget(self.browse_btn)
        mode_layout.addWidget(self.project_row, 2, 0, 1, 2)
        layout.addWidget(mode_group)

        action_box = QtWidgets.QGroupBox("Bridge control")
        action_layout = QtWidgets.QHBoxLayout(action_box)
        action_layout.setContentsMargins(16, 22, 16, 16)
        self.start_btn = QtWidgets.QPushButton("Start bridge")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start_bridge)
        self.stop_btn = QtWidgets.QPushButton("Stop bridge")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_bridge)
        self.console_btn = QtWidgets.QPushButton("Open console")
        self.console_btn.clicked.connect(lambda: self.tabs.setCurrentWidget(self.console_tab))
        action_layout.addWidget(self.start_btn)
        action_layout.addWidget(self.stop_btn)
        action_layout.addWidget(self.console_btn)
        action_layout.addStretch()
        layout.addWidget(action_box)

        info = QtWidgets.QLabel(
            "Keep this window open or minimized while using the browser extension. "
            "The extension connects to the bridge on localhost."
        )
        info.setWordWrap(True)
        info.setObjectName("hint")
        layout.addWidget(info)
        layout.addStretch()
        self.mode_changed()

    def build_console(self):
        layout = QtWidgets.QVBoxLayout(self.console_tab)
        layout.setContentsMargins(8, 14, 8, 8)
        self.console = QtWidgets.QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.console.setFont(QtGui.QFont("Consolas", 10))
        layout.addWidget(self.console)

    def build_settings(self):
        layout = QtWidgets.QFormLayout(self.settings_tab)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setVerticalSpacing(16)
        self.port = QtWidgets.QSpinBox()
        self.port.setRange(1024, 65535)
        self.port.setValue(DEFAULT_PORT)
        self.python_path = QtWidgets.QLineEdit(sys.executable)
        self.python_path.setToolTip("Python interpreter used to launch bridge.py")
        self.auto_open_console = QtWidgets.QCheckBox("Open Console tab automatically when bridge starts")
        self.auto_open_console.setChecked(True)
        layout.addRow("Bridge port:", self.port)
        layout.addRow("Python interpreter:", self.python_path)
        layout.addRow("", self.auto_open_console)
        note = QtWidgets.QLabel(
            "Godot mode uses the project folder selected on Dashboard. "
            "Roblox mode starts the configured Roblox MCP server."
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        layout.addRow("", note)
        layout.addRow("", QtWidgets.QLabel("Launcher version: 1.1"))

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f5fbf5; color: #172019; }
            QTabWidget::pane { border: 1px solid #c8d8c8; border-radius: 12px; background: #fbfffb; }
            QTabBar::tab { background: #e1eee1; color: #304330; padding: 10px 20px; margin-right: 4px; border-radius: 8px 8px 0 0; }
            QTabBar::tab:selected { background: #b9e5be; color: #0b3b18; font-weight: 600; }
            QGroupBox { border: 1px solid #c8d8c8; border-radius: 12px; margin-top: 12px; padding-top: 12px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #246331; }
            QComboBox, QLineEdit, QSpinBox { background: #ffffff; border: 1px solid #a9c4aa; border-radius: 8px; padding: 9px; min-height: 18px; }
            QPushButton { background: #e2eee2; border: 1px solid #9fbea1; border-radius: 9px; padding: 10px 16px; min-width: 100px; }
            QPushButton:hover { background: #cce8ce; }
            QPushButton#primary { background: #2f7d3d; color: white; border: none; font-weight: 600; }
            QPushButton#primary:hover { background: #236631; }
            QPushButton:disabled { color: #819082; background: #edf2ed; }
            QPlainTextEdit { background: #101612; color: #b9f2bd; border: 1px solid #38523d; border-radius: 10px; padding: 8px; }
            QLabel#title { color: #185c28; font-size: 28px; font-weight: 700; }
            QLabel#subtitle, QLabel#hint, QLabel#footer { color: #5b6d5d; }
            QLabel#statusBadge { color: #b3261e; background: #ffdad6; border-radius: 10px; padding: 8px 12px; font-weight: 600; }
        """)

    def mode_value(self):
        return self.mode.currentData()

    def mode_changed(self):
        value = self.mode_value()
        hints = {
            "roblox": "Connects to Roblox Studio through the configured MCP server. Open a place and enable Studio MCP first.",
            "godot": "Uses the selected Godot project folder for safe file tools and headless validation.",
            "terminal": "Enables local shell and file tools. Use only for work you explicitly request from the AI.",
        }
        self.mode_hint.setText(hints[value])
        self.project_row.setVisible(value == "godot")

    def browse_project(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Godot project folder")
        if path:
            project = Path(path) / "project.godot"
            if not project.is_file():
                QtWidgets.QMessageBox.warning(self, "Not a Godot project", "The selected folder does not contain project.godot.")
                return
            self.project_path.setText(str(Path(path).resolve()))
            self.append_console(f"Selected Godot project: {path}")

    def append_console(self, text):
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"{stamp} {text}"
        self.console.appendPlainText(line)
        self.bottom_console.appendPlainText(line)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())
        try:
            with self.log_file.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass

    def start_bridge(self):
        if self.process and self.process.poll() is None:
            return
        if not BRIDGE.is_file():
            QtWidgets.QMessageBox.critical(self, "Bridge not found", f"bridge.py was not found next to launcher.py:\n{BRIDGE}")
            return
        mode = self.mode_value()
        if mode == "godot" and not self.project_path.text().strip():
            QtWidgets.QMessageBox.warning(self, "Select a project", "Choose a folder containing project.godot first.")
            return
        interpreter = self.python_path.text().strip() or sys.executable
        env = os.environ.copy()
        env["XW_MODE"] = mode
        env["ZS_BRIDGE_PORT"] = str(self.port.value())
        if mode == "godot":
            env["XW_GODOT_PROJECT"] = self.project_path.text().strip()
        else:
            env.pop("XW_GODOT_PROJECT", None)
        self.append_console(f"Starting bridge: mode={mode}, port={self.port.value()}")
        try:
            self.process = subprocess.Popen(
                [interpreter, str(BRIDGE)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
            )
        except OSError as exc:
            self.append_console(f"ERROR: could not start bridge: {exc}")
            QtWidgets.QMessageBox.critical(self, "Bridge start failed", str(exc))
            return
        self.reader = BridgeReader(self.process, self.signals)
        self.reader.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        if self.auto_open_console.isChecked():
            self.tabs.setCurrentWidget(self.console_tab)

    def stop_bridge(self):
        if not self.process or self.process.poll() is not None:
            return
        self.append_console("Stopping bridge...")
        self.process.terminate()
        try:
            self.process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            self.process.kill()

    def bridge_finished(self, code):
        self.append_console(f"Bridge stopped with exit code {code}")
        self.process = None
        self.reader = None
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def refresh_status(self):
        running = bool(self.process and self.process.poll() is None)
        connected = False
        if running:
            try:
                with socket.create_connection(("127.0.0.1", self.port.value()), timeout=0.15):
                    connected = True
            except OSError:
                pass
        if connected:
            self.status_badge.setText("● Bridge listening")
            self.status_badge.setStyleSheet("color:#146c2e; background:#c9f2ce; border-radius:10px; padding:8px 12px; font-weight:600;")
            self.footer_label.setText(f"Bridge is listening on ws://127.0.0.1:{self.port.value()}")
        elif running:
            self.status_badge.setText("● Starting…")
            self.status_badge.setStyleSheet("color:#765600; background:#fff0b5; border-radius:10px; padding:8px 12px; font-weight:600;")
            self.footer_label.setText("Bridge process is running; waiting for the WebSocket port…")
        else:
            self.status_badge.setText("● Bridge offline")
            self.status_badge.setStyleSheet("color:#b3261e; background:#ffdad6; border-radius:10px; padding:8px 12px; font-weight:600;")

    def closeEvent(self, event):
        if self.process and self.process.poll() is None:
            answer = QtWidgets.QMessageBox.question(
                self, "Stop bridge?", "The bridge is still running. Stop it and close XW Studio?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if answer != QtWidgets.QMessageBox.Yes:
                event.ignore()
                return
            self.stop_bridge()
        event.accept()


def main():
    if not BRIDGE.is_file():
        print(f"ERROR: bridge.py not found next to launcher.py: {BRIDGE}")
        return 1
    _configure_qt_plugins(QtCore)
    plugins = Path(QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.PluginsPath))
    qwindows = plugins / "platforms" / ("qwindows.dll" if os.name == "nt" else "libqxcb.so")
    if os.name == "nt" and not qwindows.is_file():
        print(f"ERROR: Qt Windows platform plugin is missing: {qwindows}")
        print("Run: python -m pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip")
        print("Then: python -m pip install --user --no-cache-dir PyQt5")
        return 1
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    window = Launcher()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
