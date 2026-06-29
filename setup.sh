#!/bin/bash
set -e

# ContentForge setup script
# Run: bash setup.sh  (no sudo needed, it calls sudo internally)

if [ "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
    echo "NOTE: Running with sudo. Will fix ownership to $REAL_USER."
else
    REAL_USER="$USER"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=== ContentForge Setup ==="
echo ""

install_pacman() {
    local bin="$1" pkg="$2"
    if command -v "$bin" &>/dev/null; then
        echo "  Found: $(command -v "$bin")"
    else
        echo "  Installing $pkg..."
        sudo pacman -S --noconfirm "$pkg"
    fi
}

setup_sudoers() {
    local file="/etc/sudoers.d/ollama"
    if [ ! -f "$file" ]; then
        echo "$REAL_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start ollama, /usr/bin/systemctl stop ollama" | sudo tee "$file" > /dev/null
        sudo chmod 440 "$file"
        echo "  Passwordless sudo set up for ollama."
    fi
}

echo "[1/7] Python..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON=$(command -v "$cmd")
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python 3 not found. Install: sudo pacman -S python"
    exit 1
fi
echo "  Found: $($PYTHON --version)"

echo "[2/7] System packages..."
install_pacman ffmpeg ffmpeg
install_pacman yt-dlp yt-dlp
if [ ! -f "/usr/share/fonts/TTF/DejaVuSans.ttf" ]; then
    sudo pacman -S --noconfirm ttf-dejavu
else
    echo "  DejaVu Sans: already installed"
fi

echo "[3/7] Local AI (Ollama)..."
install_pacman ollama ollama
sudo systemctl enable --now ollama
echo "  Waiting for Ollama..."
for i in $(seq 1 15); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  Ollama is ready."
        break
    fi
    [ "$i" -eq 15 ] && echo "  WARNING: Ollama not responding, continuing..."
    sleep 1
done
echo "  Downloading AI model (llama3.2:3b, ~2GB)..."
ollama pull llama3.2:3b

echo "[4/7] Passwordless sudo for Ollama..."
setup_sudoers

echo "[5/7] Virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
fi
source venv/bin/activate

echo "[6/7] Python packages..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "[7/7] Final setup..."
[ ! -f ".env" ] && cp .env.example .env
mkdir -p clips output temp

if [ "$SUDO_USER" ]; then
    chown -R "$REAL_USER":"$REAL_USER" venv clips output temp .env 2>/dev/null || true
fi

echo ""
echo "=== Done ==="
echo "  source venv/bin/activate"
echo "  python wizard.py"
echo ""

read -rp "Press Enter to finish..."
