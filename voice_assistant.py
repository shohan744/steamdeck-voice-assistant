#!/usr/bin/env python3
import subprocess
import requests
import tempfile
import os
import sys

WHISPER_BIN = os.path.expanduser("~/whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL = os.path.expanduser("~/whisper.cpp/models/ggml-base.en.bin")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"
RECORD_SECONDS = 5

SYSTEM_PROMPT = """You are a concise voice assistant running on a Steam Deck.
Keep responses short and direct — you're being read on a small screen."""

def record_audio(filepath, seconds):
    print(f"🎙  Recording for {seconds} seconds... speak now")
    subprocess.run([
        "sox", "-t", "pulseaudio", "default",
        filepath,
        "rate", "16000",
        "channels", "1",
        "trim", "0", str(seconds)
    ], check=True, stderr=subprocess.DEVNULL)
    print("✓  Done recording")

def transcribe(filepath):
    print("🔍  Transcribing...")
    result = subprocess.run([
        WHISPER_BIN,
        "-m", WHISPER_MODEL,
        "-f", filepath,
        "--no-timestamps",
        "-nt"
    ], capture_output=True, text=True)
    transcript = result.stdout.strip()
    lines = [l.strip() for l in transcript.splitlines()
             if l.strip() and not l.strip().startswith("[")]
    return " ".join(lines)

def ask_ollama(prompt):
    print("🤖  Thinking...")
    response = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False
    })
    response.raise_for_status()
    return response.json()["response"].strip()

def main():
    print("\n🎮  Voice Assistant — Steam Deck Edition")
    print("   Press Enter to speak, Ctrl+C to quit\n")
    while True:
        try:
            input("[ Press Enter to start recording ]")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmpfile = f.name
            try:
                record_audio(tmpfile, RECORD_SECONDS)
                transcript = transcribe(tmpfile)
                if not transcript:
                    print("⚠  Nothing transcribed — try speaking louder\n")
                    continue
                print(f"\n📝  You said: {transcript}")
                response = ask_ollama(transcript)
                print(f"\n💬  Response: {response}\n")
                print("─" * 50)
            finally:
                os.unlink(tmpfile)
        except KeyboardInterrupt:
            print("\n\nBye!")
            sys.exit(0)

if __name__ == "__main__":
    main()
