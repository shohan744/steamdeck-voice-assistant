# 🎮 Decky — Local Voice Assistant on Steam Deck

A fully offline, local voice-to-AI pipeline running on a Steam Deck.  
No cloud. No API costs. No internet required.

Built with **whisper.cpp** + **Ollama** + **Qwen 2.5 7B**, all running locally on the Deck's APU inside a Distrobox container.

---

## What It Does

You press Enter, speak a command or question, and get a response — entirely on-device.
```
Your voice → Whisper (speech-to-text) → Ollama (local LLM) → Response
```

**Measured performance on Steam Deck LCD (Zen 2 APU, 16GB unified RAM):**

| Stage | Time |
|---|---|
| Speech transcription (Whisper base.en) | ~2 seconds |
| LLM response (Qwen 2.5 7B Q4_K_M) | 6–15 seconds |
| End-to-end pipeline | ~10–20 seconds |

---

## Why This Is Interesting

The Steam Deck runs a locked-down, read-only SteamOS (Arch-based). Installing development tools normally requires disabling the read-only filesystem, which breaks on OS updates. This project works around that entirely using **Distrobox** — a container that shares your home directory and hardware access while providing a fully writable Arch environment.

The result: a portable, self-contained AI assistant that:
- Runs completely offline — no API keys, no subscriptions
- Survives SteamOS updates (everything lives in /home/deck)
- Uses the Deck's PipeWire audio system from inside a container
- Transcribes speech accurately in ~2 seconds on a CPU

---

## The Stack

| Component | What It Does | Why This One |
|---|---|---|
| **whisper.cpp** | Speech-to-text | C++ port of OpenAI Whisper — fast CPU inference, no Python overhead |
| **Ollama** | LLM serving | Simple model management, OpenAI-compatible API |
| **Qwen 2.5 7B Q4_K_M** | The brain | Best tool-calling accuracy in class for its size; fits in ~4.5GB RAM |
| **Sox** | Audio recording | Handles PipeWire input + 16kHz resampling in one command |
| **Distrobox** | Container env | Writable Arch environment on a read-only OS, shares home dir + hardware |
| **Python** | Glue script | Chains all components; ~80 lines total |

---

## Prerequisites
- Steam Deck (LCD or OLED) running SteamOS 3.x
- Desktop Mode
- ~10GB free disk space
- Internet connection for initial setup only

---

## Installation

### Step 1 — Set up Distrobox

SteamOS's root filesystem is read-only, so we use Distrobox to get a writable Arch environment:
```bash
systemctl --user start podman.socket
systemctl --user enable podman.socket
distrobox create --name devbox --image archlinux:latest
distrobox enter devbox
```

### Step 2 — Install build tools

Inside the container:
```bash
sudo pacman -Syu --noconfirm
sudo pacman -S cmake gcc make git nano python-requests pipewire-pulse sox --noconfirm
```

### Step 3 — Build whisper.cpp
```bash
cd ~
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp
cmake -B build
cmake --build build --config Release -j4
bash ./models/download-ggml-model.sh base.en
```

Test it:
```bash
./build/bin/whisper-cli -m models/ggml-base.en.bin -f samples/jfk.wav
```

You should see JFK transcribed in under 3 seconds.

### Step 4 — Install Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve 2>/dev/null &
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### Step 5 — Run Decky
```bash
git clone https://github.com/shohan744/steamdeck-voice-assistant
cd steamdeck-voice-assistant
python3 voice_assistant.py
```

---

## Usage
```
🎮  Voice Assistant — Steam Deck Edition
   Press Enter to speak, Ctrl+C to quit

[ Press Enter to start recording ]
🎙  Recording for 5 seconds... speak now
✓  Done recording
🔍  Transcribing...

📝  You said: What is the difference between TCP and UDP?
🤖  Thinking...

💬  Response: TCP ensures reliable delivery with error checking and
retransmission. UDP is faster but does not guarantee delivery or order.
Use TCP for accuracy-critical data, UDP for speed-critical streams.
```

---

## Troubleshooting

**distrobox enter fails with "An error occurred"**
The Podman socket is probably not running:
```bash
systemctl --user start podman.socket
systemctl --user status podman.socket
```

**cmake: command not found**
You are on the host SteamOS shell, not inside the container. Run distrobox enter devbox first.

**Ollama install fails**
Run the install script from inside the Distrobox container where the filesystem is writable.

**Nothing transcribed**
Check mic levels:
```bash
sox -t pulseaudio default /dev/null rate 16000 channels 1 trim 0 3 stat
```
Look for "Maximum amplitude" — if it is near 0, your mic is not being picked up.

**Ollama logs flooding the terminal**
Start Ollama with stderr suppressed:
```bash
ollama serve 2>/dev/null &
```

---

## What I Learned

- Why SteamOS is read-only and how Valve's immutable OS design trades flexibility for update reliability
- How Distrobox works under the hood — user namespace mapping, shared mounts, why it is not a VM
- The GGML tensor library architecture — how whisper.cpp and llama.cpp share the same underlying compute layer
- Audio on Linux — PipeWire, why sample rates matter for ML models, the ALSA/PulseAudio/PipeWire stack
- Quantization — why a 4-bit quantized 7B model fits in 4.5GB and how much quality you actually lose
- Container audio — how to expose PipeWire sockets across container boundaries

---

## Background

Built while on active duty with the Florida Army National Guard (MOS 25U — Signal Support Systems Specialist). The goal was a useful AI assistant that works in environments with unreliable or restricted internet access, running on hardware I already had.

---

## License

MIT
