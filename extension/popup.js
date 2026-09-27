// SPDX-License-Identifier: GPL-3.0-or-later
document.getElementById("ver").textContent = `v${chrome.runtime.getManifest().version}`;

function render(s) {
  const dot = document.getElementById("dot");
  const state = document.getElementById("state");
  const tools = document.getElementById("tools");
  const servers = document.getElementById("servers");
  const list = s.servers || [];
  const up = list.filter((x) => x.alive).length;
  const mcpOk = s.connected && (s.mcpAlive || up > 0 || s.tools > 0);
  const studioOff = mcpOk && s.studio === false; // MCP up but no Studio attached
  const ok = mcpOk && !studioOff;
  dot.className = "dot " + (s.connected ? (ok ? "on" : "warn") : "");
  state.textContent = s.connected
    ? (ok ? "Connected · Roblox Studio ready"
        : studioOff ? "Studio not connected · enable the MCP server in Studio"
        : "Bridge OK · open Roblox Studio")
    : "Bridge offline";
  tools.textContent = s.connected ? `${s.tools || 0} tools available` : "Run bridge.py";
  servers.textContent = s.connected
    ? list.map((x) => `${x.alive ? "●" : "○"} ${x.id} (${x.alive ? x.tools + " tools" : "down"})`).join("\n")
    : "";
}

function refresh() {
  chrome.runtime.sendMessage({ type: "status" }, (s) => s && render(s));
}

document.getElementById("reconnect").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "reconnect" }, () => setTimeout(refresh, 600));
});
document.getElementById("restart").addEventListener("click", (e) => {
  e.target.textContent = "Restarting…";
  chrome.runtime.sendMessage({ type: "restart_mcp" }, () => {
    e.target.textContent = "⟳ Restart Roblox server";
    setTimeout(refresh, 600);
  });
});
document.getElementById("settings").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("settings.html") });
});

const updateBox = document.getElementById("update");
const updateText = document.getElementById("update-text");
document.getElementById("update-open").addEventListener("click", () => {
  chrome.tabs.create({ url: "https://github.com/stlity/xw-studio-chrome" });
});
function renderUpdate(update) {
  if (!update || !update.version) return;
  updateText.textContent = `Версия ${update.version} уже доступна. Скачайте свежую папку extension и перезагрузите расширение.`;
  updateBox.classList.add("show");
}
function checkForUpdate() {
  chrome.runtime.sendMessage({ type: "update_status" }, (r) => {
    if (r && r.update) renderUpdate(r.update);
  });
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg && msg.type === "zs-status") render(msg);
  if (msg && msg.type === "xw-update") renderUpdate(msg.update);
});
refresh();
checkForUpdate();
setInterval(refresh, 2000);
setInterval(checkForUpdate, 5 * 60 * 1000);
