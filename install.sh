#!/bin/bash
set -e

GRN='\033[0;32m'; YLW='\033[1;33m'; BLU='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GRN}✓${NC}  $1"; }
info() { echo -e "${BLU}→${NC}  $1"; }
warn() { echo -e "${YLW}⚠${NC}  $1"; }

echo -e "\n${BLU}🎮  Decky Installer${NC}\n"

info "Installing system packages..."
sudo pacman -S --noconfirm --needed \
    cmake gcc make git python-requests \
    pipewire-pulse sox nano 2>/dev/null
ok "Packages ready"

if [ -f "$HOME/whisper.cpp/build/bin/whisper-cli" ]; then
    ok "whisper.cpp already built — skipping"
else
    info "Cloning and building whisper.cpp (3-5 mins)..."
    cd ~
    [ -d whisper.cpp ] || git clone https://github.com/ggerganov/whisper.cpp
    cd whisper.cpp
    cmake -B build -DCMAKE_BUILD_TYPE=Release > /dev/null 2>&1
    cmake --build build --config Release -j4 > /dev/null 2>&1
    ok "whisper.cpp built"
fi

if [ -f "$HOME/whisper.cpp/models/ggml-base.en.bin" ]; then
    ok "Whisper model already present — skipping"
else
    info "Downloading Whisper model (~142MB)..."
    cd ~/whisper.cpp
    bash ./models/download-ggml-model.sh base.en
    ok "Whisper model ready"
fi

if command -v ollama > /dev/null 2>&1; then
    ok "Ollama already installed — skipping"
else
    info "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh > /dev/null 2>&1
    ok "Ollama installed"
fi

if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
    ok "Ollama model already pulled — skipping"
else
    info "Pulling LLM model (~4.7GB — grab a coffee)..."
    ollama serve 2>/dev/null & OPID=$!
    sleep 3
    ollama pull qwen2.5:7b-instruct-q4_K_M
    kill $OPID 2>/dev/null || true
    ok "Model ready"
fi

info "Creating launcher script..."
cat > "$HOME/launch_decky.sh" << 'LAUNCH'
#!/bin/bash
konsole --new-tab -e bash -c '
    distrobox enter devbox -- bash -c "
        ollama serve 2>/dev/null &
        sleep 2
        python3 ~/voice_assistant.py
        exec bash
    "
'
LAUNCH
chmod +x "$HOME/launch_decky.sh"
ok "Launcher created at ~/launch_decky.sh"

info "Creating desktop entry..."
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/decky.desktop" << 'DESK'
[Desktop Entry]
Version=1.0
Type=Application
Name=Decky
Comment=Local voice assistant on Steam Deck
Exec=/home/deck/launch_decky.sh
Icon=utilities-terminal
Terminal=false
Categories=Utility;
Keywords=voice;assistant;AI;
DESK
chmod +x "$HOME/.local/share/applications/decky.desktop"
ok "Desktop entry created"

echo -e "\n${GRN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GRN}  All done! Run Decky:${NC}"
echo -e "  Terminal : ${BLU}python3 ~/voice_assistant.py${NC}"
echo -e "  Launcher : ${BLU}bash ~/launch_decky.sh${NC}"
echo -e "  Desktop  : Search 'Decky' in app launcher"
echo -e "${GRN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
