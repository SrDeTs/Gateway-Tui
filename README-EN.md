<p align="center">
  <img src="https://img.shields.io/badge/version-6.2-blue" alt="v6.2">
  <img src="https://img.shields.io/badge/python-3.8%2B-green" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Linux">
  <img src="https://img.shields.io/badge/shell-fish%20%7C%20bash-orange" alt="Fish/Bash">
</p>

<h1 align="center">Gateway Config CLI</h1>
<p align="center">
  <em>Configure Claude Code or Codex CLI with compatible gateways in seconds.</em>
</p>

<p align="center">
  <a href="#-about">About</a> •
  <a href="#-features">Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-keybindings">Keybindings</a> •
  <a href="#-plain-mode">--plain mode</a> •
  <a href="#-generated-files">Generated files</a> •
  <a href="#-examples">Examples</a> •
  <a href="#-compatibility">Compatibility</a>
</p>

---

## 📋 About

**Gateway Config CLI** is an interactive terminal tool (TUI) that quickly configures **Claude Code** (Anthropic) or **Codex CLI** (OpenAI) to work with compatible gateways like **TokenRouter**, **OpenRouter**, or any API compatible with `/v1/messages` (Anthropic) or `/v1/chat/completions` (OpenAI).

It automatically generates **fish** launchers, JSON/TOML config files, `.env` files, and global variables — no manual editing required.

---

## ✨ Features

- **Interactive TUI** with keyboard and mouse navigation
- **Two modes**: Claude Code (Anthropic) and Codex CLI (OpenAI)
- **Presets** for TokenRouter, Google Gemini, and Custom
- **Isolated fish launcher** per profile (e.g. `claude-minimax`)
- **Global fish variables** (`set -Ux`) for direct `claude` usage
- **`~/.claude/settings.json`** or **`~/.codex/config.toml`** config
- **`.env` file** per profile
- **Endpoint testing** built-in before saving
- **Mouse text selection and copy**
- **Exit confirmation** when data has been entered (form and review)
- **`--plain` text mode** for terminals without curses support
- **Shortcuts**: Ctrl+V paste, Ctrl+W delete word, Ctrl+U clear field
- **[X] button** in the top-right corner to exit with mouse click

---

## 🚀 Installation

### Requirements

- Python 3.8+
- Fish shell (for fish launchers)
- Terminal with ANSI color and mouse support (optional)

### Download

```bash
# Clone or download the script
curl -LO https://raw.githubusercontent.com/your-user/gateway-tui/main/gateway-tui.py
chmod +x gateway-tui.py

# Or copy to your PATH manually
sudo cp gateway-tui.py /usr/local/bin/gateway-config
sudo chmod +x /usr/local/bin/gateway-config
```

### Dependencies

None — it uses only the Python standard library (`curses`, `json`, `re`, `subprocess`, etc.).

---

## 🎮 Usage

### Interactive mode (TUI)

```bash
python3 gateway-tui.py
```

The flow is divided into steps:

1. **Choose tool** → Claude Code or Codex CLI
2. **Fill fields** → profile, base URL, model, API key
3. **Configure options** → launcher, global, settings, discovery, permissions
4. **Review and save** → check summary, test endpoint, save
5. **Done** → view usage instructions

### Plain mode (--plain)

```bash
python3 gateway-tui.py --plain
```

Fallback mode for terminals without curses support, SSH without colors, or pipes.

---

## ⌨️ Keybindings

| Key | Action |
|-----|--------|
| `Enter` | Confirm / Next |
| `Esc` | Exit (confirmation if data exists — form, review) |
| `↑` `↓` | Navigate options |
| `1-9` | Select option by number |
| `Ctrl+V` | Paste from clipboard |
| `Ctrl+W` | Delete previous word |
| `Ctrl+U` | Clear entire field |
| `←` `→` | Move cursor in field |
| `Home` `End` | Start / End of field |
| `Mouse drag` | Select text to copy |
| `[X]` (top-right) | Exit app (click) |

### On review screen

| Key | Action |
|-----|--------|
| `Enter` | Save (with automatic test) |
| `t` | Test endpoint |
| `e` | Edit fields |
| `o` | Options |
| `c` | Copy summary |
| `Esc` | Exit (with confirmation) |

---

## 📄 Plain mode

Useful for automation or terminals without curses:

```bash
printf "1\nmy-gateway\nhttps://api.tokenrouter.com/v1\nMiniMax-M3\ny\nn\nn\nn\nn\nn\n" | python3 gateway-tui.py --plain
```

`--plain` mode asks for the API key via `getpass` (secure, not in shell history).

---

## 📁 Generated files

### Isolated fish launcher
`~/.config/fish/functions/claude-<profile>.fish`

Fish function that sets environment variables and runs `claude` — no global shell pollution.

### Global fish variables
`set -Ux` in fish

Sets variables globally to use `claude` or `codex` directly.

### Settings JSON (Claude Code)
`~/.claude/settings.json`

Configures `env.ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`.

### Config TOML (Codex CLI)
`~/.codex/config.toml`

Configures `openai.api_base_url`, `model`, `auth.api_key`.

### Env file
`~/.claude-code-gateway/<profile>.env`

`.env` file with all profile variables.

---

## 💡 Examples

### TokenRouter + MiniMax-M3

```bash
python3 gateway-tui.py
# Tool: Claude Code
# Profile: minimax
# Base URL: https://api.tokenrouter.com/v1
# Model: MiniMax-M3
# Launcher: yes
# Global: no
# Settings: no

# Afterwards:
claude-minimax
```

### Google Gemini via compatible gateway

```bash
python3 gateway-tui.py
# Tool: Claude Code
# Profile: gemini
# Base URL: https://generativelanguage.googleapis.com/v1beta
# Model: gemini-2.5-pro
# ...

claude-gemini
```

### Codex CLI + OpenAI gateway

```bash
python3 gateway-tui.py
# Tool: Codex CLI
# Profile: codex-gateway
# Base URL: https://api.example.com/v1
# Model: gpt-4o
# ...

codex-codex-gateway
```

---

## 🔧 Compatibility

| Component | Support |
|-----------|---------|
| **Systems** | Linux |
| **Shell** | Fish (launchers) |
| **Terminal** | Any curses-compatible terminal |
| **Mouse** | xterm, kitty, alacritty, foot, tmux, iTerm2 |
| **Clipboard** | OSC52 (tmux/kitty/alacritty), wl-copy (Wayland), xclip/xsel (X11) |
| **Gateway API** | Any Anthropic-compatible API (/v1/messages) or OpenAI-compatible (/v1/chat/completions) |

---

## 📝 License

MIT
