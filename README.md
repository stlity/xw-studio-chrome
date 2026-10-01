# XW Studio for Chrome - Free AI Agent for Roblox, Godot and Terminal


**XW Studio** is a free browser extension that turns supported AI chats into a Roblox Studio, Godot Engine or local Terminal agent.
Use the popup to switch between Roblox, Godot and Terminal modes. Godot mode can inspect a selected project, read and write GDScript/scenes/resources, validate the project headlessly and run bounded scene checks through the bridge. No API key is required.

## XW Studio 1.9 — direct StudioMCP fix

Click **Settings** in the extension popup to open a dedicated tab. Enable the team, choose a workflow and safety mode, then assign any supported AI to six roles: **Designer, Builder, Debugger, Security reviewer, QA tester, and Producer / architect**. The profile is stored locally and added to the active chat's system prompt. Plan preview and automatic Output-driven debugging are opt-in controls in the same page.

The current release provides role-aware orchestration instructions and safe planning in the active chat. Choose **По умолчанию** for the normal prompt, or select a role directly in the XW Studio bar before starting. Use **Save session** in the in-page menu to carry the visible conversation to another supported AI, then import it in a new chat. It does not silently open or control several AI tabs at once; each external site keeps its own login and consent boundary.

The Windows release includes a text-based Python launcher. It lets you select Roblox Studio, Godot Engine or Local Terminal, shows bridge output in the same console, and provides status, log, restart and mode commands. It requires no PyQt5 and hides the separate StudioMCP console window.

Supported AI providers include **DeepSeek** (recommended), **ChatGPT**, **Google Gemini**, **Kimi**, **GLM**, **Qwen**, **Arena**, **Meta AI**, **Microsoft Copilot**, **HuggingChat**, **Mistral**, **Claude**, **Grok**, **Perplexity** and **Duck.ai**. On ChatGPT, screenshots and image input are turned off on purpose: the free tier limits files and images on a separate quota from messages, so vision would only work part of the day. Gemini and Kimi can be unstable: Gemini tends to stop using the Roblox tools in long sessions, and Kimi sometimes uses its own native tools instead of the Roblox commands. On Arena, use **Direct** mode (XW Studio only supports Direct; it blocks Start in Battle / Side-by-Side / Agent modes). DeepSeek is the recommended provider.


> *Also known as: XW Studio Roblox, XW Studio free download, Roblox ChatGPT agent, Roblox DeepSeek agent, Roblox Gemini agent, Roblox Kimi agent, Roblox GLM agent, Roblox Qwen agent, Roblox Arena agent, Roblox Meta AI agent, Roblox Studio AI automation, Luau AI, MCP Roblox, lemonade alternative free, lemonade.gg alternative, free Roblox AI agent, free lemonade roblox alternative*

## ⚠️ XW Studio is Free Beware of Paid Copycats

XW Studio is 100% free and open-source. It always has been, and it always will be. There is no official paid version, no subscription, and no sign-in required to use the extension.

If you come across a site or extension using the XW Studio name that asks for payment or account creation, it is **not** this project. The only official links are the ones listed at the top of this README.

## How it works

```
AI chat (supported site, in your browser) -> XW Studio Extension -> Bridge (your PC) -> Roblox Studio, Godot or Terminal
```

The extension runs inside a supported chat page. In Roblox mode it sends commands to Roblox Studio through the built-in MCP server. In Godot mode it works with a selected folder containing `project.godot` and uses the installed Godot CLI for validation and bounded tests. In Terminal mode it exposes local file and shell tools through the Bridge.

## Setup

> 📺 **Lost? Watch the [setup tutorial on YouTube](https://youtu.be/kPKiZLZ9_Ps) it covers every step below.**

### 1. Download the zip and install the extension

Download the latest zip from the **Releases** page and extract it. The zip contains both the **Bridge** and the **extension folder**.

To load the extension:

- Go to `edge://extensions` (Edge) or `chrome://extensions` (Chrome)
- Enable **Developer mode** (top right toggle)
- Click **Load unpacked**
- Select the `extension` folder from the extracted zip

### 2. Configure Roblox Studio (Roblox mode only)

Open Studio and load a Place, then enable MCP (first time only):

- Click **Assistant AI** in the top bar
- Click **...** (top right of the Assistant panel)
- Click **Manage MCP Servers**
- Click **Enable Studio as MCP Server**

> Not sure where to find these options? The [video tutorial](https://youtu.be/kPKiZLZ9_Ps) shows exactly where to click.

### 3. Choose a target and run the Bridge

On Windows, run `launcher.py` and choose **Roblox Studio**, **Godot Engine** or **Local Terminal** in the text menu. The launcher keeps bridge output and commands in the same console.

- **Windows:** run `python launcher.py` inside the extracted folder. Do not use IDLE; use Command Prompt or Windows Terminal. No PyQt5 installation is required.
- **macOS:** double-click `MacOS_Start.command` inside the extracted folder. The first time, macOS will show a security warning ("could not verify... free of malware") - this is normal for any script downloaded outside the App Store, click **Done**, then go to **System Settings > Privacy & Security**, scroll to the bottom, and click **Open Anyway**. You only need to do this once.

The same console shows the bridge output. Keep it open or minimize it while using the extension.

For Godot mode, open the XW Studio popup, choose **Godot**, press **Обзор**, and select the folder containing `project.godot`. The bridge uses the installed `godot`, `godot4` or `Godot` executable; set `XW_GODOT_BIN` if it is not on PATH.

### 4. Start a session

Go to a supported site such as https://chat.deepseek.com (recommended), https://chatgpt.com, https://gemini.google.com, https://www.kimi.ai, https://chat.z.ai, https://chat.qwen.ai, https://arena.ai, https://www.meta.ai, https://claude.ai, https://grok.com, https://www.perplexity.ai or https://duck.ai and open a new chat. The XW Studio bar appears above the input box. Click **Start session**. Type what you want to build or change.

> It works only on the supported AI sites listed above; it will not inject into arbitrary websites.
> On Arena, keep the mode dropdown on **Direct** - XW Studio blocks Start in Battle / Side-by-Side / Agent modes (it only drives a single Direct reply).
> Gemini and Kimi can be unstable (model behavior, not the extension): Gemini may stop using the Roblox tools after a while, and Kimi may use its own native tools instead. Grok and Perplexity use the hardened generic adapter with broader composer/send selectors. If an AI starts answering in plain text instead of acting, remind it to use the commands or start a new session.
### 5. Watch the setup tutorial

[Watch the setup tutorial on YouTube](https://youtu.be/kPKiZLZ9_Ps)

## What the AI can do

- Read and edit scripts
- Run Luau code directly in Studio
- Inspect the game tree and instances
- Generate meshes, materials, and models
- Browse and insert from the Creator Store
- Control play-testing
- **Remember your project across sessions** persistent project memory saved inside your place

## Provider compatibility notes

- **DeepSeek: the agent starts again on the new unified model.** DeepSeek merged Instant, Expert and Vision into one model and removed the model picker, which left "Start Roblox agent" stuck on "DeepSeek mode not ready". XW Studio now recognises the new chat box, switches Search off and starts, with DeepThink left on.
- **DeepSeek: screenshots work on every chat.** Images no longer need the Vision tab (it is gone) - the unified model sees your Studio captures, one at a time or several in a row.


- **ChatGPT: the XW Studio bar is back above the composer.** ChatGPT redesigned its input box and renamed the layout slot the bar sits in. XW Studio kept asking for the old name, so the browser dropped the bar into a stray strip at the bottom right of the composer and squeezed the text field to nothing. The bar now takes the right row again, and it reads the layout live instead of trusting a fixed name, so the next redesign should not knock it out.
- **ChatGPT: long commands read cleanly on the new interface.** The same redesign replaced the code-block editor that used to hide line breaks and cut long lines off - the cause of the truncated commands fixed in 1.5.1. A 400-line block now reads back whole. If you are still on the old interface, the previous workaround is untouched.

### Kimi and DeepSeek compatibility notes

- **Kimi moved to kimi.ai.** The old address, kimi.com, now asks for a Chinese phone number to sign in, which locked most people out. Open https://www.kimi.ai instead - the page is unchanged, the bar appears above the input box exactly as before. Reopen any Kimi tab you had on the old address.
- **DeepSeek: the Instant model can now run the agent.** Picking Instant used to leave "Start Roblox agent" spinning forever with no explanation, because only Expert and Vision were accepted. Choose Instant before starting and the session runs on it - much faster than Expert, without the reasoning pass. Images stay off on Instant just like on Expert; the Vision tab remains the only one that can see screenshots.
- **DeepSeek: a reply written in DeepSeek's own tool-call format no longer kills the turn.** DeepSeek occasionally answers with its internal markup instead of a XW Studio command. Nothing recognised it, so the tool never ran, the raw tags stayed on screen and the agent stopped dead with you waiting. It is now caught, hidden behind a tool chip like any other command, and DeepSeek is told to rewrite the call properly.
- **ChatGPT: the bar no longer clips into the composer's rounded corners.**

See [CHANGELOG.md](CHANGELOG.md) for older releases.

## Panel status

| Dot | Meaning |
|-----|---------|
| Green | Bridge + Studio ready (a place is open) |
| Yellow | Bridge OK, but Studio isn't usable yet - open Roblox Studio, load a place, or enable its MCP server (hover the dot for the exact reason) |
| Grey | Bridge offline - run launcher.py (Windows) or MacOS_Start.command (macOS) |

## Requirements

- Windows or macOS
- Roblox Studio (MCP support built-in)
- Microsoft Edge or Chrome
- Python 3.9+ (installed automatically on Windows, or install it yourself on macOS - see [python.org/downloads](https://www.python.org/downloads/))

## Project

XW Studio is a free, open-source project. Use the issue tracker in the project repository for bugs, feature requests and implementation discussion.

---

Credit: the idea for connecting other MCP servers (Blender, Sketchfab, etc.) alongside Roblox Studio came from [javnpa](https://github.com/javnpa).

Credit: macOS/Linux support contributed by [archivealf](https://github.com/archivealf).
