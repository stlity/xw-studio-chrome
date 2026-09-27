/* XW Studio multi-agent settings */
(() => {
  "use strict";
  const AI = [
    ["DeepSeek", "chat.deepseek.com"], ["ChatGPT", "chatgpt.com"], ["Gemini", "gemini.google.com"],
    ["Kimi", "kimi.ai"], ["GLM", "chat.z.ai"], ["Qwen", "chat.qwen.ai"], ["Arena", "arena.ai"],
    ["Microsoft Copilot", "copilot.microsoft.com"], ["HuggingChat", "huggingface.co/chat"], ["Mistral Vibe", "chat.mistral.ai"], ["Meta AI", "meta.ai"], ["Local / other MCP", "local"]
  ];
  const roleDefs = ZS.DEFAULT_AGENT_ROLES;
  const ids = Object.keys(roleDefs);
  const $ = (id) => document.getElementById(id);
  let config = null;
  const defaultConfig = () => ({
    enabled: true, workflow: "plan-then-build", safetyMode: "confirm-risky", planMode: true, autoDebug: true,
    roles: Object.fromEntries(ids.map((id, i) => [id, { enabled: true, ais: [AI[i % 3][0]] }]))
  });
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;", "'":"&#39;"}[c]));
  function normalize(raw) {
    const base = defaultConfig();
    if (!raw) return base;
    base.enabled = raw.enabled !== false; base.workflow = raw.workflow || base.workflow; base.safetyMode = raw.safetyMode || base.safetyMode;
    base.planMode = raw.planMode !== false; base.autoDebug = raw.autoDebug !== false;
    ids.forEach((id) => { if (raw.roles && raw.roles[id]) base.roles[id] = { enabled: raw.roles[id].enabled !== false, ais: Array.isArray(raw.roles[id].ais) ? raw.roles[id].ais : base.roles[id].ais }; });
    return base;
  }
  function render() {
    $("agents-enabled").checked = config.enabled; $("workflow").value = config.workflow; $("safety").value = config.safetyMode;
    $("plan-mode").checked = config.planMode; $("auto-debug").checked = config.autoDebug;
    $("roles").innerHTML = ids.map((id) => {
      const r = roleDefs[id], saved = config.roles[id];
      const ais = AI.map(([name, host]) => `<label class="ai-choice"><input type="checkbox" data-role="${id}" data-ai="${esc(name)}" ${saved.ais.includes(name) ? "checked" : ""}><span class="switch small"></span><span>${esc(name)}</span><small>${esc(host)}</small></label>`).join("");
      return `<article class="role ${saved.enabled ? "active" : "disabled"}"><div class="role-top"><div><h3>${esc(r.name)}</h3><p>${esc(r.prompt)}</p></div><label class="role-toggle"><input type="checkbox" class="role-enabled" data-role="${id}" ${saved.enabled ? "checked" : ""}><span class="switch"></span><b>В работе</b></label></div><div class="ai-grid"><span class="ai-label">Назначить AI:</span>${ais}</div></article>`;
    }).join("");
    $("roles").querySelectorAll(".role-enabled").forEach((e) => e.addEventListener("change", () => { config.roles[e.dataset.role].enabled = e.checked; render(); }));
    $("roles").querySelectorAll("input[data-ai]").forEach((e) => e.addEventListener("change", () => { const list = config.roles[e.dataset.role].ais; config.roles[e.dataset.role].ais = e.checked ? [...new Set([...list, e.dataset.ai])] : list.filter((x) => x !== e.dataset.ai); updatePreview(); }));
    $("agents-enabled").onchange = (e) => { config.enabled = e.target.checked; updatePreview(); };
    $("workflow").onchange = (e) => { config.workflow = e.target.value; updatePreview(); };
    $("safety").onchange = (e) => { config.safetyMode = e.target.value; updatePreview(); };
    $("plan-mode").onchange = (e) => { config.planMode = e.target.checked; updatePreview(); };
    $("auto-debug").onchange = (e) => { config.autoDebug = e.target.checked; updatePreview(); };
    updatePreview();
  }
  function updatePreview() {
    const active = ids.filter((id) => config.roles[id].enabled);
    const text = active.length ? active.map((id) => `${roleDefs[id].name}: ${(config.roles[id].ais.length ? config.roles[id].ais.join(", ") : "активный AI")}`).join("\n") : "Команда выключена или роли не выбраны.";
    $("preview").textContent = `XW STUDIO MULTI-AGENT PROFILE\nWorkflow: ${config.workflow}\nSafety: ${config.safetyMode}\nPlan preview: ${config.planMode ? "ON" : "OFF"}\nAuto-debug: ${config.autoDebug ? "ON" : "OFF"}\n\n${text}`;
    $("save-state").textContent = "Есть несохранённые изменения";
  }
  function save() {
    chrome.storage.local.set({ xwMultiAgentConfig: config }, () => {
      $("save-state").textContent = "Сохранено"; $("toast").textContent = "Настройки применены ✓";
      chrome.tabs.query({}, (tabs) => tabs.forEach((tab) => { try { chrome.tabs.sendMessage(tab.id, { type: "xw-agent-config", config }); } catch {} }));
      setTimeout(() => { $("toast").textContent = ""; }, 1800);
    });
  }
  $("select-all").onclick = () => { const names = AI.map((x) => x[0]); ids.forEach((id) => { config.roles[id].ais = [...names]; }); render(); };
  $("save").onclick = save;
  $("reset").onclick = () => { config = defaultConfig(); render(); };
  chrome.storage.local.get("xwMultiAgentConfig", (r) => { config = normalize(r.xwMultiAgentConfig); render(); });
})();
