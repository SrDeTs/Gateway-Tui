#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gateway TUI v6.3

Configura Claude Code ou Codex CLI com gateways compatíveis.
Gera launchers fish, settings.json/config.toml e .env.
"""
from __future__ import annotations

import base64
import curses
import getpass
import json
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

APP = "Gateway TUI"
VERSION = "6.3"

@dataclass
class Config:
    mode: str = "claude"  # "claude" ou "codex"
    profile: str = ""
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    discovery: bool = False
    save_launcher: bool = True
    set_global: bool = False
    write_settings: bool = False
    write_envfile: bool = False
    test_first: bool = True
    skip_permissions: bool = False


def norm_profile(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", s.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-_")
    return s or "gateway"


def strip_known_endpoint(url: str) -> str:
    url = url.strip().rstrip("/")
    return re.sub(r"/v\d[\w.-]*/(?:messages|chat/completions|responses)$", "", url)


def claude_base(url: str) -> str:
    url = strip_known_endpoint(url)
    url = re.sub(r"/v\d[\w.-]*$", "", url)
    return url


def codex_base(url: str) -> str:
    url = strip_known_endpoint(url)
    if re.search(r"/v\d[\w.-]*$", url):
        return url
    return url + "/v1"


def endpoint(url: str) -> str:
    return claude_base(url) + "/v1/messages"


def codex_endpoint(url: str) -> str:
    return codex_base(url) + "/responses"


def endpoint_for(cfg: Config) -> str:
    return codex_endpoint(cfg.base_url) if cfg.mode == "codex" else endpoint(cfg.base_url)


def codex_gateway_hint(body: str, ep: str) -> str:
    low = body.lower()
    if "invalid json body" in low or "bad_request" in low:
        return (
            " Dica: Codex exige gateway compativel com OpenAI Responses API "
            f"({ep}) e alguns gateways aceitam so /chat/completions."
        )
    return ""


def mask(s: str) -> str:
    if not s:
        return "<vazio>"
    if len(s) <= 12:
        return s[:3] + "*" * max(0, len(s) - 6) + s[-3:]
    return s[:6] + "*" * (len(s) - 10) + s[-4:]


def fish_escape(v: str) -> str:
    if shutil.which("fish"):
        try:
            p = subprocess.run(["fish", "-lc", "string escape -- $argv[1]", v], text=True, capture_output=True, timeout=2)
            if p.returncode == 0 and p.stdout.strip():
                return p.stdout.strip()
        except Exception:
            pass
    return shlex.quote(v)


def toml_string(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


def paste_text() -> tuple[bool, str]:
    for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
        if shutil.which(cmd[0]):
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                if p.returncode == 0 and p.stdout.strip():
                    return True, p.stdout.rstrip("\n")
            except Exception:
                pass
    return False, "Nada no clipboard (ou sem ferramenta de paste)."


def copy_text(text: str) -> tuple[bool, str]:
    text = text.strip("\n")
    if not text.strip():
        return False, "Nada para copiar."
    # OSC52 primeiro: instantâneo (escreve direto no stdout, sem subprocesso)
    # Suportado por: tmux, screen, kitty, alacritty, iterm2, foot, etc.
    try:
        data = base64.b64encode(text.encode()).decode()
        sys.__stdout__.write(f"\033]52;c;{data}\a")
        sys.__stdout__.flush()
        return True, "Copiado."
    except Exception:
        pass
    # Fallback: ferramentas externas (wl-copy, xclip, etc.) — mais lentas
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        if shutil.which(cmd[0]):
            try:
                p = subprocess.run(cmd, input=text, text=True, capture_output=True, timeout=2)
                if p.returncode == 0:
                    return True, "Copiado."
            except Exception:
                pass
    return False, "Falha no clipboard."


def test_gateway(cfg: Config, timeout: int = 15) -> tuple[bool, str]:
    if not cfg.api_key.strip():
        return False, "API key vazia."

    ep = endpoint_for(cfg)
    if cfg.mode == "codex":
        payload = {"model": cfg.model, "input": "ping", "max_output_tokens": 80, "store": False}
    else:
        payload = {"model": cfg.model, "max_tokens": 80, "messages": [{"role": "user", "content": "ping"}]}

    base_headers = {"Content-Type": "application/json"}
    if cfg.mode == "claude":
        base_headers["anthropic-version"] = "2023-06-01"
        auth_variants = (
            {"Authorization": f"Bearer {cfg.api_key}"},
            {"x-api-key": cfg.api_key},
        )
    else:
        auth_variants = ({"Authorization": f"Bearer {cfg.api_key}"},)

    last_error = ""
    for auth_headers in auth_variants:
        headers = {**base_headers, **auth_headers}
        req = urllib.request.Request(
            ep,
            data=json.dumps(payload).encode(),
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode(errors="replace")
                try:
                    obj = json.loads(body)
                    txt = response_text(obj)
                    return True, f"OK {r.status}. Modelo: {obj.get('model', cfg.model)}. {txt}"
                except Exception:
                    return True, f"OK {r.status}. {body[:220]}"
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:700]
            hint = codex_gateway_hint(body, ep) if cfg.mode == "codex" else ""
            last_error = f"HTTP {e.code}: {body}{hint}"
            if cfg.mode != "claude" or e.code not in (401, 403):
                return False, last_error
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
    return False, last_error or "Falha no teste."


def response_text(obj: dict) -> str:
    if isinstance(obj.get("content"), list) and obj["content"]:
        return str(obj["content"][0].get("text", ""))[:160]
    choices = obj.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {})
        if isinstance(msg, dict):
            return str(msg.get("content", ""))[:160]
    output = obj.get("output")
    if isinstance(output, list):
        chunks = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    chunks.append(str(part.get("text", "")))
        return " ".join(chunks)[:160]
    return ""


def fish_assignments(vals: dict[str, str], unset: tuple[str, ...] = ()) -> str:
    chunks = [f"set -e {k}; set -Ue {k}" for k in unset]
    for k, v in vals.items():
        if not v:
            continue
        chunks.append(f"set -e {k}; set -Ue {k}; set -Ux {k} {fish_escape(v)}")
    return "; ".join(chunks)


def save_fish_global(cfg: Config) -> None:
    fish = shutil.which("fish")
    if not fish:
        raise RuntimeError("fish não encontrado")

    if cfg.mode == "codex":
        vals = {
            "OPENAI_API_KEY": cfg.api_key,
        }
        unset = ()
    else:
        vals = {
            "ANTHROPIC_BASE_URL": claude_base(cfg.base_url),
            "ANTHROPIC_AUTH_TOKEN": cfg.api_key,
            "ANTHROPIC_MODEL": cfg.model,
        }
        if cfg.discovery:
            vals["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"
        if cfg.skip_permissions:
            vals["CLAUDE_CODE_DANGEROUSLY_SKIP_PERMISSIONS"] = "1"
        unset = tuple(k for k in (
            "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY",
            "CLAUDE_CODE_DANGEROUSLY_SKIP_PERMISSIONS",
        ) if k not in vals)

    script = fish_assignments(vals, unset)
    if not script:
        return
    p = subprocess.run([fish, "-lc", script], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout or "erro no fish")


def write_launcher(cfg: Config) -> Path:
    d = Path.home() / ".config" / "fish" / "functions"
    d.mkdir(parents=True, exist_ok=True)
    name = norm_profile(cfg.profile)

    if cfg.mode == "codex":
        path = d / f"codex-{name}.fish"
        env_lines = []
        if cfg.api_key:
            env_lines.append(f"    set -lx OPENAI_API_KEY {fish_escape(cfg.api_key)}")
        openai_base_arg = "openai_base_url=" + toml_string(codex_base(cfg.base_url))
        no_store_arg = "disable_response_storage=true"
        lines = [
            f"function codex-{name}",
            *env_lines,
            f"    codex --model {fish_escape(cfg.model)} --disable responses_websockets -c {fish_escape(openai_base_arg)} -c {fish_escape(no_store_arg)} $argv",
            "end",
            "",
        ]
    else:
        prefix = "claude"
        path = d / f"claude-{name}.fish"
        lines = [
            f"function claude-{name}",
            f"    set -lx ANTHROPIC_BASE_URL {fish_escape(claude_base(cfg.base_url))}",
            f"    set -lx ANTHROPIC_MODEL {fish_escape(cfg.model)}",
        ]
        if cfg.api_key:
            lines.append(f"    set -lx ANTHROPIC_AUTH_TOKEN {fish_escape(cfg.api_key)}")
        if cfg.discovery:
            lines.append("    set -lx CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY 1")
        if cfg.skip_permissions:
            lines.append(f"    {prefix} --dangerously-skip-permissions $argv")
        else:
            lines.append(f"    {prefix} $argv")
        lines += ["end", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o600)
    return path


def update_codex_config(existing: str, cfg: Config) -> str:
    managed = {
        "model": cfg.model,
        "openai_base_url": codex_base(cfg.base_url),
    }
    lines = existing.splitlines()
    out = []
    in_top_level = True
    drop_table = False

    for line in lines:
        stripped = line.strip()
        table = re.fullmatch(r"\[([A-Za-z0-9_.-]+)\]", stripped)
        if table:
            name = table.group(1)
            drop_table = name in {"openai", "auth"}
            in_top_level = False
            if drop_table:
                continue
        if drop_table:
            continue
        if stripped == "# Gateway TUI managed settings":
            continue
        if in_top_level and any(re.match(rf"{re.escape(k)}\s*=", stripped) for k in managed):
            continue
        out.append(line)

    prefix = ["# Gateway TUI managed settings"]
    prefix.extend(f"{k} = {toml_string(v)}" for k, v in managed.items())
    prefix.append("")
    while out and not out[0].strip():
        out.pop(0)
    return "\n".join(prefix + out).rstrip() + "\n"


def write_settings(cfg: Config) -> Path:
    if cfg.mode == "codex":
        d = Path.home() / ".codex"
        d.mkdir(parents=True, exist_ok=True)
        path = d / "config.toml"
        existing = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="replace")
        content = update_codex_config(existing, cfg)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o600)
        return path

    # Modo Claude: ~/.claude/settings.json
    d = Path.home() / ".claude"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "settings.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("settings.json precisa ser um objeto JSON")
        except Exception:
            path.with_suffix(".json.bak").write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
            data = {}
    env = data.setdefault("env", {})
    env["ANTHROPIC_BASE_URL"] = claude_base(cfg.base_url)
    env["ANTHROPIC_AUTH_TOKEN"] = cfg.api_key
    env["ANTHROPIC_MODEL"] = cfg.model
    if cfg.discovery:
        env["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"] = "1"
    else:
        env.pop("CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY", None)
    if cfg.skip_permissions:
        env["CLAUDE_CODE_DANGEROUSLY_SKIP_PERMISSIONS"] = "1"
    else:
        env.pop("CLAUDE_CODE_DANGEROUSLY_SKIP_PERMISSIONS", None)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    path.chmod(0o600)
    return path


def write_envfile(cfg: Config) -> Path:
    d = Path.home() / ".claude-code-gateway"
    d.mkdir(parents=True, exist_ok=True)
    name = norm_profile(cfg.profile)
    path = d / f"{name}.env"

    if cfg.mode == "codex":
        lines = [
            f"OPENAI_API_KEY={shlex.quote(cfg.api_key)}",
            f"OPENAI_BASE_URL={shlex.quote(codex_base(cfg.base_url))}",
            f"OPENAI_MODEL={shlex.quote(cfg.model)}",
            "",
        ]
    else:
        lines = [
            f"ANTHROPIC_BASE_URL={shlex.quote(claude_base(cfg.base_url))}",
            f"ANTHROPIC_AUTH_TOKEN={shlex.quote(cfg.api_key)}",
            f"ANTHROPIC_MODEL={shlex.quote(cfg.model)}",
            f"CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY={'1' if cfg.discovery else ''}",
            f"CLAUDE_CODE_DANGEROUSLY_SKIP_PERMISSIONS={'1' if cfg.skip_permissions else ''}",
            "",
        ]

    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o600)
    return path


class TUI:
    def __init__(self, s):
        self.s = s
        self.cfg = Config()
        self.msg = ""
        self.err = ""
        self.lines: dict[int, str] = {}
        self.mouse_start: Optional[tuple[int, int]] = None
        self.selecting = False
        self.select_anchor: Optional[tuple[int, int]] = None
        self.select_pos: Optional[tuple[int, int]] = None
        self.h = 0  # cached terminal height
        self.w = 0  # cached terminal width
        self._needs_full_redraw = False  # força redesenho completo após mouse copy
        self._confirming = False  # evita recursão no confirm_exit()
        self._hover_x = False  # mouse hover sobre [X]

    def has_data(self) -> bool:
        """Verifica se já há dados salvos no config."""
        return bool(self.cfg.profile or self.cfg.base_url or self.cfg.model or self.cfg.api_key)

    def confirm_exit(self) -> bool:
        """Pergunta se realmente deseja sair. Retorna True se deve sair, False se deve continuar.
        Usa flag _confirming para evitar recursão quando chamado de dentro do choose()."""
        if self._confirming:
            return True  # já está num diálogo de confirmação, sai direto
        self._confirming = True
        try:
            return self.choose("Confirmação", [
                ("sim", "Sim, sair", "Perde os dados preenchidos"),
                ("nao", "Não, continuar", "Volta ao preenchimento"),
            ], 1) == "sim"
        finally:
            self._confirming = False

    def color(self, n):
        try:
            return curses.color_pair(n)
        except Exception:
            return 0

    def add(self, y, x, text, attr=0, copyable=True):
        w = self.w
        if y < 0 or y >= self.h or x >= w:
            return
        txt = str(text)[: max(0, w - x - 1)]

        if copyable:
            old = self.lines.get(y, "")
            self.lines[y] = (old + " " * max(0, x - len(old)) + txt) if len(old) <= x else old[:x] + txt

        if self.selecting and self.select_anchor and self.select_pos and copyable:
            try:
                ax, ay = self.select_anchor
                bx, by = self.select_pos
                y1, y2 = sorted((ay, by))
                if y1 <= y <= y2:
                    if ay == by:
                        a, b = sorted((ax, bx))
                    elif y == ay:
                        a, b = ax, w
                    elif y == by:
                        a, b = 0, bx
                    else:
                        a, b = 0, w
                    seg_start = max(0, a - x)
                    seg_end = min(len(txt), b - x + 1)
                    if seg_start < seg_end:
                        self.s.addstr(y, x, txt[:seg_start], attr)
                        self.s.addstr(y, x + seg_start, txt[seg_start:seg_end], attr | curses.A_REVERSE)
                        self.s.addstr(y, x + seg_end, txt[seg_end:], attr)
                    else:
                        self.s.addstr(y, x, txt, attr)
                else:
                    self.s.addstr(y, x, txt, attr)
            except curses.error:
                pass
        else:
            try:
                self.s.addstr(y, x, txt, attr)
            except curses.error:
                pass

    def frame(self, title):
        self.s.erase(); self.lines.clear()
        self.h, self.w = self.s.getmaxyx()
        h, w = self.h, self.w
        self.add(0, 2, f" {APP} v{VERSION} ", curses.A_REVERSE | curses.A_BOLD)
        x_attr = curses.A_BOLD | (self.color(5) if self._hover_x else self.color(4))
        self.add(0, w - 5, " [X]", x_attr)
        self.add(3, 2, title, curses.A_BOLD | self.color(1))
        if self.msg: self.add(h-4, 2, self.msg[:w-4], self.color(2) | curses.A_BOLD)
        if self.err: self.add(h-3, 2, self.err[:w-4], self.color(4) | curses.A_BOLD)
        self.add(h-2, 2, "Ctrl+V cola · Ctrl+W apaga palavra · Ctrl+U limpa · Esc volta/sai", curses.A_DIM, False)

    def summary(self, y=5):
        is_codex = self.cfg.mode == "codex"
        mode_name = "Codex CLI" if is_codex else "Claude Code"
        ep = codex_endpoint(self.cfg.base_url) if is_codex else endpoint(self.cfg.base_url)
        rows = [
            ("Ferramenta", mode_name),
            ("Profile", self.cfg.profile),
            ("Base input", self.cfg.base_url),
            ("Endpoint", ep),
            ("Model", self.cfg.model),
            ("API key", mask(self.cfg.api_key)),
        ]
        if not is_codex:
            rows += [
                ("Discovery", "sim" if self.cfg.discovery else "não"),
            ]
        rows += [
            ("Global fish", "sim" if self.cfg.set_global else "não"),
            ("Fish launcher", "sim" if self.cfg.save_launcher else "não"),
        ]
        if is_codex:
            rows.append(("Config TOML", "sim" if self.cfg.write_settings else "não"))
        else:
            rows.append(("Settings JSON", "sim" if self.cfg.write_settings else "não"))
        rows.append(("Env file", "sim" if self.cfg.write_envfile else "não"))
        self.add(y, 2, "Resumo", curses.A_BOLD)
        for i, (k, v) in enumerate(rows, 1):
            self.add(y+i, 4, f"{k:<14} {v}")

    def mouse(self):
        try:
            _, x, y, _, state = curses.getmouse()
        except Exception:
            return

        # Hover tracking para [X] (antes de qualquer outra lógica)
        is_hover_x = (y == 0 and self.w - 5 <= x <= self.w - 2)
        if is_hover_x != self._hover_x:
            self._hover_x = is_hover_x
            attr = curses.A_BOLD | (self.color(5) if is_hover_x else self.color(4))
            try:
                self.add(0, self.w - 5, " [X]", attr)
                self.s.refresh()
            except curses.error:
                pass

        if state & curses.BUTTON1_PRESSED:
            # Botao [X] no canto superior direito
            if is_hover_x:
                raise SystemExit(0)
            self.mouse_start = (x, y)
            self.selecting = True
            self.select_anchor = (x, y)
            self.select_pos = (x, y)
            self.msg = "Selecionando..."
            self.err = ""
            return

        # Se o terminal enviar eventos de movimento, atualiza o highlight em tempo real.
        # Em alguns terminais/curses, movimento chega com state=0.
        if self.selecting and not (state & (curses.BUTTON1_RELEASED | curses.BUTTON1_CLICKED)):
            self.select_pos = (x, y)
            self.msg = "Selecionando..."
            return

        if state & (curses.BUTTON1_RELEASED | curses.BUTTON1_CLICKED):
            sx, sy = self.mouse_start or (x, y)
            self.selecting = False
            self.select_anchor = None
            self.select_pos = None

            if sy > y:
                sy, y = y, sy
                sx, x = x, sx

            out = []
            for yy in range(sy, y+1):
                line = self.lines.get(yy, "")
                if not line:
                    continue
                if sy == y:
                    a, b = sorted((sx, x))
                    part = line[a:b+1].strip()
                elif yy == sy:
                    part = line[sx:].strip()
                elif yy == y:
                    part = line[:x+1].strip()
                else:
                    part = line.strip()
                if part:
                    out.append(part)

            if not out and y in self.lines:
                out = [self.lines[y].strip()]

            if out:
                copied = "\n".join(out)
                # Feedback imediato ANTES da cópia lenta (wl-copy, xclip...)
                self.msg = f"Copiando {len(copied)} caracteres..."
                self.err = ""
                self.mouse_start = None
                self.s.refresh()
                ok, m = copy_text(copied)
                self.msg = f"{m} {len(copied)} caracteres."
                self.err = "" if ok else m
                self._needs_full_redraw = True
                self.s.refresh()
            else:
                self.msg = "Seleção vazia."
                self.mouse_start = None

    def key(self):
        try:
            k = self.s.get_wch()
            if k == curses.KEY_MOUSE:
                self.mouse(); return None
            if k == "\x1b":
                self.s.timeout(10)  # 10ms para detectar sequências de escape
                try:
                    nxt = self.s.get_wch()
                    if nxt == -1 or nxt == "\x1b":
                        # timeout (-1) = lone Esc | double Esc = lone Esc
                        return "\x1b"
                    if nxt == "[":
                        seq = "["
                        while True:
                            try:
                                c = self.s.get_wch()
                            except curses.error:
                                break
                            if isinstance(c, int):
                                return c
                            seq += c
                            if c in "ABCDHF~" or len(seq) > 8:
                                break
                        if seq == "[A":
                            return curses.KEY_UP
                        if seq == "[B":
                            return curses.KEY_DOWN
                        if seq == "[C":
                            return curses.KEY_RIGHT
                        if seq == "[D":
                            return curses.KEY_LEFT
                        if seq == "[H":
                            return curses.KEY_HOME
                        if seq == "[F":
                            return curses.KEY_END
                        if seq in ("[3;5~", "[3;2~", "[3;3~"):
                            return "\x17"
                        return None
                    return None  # unknown sequence, discard
                except curses.error:
                    return "\x1b"  # fallback: standalone escape
                finally:
                    self.s.timeout(-1)
            return k
        except KeyboardInterrupt:
            self.err = "Ctrl+C recebido. Use Esc para sair."
            return None
        except curses.error:
            return None

    def choose(self, title, options, default=0):
        idx = default
        redraw = True
        while True:
            if redraw:
                self.frame(title)
                y = 5
                for i, (key, name, desc) in enumerate(options):
                    attr = curses.A_REVERSE if i == idx else 0
                    self.add(y+i*3, 4, f"{i+1}. {name}", attr | curses.A_BOLD)
                    self.add(y+i*3+1, 7, desc, curses.A_DIM)
                self.s.refresh()
                redraw = False

            k = self.key()
            if k is None: continue
            if k in ("\n", "\r"): return options[idx][0]
            if k == "\x1b":
                if self.has_data() and not self.confirm_exit():
                    continue
                raise SystemExit(0)
            if k == curses.KEY_UP:
                idx = (idx-1) % len(options)
                redraw = True
            elif k == curses.KEY_DOWN:
                idx = (idx+1) % len(options)
                redraw = True
            elif isinstance(k, str) and k.isdigit() and 1 <= int(k) <= len(options):
                return options[int(k)-1][0]
            elif isinstance(k, str):
                for key, _, _ in options:
                    if k.lower() == key.lower(): return key

    def prompt(self, title, label, default="", secret=False, required=False):
        val = default; cur = len(val)
        curses.curs_set(1)

        # Full draw only on first iteration
        self.frame(title); self.summary(5)
        h, w = self.h, self.w
        y = max(18, h - 9)
        self.add(y, 2, label, curses.A_BOLD)
        prev_msg = self.msg
        prev_err = self.err

        while True:
            shown = "*" * len(val) if secret else val

            # Se estiver selecionando com mouse, redesenha TUDO para mostrar highlight
            # Redesenho completo: após mouse copy (limpa highlight) ou durante seleção
            if self._needs_full_redraw or self.selecting:
                if self._needs_full_redraw:
                    self._needs_full_redraw = False
                self.frame(title); self.summary(5)
                self.add(y, 2, label, curses.A_BOLD)
                self.add(y+1, 2, ("> " + shown[:w-6]).ljust(w - 2))
            else:
                # Update just the input line (not full screen)
                self.add(y+1, 2, ("> " + shown[:w-6]).ljust(w - 2))

                # Update msg/err lines only when changed
                if self.msg != prev_msg:
                    prev_msg = self.msg
                    txt = (self.msg[:w-4] if self.msg else "")[:w-4]
                    self.add(h-4, 2, txt.ljust(w-4), self.color(2) | curses.A_BOLD if self.msg else 0)
                if self.err != prev_err:
                    prev_err = self.err
                    txt = (self.err[:w-4] if self.err else "")[:w-4]
                    self.add(h-3, 2, txt.ljust(w-4), self.color(4) | curses.A_BOLD if self.err else 0)

            try: self.s.move(y+1, min(w-2, 4+cur))
            except curses.error: pass
            self.s.refresh()
            k = self.key()

            if k is None: continue
            if k in ("\n", "\r"):
                if val.strip() or not required:
                    curses.curs_set(0); return val
                self.err = "Campo obrigatório."; continue
            if k == "\x1b":
                if (val or self.has_data()) and not self.confirm_exit():
                    self._needs_full_redraw = True
                    continue
                curses.curs_set(0); return None
            if isinstance(k, int):
                if k in (curses.KEY_BACKSPACE, 8, 127):
                    if cur: val = val[:cur-1] + val[cur:]; cur -= 1
                elif k == curses.KEY_DC:
                    if cur < len(val): val = val[:cur] + val[cur+1:]
                elif k == curses.KEY_LEFT: cur = max(0, cur-1)
                elif k == curses.KEY_RIGHT: cur = min(len(val), cur+1)
                elif k == curses.KEY_HOME: cur = 0
                elif k == curses.KEY_END: cur = len(val)
                continue
            if k in ("\b", "\x7f"):
                if cur: val = val[:cur-1] + val[cur:]; cur -= 1
                continue
            if k == "\x1f":
                left = val[:cur].rstrip(); new_left = re.sub(r"\S+$", "", left)
                val = new_left + val[cur:]; cur = len(new_left); continue
            if k == "\x16":
                ok, clip = paste_text()
                if ok:
                    val = val[:cur] + clip + val[cur:]
                    cur += len(clip)
                    self.msg = f"Colado do clipboard: {len(clip)} caracteres."
                    self.err = ""
                else:
                    self.err = clip
                continue
            if k == "\x17":
                left = val[:cur].rstrip(); new_left = re.sub(r"\S+$", "", left)
                val = new_left + val[cur:]; cur = len(new_left); continue
            if k == "\x15": val = ""; cur = 0; continue
            if isinstance(k, str) and len(k) == 1 and (ord(k) < 32 or ord(k) == 127): continue
            if isinstance(k, str) and k.isprintable(): val = val[:cur] + k + val[cur:]; cur += len(k)

    def yesno(self, title, question, default=False):
        return self.choose(title, [("s", "Sim", question), ("n", "Não", "Manter atual")], 0 if default else 1) == "s"

    def run(self):
        curses.curs_set(0); self.s.keypad(True)
        try:
            curses.start_color(); curses.use_default_colors()
            for n, c in [(1,curses.COLOR_CYAN),(2,curses.COLOR_GREEN),(3,curses.COLOR_YELLOW),(4,curses.COLOR_RED),(5,curses.COLOR_MAGENTA)]: curses.init_pair(n, c, -1)
        except Exception: pass
        try:
            curses.mousemask(curses.ALL_MOUSE_EVENTS | getattr(curses, "REPORT_MOUSE_POSITION", 0))
            print("\033[?1003h\033[?1006h", end="", flush=True)
        except Exception: pass
        try:
            h, w = self.s.getmaxyx()
            if h < 24 or w < 50:
                self.frame("Terminal pequeno demais")
                self.add(5, 2, f"Dimensões atuais: {h}x{w}", curses.A_BOLD | self.color(4))
                self.add(6, 2, "Mínimo recomendado: 24x50", curses.A_BOLD)
                self.add(8, 2, "Pressione qualquer tecla para sair.", curses.A_DIM)
                self.s.refresh(); self.key()
                return
            self.choose_mode()
            if self.form() is None: raise SystemExit(0)
            self.options(); self.review(); self.save(); self.final()
        finally:
            try: print("\033[?1003l\033[?1006l", end="", flush=True)
            except Exception: pass

    def choose_mode(self):
        key = self.choose("Qual ferramenta?", [
            ("claude", "Claude Code (Anthropic)", "Usa ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN, ANTHROPIC_MODEL"),
            ("codex", "Codex CLI (OpenAI)", "Usa --model, -c openai_base_url e API Responses"),
        ], 0)
        self.cfg.mode = key
        self.msg = f"Modo: {'Claude Code' if key == 'claude' else 'Codex CLI'}"

    def form(self):
        is_codex = self.cfg.mode == "codex"
        prefix = "codex" if is_codex else "claude"

        profile_ex = f"ex: meu-{prefix}"
        v = self.prompt("Campos", f"Nome do profile/launcher ({profile_ex}):", self.cfg.profile, required=True)
        if v is None: return None
        self.cfg.profile = norm_profile(v)
        base_hint = "https://api.anthropic.com/v1" if not is_codex else "https://api.openai.com/v1"
        model_hint = "claude-sonnet-4-20250514" if not is_codex else "gpt-5.5"
        v = self.prompt("Campos", f"Base URL com /v1 (ex: {base_hint}):", self.cfg.base_url, required=True)
        if v is None: return None
        self.cfg.base_url = v.strip()
        v = self.prompt("Campos", f"Nome EXATO do modelo (ex: {model_hint}):", self.cfg.model, required=True)
        if v is None: return None
        self.cfg.model = v.strip()
        v = self.prompt("Campos", "API key:", "", secret=True)
        if v is not None and v.strip(): self.cfg.api_key = v.strip()
        return self.cfg

    def options(self):
        is_codex = self.cfg.mode == "codex"
        prefix = "codex" if is_codex else "claude"

        self.cfg.save_launcher = self.yesno("Opções", f"Criar launcher fish isolado? Ex: {prefix}-meu-profile", True)
        self.cfg.set_global = self.yesno("Opções", "Definir como global no fish com set -Ux?", False)

        if is_codex:
            self.cfg.write_settings = self.yesno("Opções", "Gravar ~/.codex/config.toml?", False)
            self.cfg.discovery = False
            self.cfg.skip_permissions = False
        else:
            self.cfg.write_settings = self.yesno("Opções", "Gravar também em ~/.claude/settings.json?", False)
            self.cfg.discovery = self.yesno("Opções", "Ativar discovery de modelos do gateway?", False)
            self.cfg.skip_permissions = self.yesno("Opções", "Adicionar --dangerously-skip-permissions?", False)

        self.cfg.write_envfile = self.yesno("Opções", "Gerar arquivo .env do profile?", False)
        self.cfg.test_first = self.yesno("Opções", "Testar endpoint antes de salvar?", True)

    def review(self):
        while True:
            self.frame("Revisão"); self.summary(5)
            y = 20
            for i, line in enumerate(["Enter salvar", "t testar agora", "e editar campos", "o opções", "c copiar resumo", "Esc sair"]): self.add(y+i, 4, line)
            self.s.refresh(); k = self.key()
            if k is None: continue
            if k in ("\n", "\r"):
                if self.cfg.test_first:
                    self.msg = "Testando endpoint..."
                    self.err = ""
                    self.s.refresh()
                    ok, m = test_gateway(self.cfg)
                    if not ok: self.err = "Teste falhou: " + m; continue
                    self.msg = m
                return
            if k == "\x1b":
                if not self.confirm_exit():
                    continue
                raise SystemExit(0)
            if isinstance(k, str) and k.lower() == "t":
                self.msg = "Testando endpoint..."
                self.err = ""
                self.s.refresh()
                ok, m = test_gateway(self.cfg)
                self.msg = m if ok else ""
                self.err = "" if ok else "Teste falhou: " + m
            elif isinstance(k, str) and k.lower() == "e": self.form()
            elif isinstance(k, str) and k.lower() == "o": self.options()
            elif isinstance(k, str) and k.lower() == "c":
                text = f"Profile: {self.cfg.profile}\nBase: {claude_base(self.cfg.base_url)}\nEndpoint: {endpoint_for(self.cfg)}\nModel: {self.cfg.model}"
                ok, m = copy_text(text); self.msg = m; self.err = "" if ok else m

    def save(self):
        while True:
            saved = []
            errors = []
            has_fish = bool(shutil.which("fish"))

            if self.cfg.save_launcher:
                if has_fish:
                    try:
                        saved.append(str(write_launcher(self.cfg)))
                    except Exception as e:
                        errors.append(f"launcher: {e}")
                else:
                    errors.append("launcher: fish não encontrado")
            if self.cfg.set_global:
                try:
                    save_fish_global(self.cfg); saved.append("fish universal vars")
                except Exception as e:
                    errors.append(f"global: {e}")
            if self.cfg.write_settings:
                try:
                    saved.append(str(write_settings(self.cfg)))
                except Exception as e:
                    errors.append(f"settings: {e}")
            if self.cfg.write_envfile:
                try:
                    saved.append(str(write_envfile(self.cfg)))
                except Exception as e:
                    errors.append(f".env: {e}")

            if errors:
                self.err = "Erro: " + "; ".join(errors)
            if saved:
                self.msg = "Salvo: " + ", ".join(saved)
                break
            elif not errors:
                self.err = "Nada salvo. Volte e selecione uma opção."
            self.options()

    def final(self):
        is_codex = self.cfg.mode == "codex"
        prefix = "codex" if is_codex else "claude"

        self.frame("Finalizado"); self.summary(5)
        y = 20
        self.add(y, 2, "Pronto.", curses.A_BOLD | self.color(2))
        if self.cfg.save_launcher:
            self.add(y+2, 2, "Abra terminal novo e rode:")
            label = f"{prefix}-{norm_profile(self.cfg.profile)}"
            if not is_codex and self.cfg.skip_permissions:
                label += "  (com --dangerously-skip-permissions)"
            self.add(y+3, 4, label, curses.A_BOLD | self.color(1))
        if self.cfg.set_global or self.cfg.write_settings:
            if is_codex:
                self.add(y+5, 2, "Ou rode: codex")
            else:
                self.add(y+5, 2, "Ou rode: claude")
        if is_codex:
            self.add(y+7, 2, "Codex usa config openai_base_url e API Responses")
        else:
            self.add(y+7, 2, "Dentro do Claude Code: /status e /model")
        self.add(y+9, 2, "Pressione qualquer tecla para sair.", curses.A_DIM)
        self.s.refresh(); self.key()


def plain():
    cfg = Config()
    print(f"{APP} v{VERSION}\n")

    raw = input("Configurar para [1] Claude Code ou [2] Codex CLI? [1]: ").strip()
    cfg.mode = "codex" if raw == "2" else "claude"
    print(f"  Modo: {'Codex CLI' if cfg.mode == 'codex' else 'Claude Code'}")

    is_codex = cfg.mode == "codex"
    prefix = "codex" if is_codex else "claude"

    cfg.profile = norm_profile(input(f"Profile (ex: meu-{prefix}): ").strip() or f"meu-{prefix}")
    cfg.base_url = input("Base URL (com /v1): ").strip()
    model_hint = "claude-sonnet-4-20250514" if not is_codex else "gpt-5.5"
    cfg.model = input(f"Modelo (ex: {model_hint}): ").strip()
    cfg.api_key = getpass.getpass("API key: ").strip()

    missing = []
    if not cfg.base_url:
        missing.append("Base URL")
    if not cfg.model:
        missing.append("Modelo")
    if missing:
        print("Campos obrigatórios vazios: " + ", ".join(missing), file=sys.stderr)
        sys.exit(2)

    cfg.save_launcher = input("Criar launcher fish? [S/n]: ").strip().lower() not in ("n","nao","não","no")
    cfg.set_global = input("Definir global fish set -Ux? [s/N]: ").strip().lower() in ("s","sim","y","yes")

    if is_codex:
        cfg.write_settings = input("Gravar ~/.codex/config.toml? [s/N]: ").strip().lower() in ("s","sim","y","yes")
    else:
        cfg.write_settings = input("Gravar ~/.claude/settings.json? [s/N]: ").strip().lower() in ("s","sim","y","yes")
        cfg.discovery = input("Discovery? [s/N]: ").strip().lower() in ("s","sim","y","yes")
        cfg.skip_permissions = input("--dangerously-skip-permissions? [s/N]: ").strip().lower() in ("s","sim","y","yes")

    cfg.write_envfile = input("Gerar .env? [s/N]: ").strip().lower() in ("s","sim","y","yes")

    if input("Testar antes? [S/n]: ").strip().lower() not in ("n","nao","não","no"):
        ok, m = test_gateway(cfg); print(m)
        if not ok and input("Continuar mesmo assim? [s/N]: ").strip().lower() not in ("s","sim","y","yes"): sys.exit(1)
    saved = []
    errors = []
    has_fish = bool(shutil.which("fish"))

    if cfg.save_launcher:
        if has_fish:
            try:
                saved.append(str(write_launcher(cfg)))
            except Exception as e:
                errors.append(f"launcher: {e}")
        else:
            errors.append("launcher: fish não encontrado")
    if cfg.set_global:
        try:
            save_fish_global(cfg); saved.append("fish universal vars")
        except Exception as e:
            errors.append(f"global: {e}")
    if cfg.write_settings:
        try:
            saved.append(str(write_settings(cfg)))
        except Exception as e:
            errors.append(f"settings: {e}")
    if cfg.write_envfile:
        try:
            saved.append(str(write_envfile(cfg)))
        except Exception as e:
            errors.append(f".env: {e}")
    if errors:
        print("\nErros:", file=sys.stderr)
        for e in errors:
            print("-", e, file=sys.stderr)
    if not saved:
        sys.exit(1 if errors else 0)
    print("\nSalvo:")
    for s in saved:
        print("-", s)
    if cfg.save_launcher:
        print(f"\nAbra terminal novo e rode: {prefix}-{norm_profile(cfg.profile)}")


def main():
    if "--plain" in sys.argv or not sys.stdin.isatty(): return plain()
    try: curses.wrapper(lambda s: TUI(s).run())
    except KeyboardInterrupt: print("\nCancelado.")
    except curses.error: plain()

if __name__ == "__main__": main()
