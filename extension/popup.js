// SPDX-License-Identifier: GPL-3.0-or-later
document.getElementById("ver").textContent = `v${chrome.runtime.getManifest().version}`;
const projectBox = document.getElementById("project");
const projectLabel = document.getElementById("project-label");
const projectInput = document.getElementById("godot-path");
let currentMode = "roblox";
let currentProjectPath = "";

function normalizeMode(mode) { return ["terminal", "godot"].includes(mode) ? mode : "roblox"; }
function render(s) {
  const mode = normalizeMode(s.mode);
  currentMode = mode;
  if (typeof s.projectPath === "string" && s.projectPath) {
    currentProjectPath = s.projectPath;
    projectInput.value = currentProjectPath;
  }
  ["roblox", "godot", "terminal"].forEach((x) => document.getElementById(`mode-${x}`).classList.toggle("active", mode === x));
  const list = s.servers || [];
  const up = list.filter((x) => x.alive).length;
  const mcpOk = s.connected && (s.mcpAlive || up > 0 || s.tools > 0);
  const studioOff = mcpOk && s.studio === false;
  const ok = mcpOk && !studioOff;
  const godotReady = mode === "godot" && s.connected && !!currentProjectPath;
  const dotState = !s.connected ? "" : mode === "godot" ? (godotReady ? "on" : "warn") : mode === "terminal" ? "on" : (ok ? "on" : "warn");
  document.getElementById("dot").className = `dot ${dotState}`;
  const state = document.getElementById("state");
  state.textContent = s.connected
    ? mode === "godot" ? (godotReady ? "Connected · Godot project ready" : "Bridge connected · choose a Godot project")
      : mode === "terminal" ? "Connected · Terminal ready"
      : ok ? "Connected · Roblox Studio ready"
        : studioOff ? "Studio not connected · enable the MCP server in Studio"
        : "Bridge OK · open Roblox Studio"
    : "Bridge offline";
  document.getElementById("tools").textContent = s.connected ? `${s.tools || 0} tools available` : "Run bridge.py";
  document.getElementById("servers").textContent = s.connected
    ? mode === "godot" ? `● Godot project\n${currentProjectPath || "not selected"}`
      : mode === "terminal" ? "● terminal tools"
      : list.map((x) => `${x.alive ? "●" : "○"} ${x.id} (${x.alive ? x.tools + " tools" : "down"})`).join("\n")
    : "";
  projectBox.classList.toggle("show", mode === "godot");
  projectLabel.classList.toggle("show", mode === "godot");
  document.getElementById("hint").innerHTML = mode === "godot"
    ? "Godot: выберите папку с <code>project.godot</code>."
    : mode === "terminal" ? "Terminal: агент сможет запускать команды и читать/изменять файлы через bridge."
    : "Roblox: открой Studio и включи MCP-сервер.";
}
function refresh() { chrome.runtime.sendMessage({ type: "status" }, (s) => s && render(s)); }
function selectMode(mode) {
  mode = normalizeMode(mode);
  currentMode = mode;
  currentProjectPath = projectInput.value.trim() || currentProjectPath;
  chrome.storage.local.set({ xwTargetMode: mode, xwGodotProjectPath: currentProjectPath });
  chrome.runtime.sendMessage({ type: "set_mode", mode, project_path: currentProjectPath }, (r) => {
    if (!r || !r.ok) document.getElementById("state").textContent = "Bridge offline — выбор сохранён";
    refresh();
  });
}
document.getElementById("reconnect").addEventListener("click", () => { chrome.runtime.sendMessage({ type: "reconnect" }, () => setTimeout(refresh, 600)); });
document.getElementById("restart").addEventListener("click", (e) => { e.target.textContent = "Restarting…"; chrome.runtime.sendMessage({ type: "restart_mcp" }, () => { e.target.textContent = "⟳ Перезапустить bridge"; setTimeout(refresh, 600); }); });
document.getElementById("mode-roblox").addEventListener("click", () => selectMode("roblox"));
document.getElementById("mode-terminal").addEventListener("click", () => selectMode("terminal"));
document.getElementById("mode-godot").addEventListener("click", () => selectMode("godot"));
projectInput.addEventListener("change", () => { currentProjectPath = projectInput.value.trim(); chrome.storage.local.set({ xwGodotProjectPath: currentProjectPath }); if (currentMode === "godot") selectMode("godot"); });
document.getElementById("godot-browse").addEventListener("click", () => {
  const button = document.getElementById("godot-browse"); button.textContent = "Открываю…"; button.disabled = true;
  chrome.runtime.sendMessage({ type: "browse_godot_project" }, (r) => {
    button.textContent = "Обзор"; button.disabled = false;
    if (r && r.ok && r.path) { currentProjectPath = r.path; projectInput.value = r.path; currentMode = "godot"; refresh(); }
    else if (r && !r.cancelled) document.getElementById("state").textContent = r.error || "Не удалось открыть выбор папки";
  });
});
document.getElementById("settings").addEventListener("click", () => chrome.tabs.create({ url: chrome.runtime.getURL("settings.html") }));
const updateBox = document.getElementById("update"), updateText = document.getElementById("update-text");
document.getElementById("update-open").addEventListener("click", () => chrome.tabs.create({ url: "https://github.com/stlity/xw-studio-chrome" }));
function renderUpdate(update) { if (!update || !update.version) return; updateText.textContent = `Версия ${update.version} уже доступна. Скачайте свежую папку extension и перезагрузите расширение.`; updateBox.classList.add("show"); }
function checkForUpdate() { chrome.runtime.sendMessage({ type: "update_status" }, (r) => { if (r && r.update) renderUpdate(r.update); }); }
chrome.runtime.onMessage.addListener((msg) => { if (msg && msg.type === "zs-status") render(msg); if (msg && msg.type === "xw-update") renderUpdate(msg.update); });
refresh(); checkForUpdate();
chrome.storage.local.get(["xwTargetMode", "xwGodotProjectPath"], (r) => { currentProjectPath = r.xwGodotProjectPath || ""; projectInput.value = currentProjectPath; if (r.xwTargetMode) selectMode(r.xwTargetMode); });
setInterval(refresh, 2000); setInterval(checkForUpdate, 5 * 60 * 1000);
