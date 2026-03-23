#!/usr/bin/env python3
import subprocess
import requests
import tempfile
import os
import sys
import time
import json
from datetime import datetime

# ── Config (edit these to customize) ─────────────────────────────────────────
WHISPER_BIN   = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL = os.path.expanduser("~/whisper.cpp/models/ggml-base.en.bin")
OLLAMA_URL    = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL  = "qwen2.5:7b-instruct-q4_K_M"
RECORD_SECONDS = 5

# ── Colors ────────────────────────────────────────────────────────────────────
GRN  = "\033[0;32m"; YLW  = "\033[1;33m"; BLU  = "\033[0;34m"
CYN  = "\033[0;36m"; RED  = "\033[0;31m"; BOLD = "\033[1m"; NC = "\033[0m"

# ── System prompts ────────────────────────────────────────────────────────────
CHAT_PROMPT = """You are a concise voice assistant running on a Steam Deck.
Keep responses short and direct — you are being read on a small screen.
Never use markdown formatting like asterisks or hashtags in your responses."""

CLASSIFY_PROMPT = """You are a command classifier. The user has spoken a request.
Classify it as one of these exact command keys if it matches, or reply with "chat" if it is a question or conversation.

Command keys:
- open_firefox        : open browser, open default browser, launch browser
- open_terminal       : open terminal, new terminal, open konsole
- lock_screen         : lock screen, lock the computer, lock session
- volume_up           : volume up, louder, increase volume, turn it up
- volume_down         : volume down, quieter, decrease volume, turn it down
- volume_mute         : mute, mute audio, silence
- screenshot          : take a screenshot, screenshot, capture screen
- network_scan        : scan network, scan local network, run nmap, what's on the network
- what_time           : what time is it, current time, what's the time
- what_date           : what is today's date, what day is it, today's date
- open_files          : open file manager, open files, open dolphin
- system_info         : system info, show system stats, how's the system

Reply with ONLY the command key or the word "chat". Nothing else. No punctuation."""

# ── Command dispatch ──────────────────────────────────────────────────────────
def run_command(key):
    commands = {
        "open_firefox":  lambda: (subprocess.Popen(["xdg-open", "https://"]),                                          "Opening default browser."),
        "open_terminal": lambda: (subprocess.Popen(["konsole"]),                                          "Opening terminal."),
        "open_files":    lambda: (subprocess.Popen(["xdg-open", os.path.expanduser("~/")]),                                          "Opening file manager."),
        "lock_screen":   lambda: (subprocess.Popen(["loginctl", "lock-session"]),                         "Locking screen."),
        "volume_up":     lambda: (subprocess.Popen(["bash", "-c", "pactl set-sink-volume @DEFAULT_SINK@ +10%"]), "Volume up."),
        "volume_down":   lambda: (subprocess.Popen(["bash", "-c", "pactl set-sink-volume @DEFAULT_SINK@ -10%"]), "Volume down."),
        "volume_mute":   lambda: (subprocess.Popen(["bash", "-c", "pactl set-sink-mute @DEFAULT_SINK@ toggle"]), "Audio toggled."),
        "screenshot":    lambda: (subprocess.Popen(["spectacle", "-b"]),                                  "Screenshot taken."),
        "what_time":     lambda: (None, f"Current time: {datetime.now().strftime('%I:%M %p')}"),
        "what_date":     lambda: (None, f"Today is {datetime.now().strftime('%A, %B %d %Y')}"),
        "network_scan":  lambda: network_scan(),
        "system_info":   lambda: system_info(),
    }
    if key in commands:
        result = commands[key]()
        return result[1] if isinstance(result, tuple) else result
    return f"Unknown command: {key}"

def network_scan():
    print(f"{BLU}→  Scanning network...{NC}", flush=True)
    try:
        result = subprocess.run(
            ["bash", "-c", "ip route | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+/\\d+' | head -1"],
            capture_output=True, text=True, timeout=5
        )
        subnet = result.stdout.strip() or "192.168.1.0/24"
        scan = subprocess.run(
            ["bash", "-c", f"nmap -sn {subnet} 2>/dev/null | grep 'Nmap scan report' | awk '{{print $5, $6}}'"],
            capture_output=True, text=True, timeout=30
        )
        hosts = scan.stdout.strip()
        if hosts:
            return f"Found {len(hosts.splitlines())} host(s) on {subnet}:\n{hosts}"
        return f"No hosts found on {subnet}"
    except subprocess.TimeoutExpired:
        return "Network scan timed out."
    except Exception as e:
        return f"Scan error: {e}"

def system_info():
    try:
        mem  = subprocess.run(["bash", "-c", "free -h | awk '/^Mem:/ {print $3\"/\"$2}'"],
                              capture_output=True, text=True).stdout.strip()
        cpu  = subprocess.run(["bash", "-c", "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'"],
                              capture_output=True, text=True).stdout.strip()
        disk = subprocess.run(["bash", "-c", "df -h ~ | awk 'NR==2 {print $3\"/\"$2\" (\"$5\" used)\"}'"],
                              capture_output=True, text=True).stdout.strip()
        return f"RAM: {mem} | CPU: {cpu}% | Disk: {disk}"
    except Exception as e:
        return f"Error: {e}"

# ── Ollama health check ───────────────────────────────────────────────────────
def ensure_ollama():
    print(f"{BLU}→  Checking Ollama...{NC}", end=" ", flush=True)
    try:
        requests.get("http://127.0.0.1:11434", timeout=3)
        print(f"{GRN}online{NC}")
        return
    except:
        pass
    print(f"\n{YLW}⚠  Starting Ollama...{NC}")
    subprocess.Popen(["ollama", "serve"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(10):
        time.sleep(1)
        try:
            requests.get("http://127.0.0.1:11434", timeout=2)
            print(f"{GRN}✓  Ready{NC}")
            return
        except:
            pass
    print(f"{YLW}⚠  Ollama slow to start — continuing{NC}")

# ── Classify intent ───────────────────────────────────────────────────────────
def classify(transcript):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": f'User said: "{transcript}"',
            "system": CLASSIFY_PROMPT,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 10}
        }, timeout=30)
        result = response.json()["response"].strip().lower()
        valid = ["open_firefox","open_terminal","open_files","lock_screen",
                 "volume_up","volume_down","volume_mute","screenshot",
                 "what_time","what_date","network_scan","system_info","chat"]
        return result if result in valid else "chat"
    except:
        return "chat"

# ── Record audio ──────────────────────────────────────────────────────────────
def record_audio(filepath, seconds):
    print(f"{YLW}🎙  Recording {seconds}s — speak now...{NC}", flush=True)
    subprocess.run([
        "sox", "-t", "pulseaudio", "default", filepath,
        "rate", "16000", "channels", "1", "trim", "0", str(seconds)
    ], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    print(f"{GRN}✓  Done{NC}", flush=True)

# ── Transcribe ────────────────────────────────────────────────────────────────
def transcribe(filepath):
    print(f"{BLU}🔍  Transcribing...{NC}", flush=True)
    result = subprocess.run([
        WHISPER_BIN, "-m", WHISPER_MODEL, "-f", filepath,
        "--no-timestamps", "-nt",
    ], capture_output=True, text=True)
    lines = [
        l.strip() for l in result.stdout.splitlines()
        if l.strip() and not any(l.strip().startswith(p)
            for p in ["[", "whisper_", "main:", "system_info", "ggml_"])
    ]
    return " ".join(lines).strip()

# ── Chat ──────────────────────────────────────────────────────────────────────
def ask_ollama(prompt):
    print(f"{BLU}🤖  Thinking...{NC}", flush=True)
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": CHAT_PROMPT,
            "stream": False
        }, timeout=120)
        response.raise_for_status()
        return response.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        return "Ollama is not running. Start it with: ollama serve &"
    except requests.exceptions.Timeout:
        return "Request timed out."
    except Exception as e:
        return f"Error: {e}"

# ── Banner ────────────────────────────────────────────────────────────────────
def banner():
    print(f"""
{BLU}{BOLD}╔═══════════════════════════════════════╗
║   🎮  Decky — Steam Deck Assistant    ║
║   Local • Offline • No API costs      ║
╚═══════════════════════════════════════╝{NC}
  Commands : Browser, terminal, lock screen,
             volume, screenshot, network scan,
             time, date, system info
  Anything else triggers a chat response.
  {CYN}Ctrl+C{NC} to quit
""")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    banner()
    ensure_ollama()
    print()

    while True:
        try:
            input(f"{BOLD}[ Press Enter to speak ]{NC}")
            print()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmpfile = f.name

            try:
                record_audio(tmpfile, RECORD_SECONDS)
                transcript = transcribe(tmpfile)

                if not transcript:
                    print(f"{YLW}⚠  Nothing heard — try again{NC}\n")
                    continue

                print(f"\n{BOLD}You:{NC} {transcript}")
                intent = classify(transcript)

                if intent != "chat":
                    print(f"{CYN}⚡  Command: {intent}{NC}")
                    result = run_command(intent)
                    print(f"{GRN}{BOLD}Decky:{NC} {result}\n")
                else:
                    response = ask_ollama(transcript)
                    print(f"{GRN}{BOLD}Decky:{NC} {response}\n")

                print("─" * 45)

            finally:
                os.unlink(tmpfile)

        except KeyboardInterrupt:
            print(f"\n{BLU}Goodbye!{NC}\n")
            sys.exit(0)

if __name__ == "__main__":
    main()
