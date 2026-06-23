<p align="center">
  <img src="https://img.shields.io/badge/versão-6.2-blue" alt="v6.2">
  <img src="https://img.shields.io/badge/python-3.8%2B-green" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/plataforma-linux-lightgrey" alt="Linux">
  <img src="https://img.shields.io/badge/shell-fish-orange" alt="Fish">
</p>

<h1 align="center">Gateway TUI</h1>
<p align="center">
  <em>Configure Claude Code ou Codex CLI com gateways compatíveis em segundos.</em>
</p>

<p align="center">
  🌐 <a href="README-EN.md"><strong>English version available →</strong></a>
</p>

<p align="center">
  <a href="#-sobre">Sobre</a> •
  <a href="#-funcionalidades">Funcionalidades</a> •
  <a href="#-instalação">Instalação</a> •
  <a href="#-como-usar">Como usar</a> •
  <a href="#-teclas">Teclas</a> •
  <a href="#-modo-plain">Modo --plain</a> •
  <a href="#-arquivos-gerados">Arquivos gerados</a> •
  <a href="#-exemplos">Exemplos</a> •
  <a href="#-compatibilidade">Compatibilidade</a>
</p>

---

## 📋 Sobre

**Gateway TUI** é uma ferramenta de terminal interativa que configura rapidamente o **Claude Code** (Anthropic) ou **Codex CLI** (OpenAI) para usar gateways compatíveis com `/v1/messages` (Anthropic) ou `/v1/chat/completions` (OpenAI).

Ela gera automaticamente launchers **fish**, configurações JSON/TOML, arquivos `.env`, e variáveis globais — sem editar nada manualmente.

---

## ✨ Funcionalidades

- **TUI interativa** com navegação por teclado e mouse
- **Dois modos**: Claude Code (Anthropic) e Codex CLI (OpenAI)
- **Preset customizável** para qualquer gateway compatível
- **Launcher fish isolado** por profile (ex: `claude-minimax`)
- **Variáveis globais fish** (`set -Ux`) para usar `claude` direto
- **Config `~/.claude/settings.json`** ou **`~/.codex/config.toml`**
- **Arquivo `.env`** por profile
- **Teste de endpoint** integrado antes de salvar
- **Seleção e cópia** de texto com o mouse
- **Confirmação ao sair** com dados preenchidos (formulário e revisão)
- **Modo texto `--plain`** para terminais sem suporte a curses
- **Atalhos** Ctrl+V colar, Ctrl+W apagar palavra, Ctrl+U limpar campo
- **Botão [X]** no canto superior direito para sair com o mouse

---

## 🚀 Instalação

### Requisitos

- Python 3.8+
- Fish shell (para launchers fish)
- Terminal com suporte a cores ANSI e mouse (opcional)

### Download

```bash
# Clone ou baixe o script
curl -LO https://raw.githubusercontent.com/seu-usuario/gateway-tui/main/gateway-tui.py
chmod +x gateway-tui.py

# Ou copie manualmente para seu PATH
sudo cp gateway-tui.py /usr/local/bin/gateway-config
sudo chmod +x /usr/local/bin/gateway-config
```

### Dependências

Nenhuma — a ferramenta usa apenas a biblioteca padrão do Python (`curses`, `json`, `re`, `subprocess`, etc.).

---

## 🎮 Como usar

### Modo interativo (TUI)

```bash
python3 gateway-tui.py
```

O fluxo é dividido em etapas:

1. **Escolha a ferramenta** → Claude Code ou Codex CLI
2. **Preencha os campos** → profile, base URL, modelo, API key
3. **Configure opções** → launcher, global, settings, discovery, permissões
4. **Revise e salve** → confira o resumo, teste o endpoint, salve
5. **Pronto** → veja as instruções de uso

### Modo texto (--plain)

```bash
python3 gateway-tui.py --plain
```

Modo fallback para terminais sem suporte a curses, SSH sem cores, ou pipes.

---

## ⌨️ Teclas

| Tecla | Ação |
|-------|------|
| `Enter` | Confirmar / Avançar |
| `Esc` | Sair (com confirmação se houver dados — formulário, revisão) |
| `↑` `↓` | Navegar entre opções |
| `1-9` | Selecionar opção pelo número |
| `Ctrl+V` | Colar do clipboard |
| `Ctrl+W` | Apagar palavra anterior |
| `Ctrl+U` | Limpar o campo inteiro |
| `←` `→` | Mover cursor no campo |
| `Home` `End` | Início / Fim do campo |
| `Mouse drag` | Selecionar texto para copiar |
| `[X]` (canto topo) | Sair do app (clique) |

### Na tela de revisão

| Tecla | Ação |
|-------|------|
| `Enter` | Salvar (com teste automático) |
| `t` | Testar endpoint |
| `e` | Editar campos |
| `o` | Opções |
| `c` | Copiar resumo |
| `Esc` | Sair (com confirmação) |

---

## 📄 Modo --plain

Útil para automação ou terminais sem curses:

```bash
printf "1\nmeu-gateway\nhttps://api.tokenrouter.com/v1\nMiniMax-M3\ns\nn\nn\nn\nn\nn\n" | python3 gateway-tui.py --plain
```

O modo `--plain` solicita a API key via `getpass` (seguro, não fica no histórico).

---

## 📁 Arquivos gerados

### Launcher fish isolado
`~/.config/fish/functions/claude-<profile>.fish`

Função fish que define variáveis de ambiente e executa `claude` — sem poluir o shell global.

### Variáveis globais fish
`set -Ux` no fish

Define variáveis globalmente para usar `claude` ou `codex` diretamente.

### Settings JSON (Claude Code)
`~/.claude/settings.json`

Configura `env.ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`.

### Config TOML (Codex CLI)
`~/.codex/config.toml`

Configura `openai.api_base_url`, `model`, `auth.api_key`.

### Env file
`~/.claude-code-gateway/<profile>.env`

Arquivo `.env` com todas as variáveis do profile.

---

## 💡 Exemplos

### Gateway personalizado

```bash
python3 gateway-tui.py
# Ferramenta: Claude Code
# Profile: meu-gateway
# Base URL: https://api.seu-gateway.com/v1
# Modelo: modelo-exato
# Launcher: sim
# ...

claude-meu-gateway
```

### Codex CLI + gateway OpenAI

```bash
python3 gateway-tui.py
# Ferramenta: Codex CLI
# Profile: codex-gateway
# Base URL: https://api.exemplo.com/v1
# Modelo: gpt-4o
# ...

codex-codex-gateway
```

---

## 🔧 Compatibilidade

| Componente | Suporte |
|------------|---------|
| **Sistemas** | Linux |
| **Shell** | Fish (launchers) |
| **Terminal** | Qualquer terminal com curses |
| **Mouse** | xterm, kitty, alacritty, foot, tmux, iTerm2 |
| **Clipboard** | OSC52 (tmux/kitty/alacritty), wl-copy (Wayland), xclip/xsel (X11) |
| **Gateway API** | Qualquer API Anthropic-compatible (/v1/messages) ou OpenAI-compatible (/v1/chat/completions) |

