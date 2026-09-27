// SPDX-License-Identifier: GPL-3.0-or-later
// Experimental provider for free AI chat sites with a conventional textarea/
// contenteditable composer. It intentionally uses resilient semantic selectors.
// Site-specific providers remain preferred when a site exposes a stable DOM API.
// eslint-disable-next-line no-unused-vars
const ZSProvider = (() => {
  "use strict";
  let diag = () => {};
  let locked = false;
  const host = location.hostname;
  const siteId = host.includes("copilot") ? "copilot" : host.includes("mistral") ? "mistral" : host.includes("claude") ? "claude" : host.includes("grok") ? "grok" : host.includes("perplexity") ? "perplexity" : host.includes("duck") ? "duck" : "huggingchat";
  const displayName = { copilot: "Microsoft Copilot", mistral: "Mistral Vibe", claude: "Claude", grok: "Grok", perplexity: "Perplexity", duck: "Duck.ai", huggingchat: "HuggingChat" }[siteId];
  const timings = { GEN_IDLE_MS: 1400, REASON_IDLE_MS: 8000, WARMUP_MS: 30000, REASON_NOREPLY_MS: 60000, STABLE_MS: 7000, RESPONSE_TIMEOUT_MS: 240000 };
  const TEXT = "textarea:not(#zs-set-text), [contenteditable=\"true\"]:not(#zs-set-text)";
  const SEND = "button[type=submit], button[aria-label*='Send' i], button[aria-label*='send' i], button[data-testid*='send' i], button[class*='send' i]";
  const STOP = "button[aria-label*='Stop' i], button[aria-label*='stop' i], button[data-testid*='stop' i]";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visible = (e) => e && !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
  const text = (e) => (e && (e.innerText || e.textContent || "")).trim();
  const editor = () => [...document.querySelectorAll(TEXT)].filter((e) => !e.closest("#zs-root") && visible(e)).pop() || null;
  const sendButton = () => [...document.querySelectorAll(SEND)].filter((e) => !e.closest("#zs-root") && visible(e)).pop() || null;
  const assistant = (e) => {
    const role = (e.getAttribute("data-message-author-role") || e.getAttribute("data-author") || e.getAttribute("aria-label") || "").toLowerCase();
    return /assistant|bot|copilot|ai|model|hugging/.test(role);
  };
  function allItems() {
    const sels = ["[data-message-author-role]", "[data-testid*='message' i]", "article", "[role='article']"];
    const out = [], seen = new Set();
    for (const e of document.querySelectorAll(sels.join(","))) {
      if (!visible(e) || e.closest("#zs-root") || !text(e) || seen.has(e)) continue;
      // Prefer the outer message element, not nested spans with the same marker.
      if ([...e.children].some((c) => c.matches && sels.some((s) => { try { return c.matches(s); } catch { return false; } }))) continue;
      seen.add(e); out.push(e);
    }
    return out;
  }
  const isAssistantItem = (e) => assistant(e);
  const isUserItem = (e) => !assistant(e);
  const assistantItems = () => allItems().filter(isAssistantItem);
  const lastAssistant = () => assistantItems().pop() || null;
  const itemText = (e) => text(e);
  const classifyText = (e, exclude) => {
    if (!e) return "";
    const copy = e.cloneNode(true);
    copy.querySelectorAll(".zs-chip, " + (exclude || "#zs-never")).forEach((n) => n.remove());
    return text(copy);
  };
  const getEditor = editor;
  const editorText = () => { const e = editor(); return e ? ("value" in e ? e.value : e.textContent || "") : ""; };
  const setEditor = (e, value) => {
    if (!e) return;
    if ("value" in e) {
      const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(e), "value")?.set;
      setter ? setter.call(e, value) : (e.value = value);
      e.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      e.focus(); document.execCommand("selectAll", false); document.execCommand("insertText", false, value);
      e.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }));
    }
  };
  const clickSend = () => { const b = sendButton(); if (b) { b.click(); return true; } return false; };
  async function typeAndSend(value) { const e = editor(); if (!e) throw new Error("composer not found"); setEditor(e, value); await sleep(120); if (!clickSend()) e.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", bubbles: true })); }
  function setInputLock(on) { locked = !!on; const e = editor(); if (!e) return; if (on) { e.dataset.xwPlaceholder = e.getAttribute("placeholder") || ""; e.setAttribute("readonly", ""); e.setAttribute("placeholder", "XW Studio is working…"); } else { e.removeAttribute("readonly"); if (e.dataset.xwPlaceholder != null) e.setAttribute("placeholder", e.dataset.xwPlaceholder); } }
  const isGenerating = () => !!document.querySelector(STOP);
  const isBusyNow = isGenerating;
  const isHardGenerating = isGenerating;
  const stopGeneration = () => { const b = [...document.querySelectorAll(STOP)].find(visible); if (b) b.click(); };
  const snapshot = () => ({ host, items: allItems().length, assistants: assistantItems().length, editor: !!editor() });
  const streamLen = (e) => itemText(e).length;
  const readAssistant = () => { const item = lastAssistant(); return item ? { present: true, reply: itemText(item), thinking: "", item } : { present: false, reply: "", thinking: "", item: null }; };
  const itemKey = (e) => e ? (e.getAttribute("data-message-id") || e.getAttribute("data-testid") || null) : null;
  const conversationKey = () => location.href;
  const chatIsEmpty = () => allItems().length === 0;
  const isFreshChat = () => chatIsEmpty() && !!editor();
  let cachedEditor = null;
  let cachedSurface = null;
  function composerSurface() {
    const e = editor();
    if (!e) return null;
    if (e === cachedEditor && cachedSurface?.isConnected) return cachedSurface;
    let node = e.parentElement;
    const fallback = node;
    let candidate = fallback;
    for (let depth = 0; node && node !== document.body && depth < 8; depth++, node = node.parentElement) {
      const rect = node.getBoundingClientRect();
      const hasSend = [...node.querySelectorAll(SEND)].some((b) => !b.closest("#zs-root") && visible(b));
      // Keep climbing through compact composer wrappers. The outermost compact
      // card is where the host puts its quick-access row and microphone button;
      // mounting there places XW Studio above the input, like a native banner.
      if (hasSend && rect.width >= 280 && rect.height <= 360) candidate = node;
    }
    cachedEditor = e;
    cachedSurface = candidate;
    return candidate;
  }
  const composerFrame = () => editor()?.parentElement || null;
  function barMount() {
    const surface = composerSurface();
    if (!surface) return null;
    let before = surface.firstElementChild;
    if (before?.id === "zs-bar") before = before.nextElementSibling;
    return { parent: surface, before, inside: true };
  }
  const barAnchor = () => composerSurface();
  const ensureComposerReady = () => ({ ready: !!editor() });
  const enforceComposer = () => { if (locked) setInputLock(true); return { ready: !!editor() }; };
  const installSendHooks = () => {};
  const findToolBlockSpot = (e) => e;
  const turnHalted = () => false;
  const scanError = () => null;
  const isTooLongMsg = (s) => /too long|context limit|лимит контекста/i.test(s || "");
  const isBusyMsg = (s) => /busy|try again|rate limit|занят/i.test(s || "");
  const captchaPresent = () => /captcha|verify you are human/i.test(document.body?.innerText || "");
  const overlayBlocking = () => false;
  const modeWarning = () => "";
  const conversation = () => location.href;
  const assistantCount = () => assistantItems().length;
  const userCount = () => allItems().filter(isUserItem).length;
  const lastAssistantId = () => itemKey(lastAssistant());
  return {
    id: siteId, displayName, supportsVision: false, timings,
    init({ diag: d } = {}) { if (d) diag = d; }, allItems, isUserItem, isAssistantItem, itemText, classifyText,
    assistantCount, userCount, lastAssistant, lastAssistantId, itemKey, readAssistant, streamLen, snapshot,
    getEditor, editorText, chatIsEmpty, isFreshChat, composerFrame, barMount, barAnchor, setInputLock,
    typeAndSend, stopGeneration, isGenerating, isBusyNow, isHardGenerating, enforceComposer, ensureComposerReady,
    turnHalted, findToolBlockSpot, scanError, isTooLongMsg, isBusyMsg, captchaPresent, overlayBlocking, modeWarning,
    conversationKey, installSendHooks, reliableCounts: true, chipAtItemLevel: true, chipAppend: true,
    promptExtra: siteId === "claude"
      ? "- Claude is operating as the XW Studio Roblox agent, not as a tutorial writer. Do not tell the user to paste code, build a model manually, or configure Studio themselves. For any Roblox request, act through the XW Studio command format: inspect first, then execute one exact command and wait for its result. If the user asks to create a model or feature, perform the work in the connected place; only ask a question when the request is genuinely ambiguous or a destructive scope needs confirmation. Never claim that direct Roblox access is impossible while XW Studio is active."
      : siteId === "grok"
        ? "- Use XW Studio commands for Roblox work, not Grok's native web/X search, connectors, or built-in agents. Never tell the user to paste code manually: inspect the connected place, send one fenced JSON XW command, wait for its result, then continue."
        : siteId === "perplexity"
          ? "- Do not turn a Roblox request into a web-search answer. Use the XW Studio command format to inspect and change the connected place; use Perplexity search only when the user explicitly asks for external documentation. One command per reply, then wait for its result."
          : siteId === "duck"
            ? "- Treat the selected Duck.ai model as the XW Studio Roblox agent. Do not explain how the user can build or paste code manually. Use one fenced JSON XW command at a time, inspect first, wait for the result, and perform changes in the connected place."
            : "- This site is connected through XW Studio's generic adapter. Prefer one short command per turn and wait for the result before continuing."
  };
})();
