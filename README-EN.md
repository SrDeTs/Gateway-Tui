<p align="center">
  <img src="https://img.shields.io/badge/version-6.2-blue" alt="v6.2">
  <img src="https://img.shields.io/badge/python-3.8%2B-green" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Linux">
  <img src="https://img.shields.io/badge/shell-fish-orange" alt="Fish">
</p>

<h1 align="center">Gateway TUI</h1>
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

**Gateway TUI** is an interactive terminal tool that quickly configures **Claude Code** (Anthropic) or **Codex CLI** (OpenAI) to work with compatible gateways using `/v1/messages` (Anthropic) or `/v1/chat/completions` (OpenAI).

It automatically generates **fish** launchers, JSON/TOML config files, `.env` files, and global variables — no manual editing required.

---

## ✨ Features

- **Interactive TUI** with keyboard and mouse navigation
- **Two modes**: Claude Code (Anthropic) and Codex CLI (OpenAI)
- **Customizable preset** for any compatible gateway
- **Isolated fish launcher** per profile (e.g. `claude-my-gateway`)
- **Global fish variables** (`set -Ux`) for direct `claude` usage
- **`~/.claude/settings.json`** or **`~/.codex/config.toml`** config
- **`.env` file** per profile
- **Endpoint testing** built-in before saving (with "Testing..." feedback)
- **Mouse text selection and copy**
- **Exit confirmation** when data has been entered (form, options, and review)
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
| `Esc` | Exit (confirmation if data exists — form, options, review) |
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
printf "1\nmy-gateway\nhttps://api.openai.com/v1\ngpt-5.4\ny\nn\nn\nn\nn\nn\n" | python3 gateway-tui.py --plain
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

### Claude Code with gateway

```bash
python3 gateway-tui.py
# Tool: Claude Code
# Profile: my-gateway
# Base URL: https://api.anthropic.com/v1
# Model: claude-sonnet-4-20250514
# Launcher: yes
# ...

claude-my-gateway
```

### Codex CLI with gateway

```bash
python3 gateway-tui.py
# Tool: Codex CLI
# Profile: codex-gateway
# Base URL: https://api.openai.com/v1
# Model: gpt-5.4
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

