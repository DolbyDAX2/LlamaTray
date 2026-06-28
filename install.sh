#!/usr/bin/env bash
#
# LlamaTray — Installation Script (v1.2.0)
# Supports: Ubuntu/Debian, Fedora
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
INSTALL_DIR="$SCRIPT_DIR"
HOME_DIR="$HOME"
DESKTOP_DIR="$HOME_DIR/.local/share/applications"
BIN_DIR="$HOME_DIR/.local/bin"
VENV_DIR="$INSTALL_DIR/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Detect distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/redhat-release ]; then
        echo "fedora"
    else
        echo "unknown"
    fi
}

# Install system dependencies based on distro
install_system_deps() {
    local distro
    distro=$(detect_distro)

    case "$distro" in
        ubuntu|debian|linuxmint)
            info "Detected Debian/Ubuntu-based system."
            info "Installing system dependencies: python3-venv, python3-pip"
            sudo apt-get update
            sudo apt-get install -y python3-venv python3-pip
            ;;
        fedora)
            info "Detected Fedora system."
            info "Installing system dependencies: python3"
            sudo dnf install -y python3
            ;;
        arch|archlinux)
            info "Detected Arch Linux system."
            info "Installing system dependencies: python"
            sudo pacman -Sy --noconfirm python
            ;;
        *)
            warn "Unknown distribution ($distro). Attempting generic installation."
            # Try apt first, then dnf, then pacman
            if command -v apt-get &>/dev/null; then
                sudo apt-get update
                sudo apt-get install -y python3-venv python3-pip
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y python3
            elif command -v pacman &>/dev/null; then
                sudo pacman -Sy --noconfirm python
            else
                error "No supported package manager found. Please install Python 3 manually."
                exit 1
            fi
            ;;
    esac
}

# Check if python3 is available
check_python() {
    if ! command -v python3 &>/dev/null; then
        error "Python 3 not found. Installing system dependencies..."
        install_system_deps
    fi
    # Verify again
    if ! command -v python3 &>/dev/null; then
        error "Python 3 still not available after installation attempt."
        exit 1
    fi
    info "Python 3 found: $(python3 --version)"
}

# Create virtual environment
create_venv() {
    if [ -d "$VENV_DIR" ]; then
        info "Virtual environment already exists at $VENV_DIR"
    else
        info "Creating virtual environment at $VENV_DIR"
        python3 -m venv "$VENV_DIR"
    fi
}

# Install Python dependencies
install_python_deps() {
    info "Installing Python dependencies from requirements.txt"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    info "Python dependencies installed successfully."
}

# Create launcher script
create_launcher() {
    mkdir -p "$BIN_DIR"

    local icon_path="$INSTALL_DIR/LlamaTray/assets/icon.png"
    if [ ! -f "$icon_path" ]; then
        icon_path=""
    fi

    cat > "$BIN_DIR/llamatray" <<LAUNCHER_EOF
#!/usr/bin/env bash
# LlamaTray launcher script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$INSTALL_DIR"
VENV_DIR="$PROJECT_DIR/venv"

# Activate virtual environment and run
exec "$VENV_DIR/bin/python" -m LlamaTray "\$@"
LAUNCHER_EOF

    chmod +x "$BIN_DIR/llamatray"
    info "Launcher script created at $BIN_DIR/llamatray"
}

# Create .desktop file
create_desktop_file() {
    mkdir -p "$DESKTOP_DIR"

    local icon_path="$INSTALL_DIR/LlamaTray/assets/icon.png"
    local icon_entry=""
    if [ -f "$icon_path" ]; then
        icon_entry="Icon=$icon_path"
    else
        icon_entry="Icon=utilities-terminal"
    fi

    cat > "$DESKTOP_DIR/llamatray.desktop" <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=LlamaTray
GenericName=AI Server Manager
Comment=Llama.cpp server management tool for Linux
Exec=$BIN_DIR/llamatray
$icon_entry
Categories=Utility;
Terminal=false
Keywords=llama;ai;llamacpp;server;
DESKTOP_EOF

    info "Desktop file created at $DESKTOP_DIR/llamatray.desktop"
}

# Main installation flow
main() {
    echo ""
    echo "========================================"
    echo "  LlamaTray v1.2.0 Installer"
    echo "========================================"
    echo ""

    # Verify we're in the right directory
    if [ ! -f "$INSTALL_DIR/requirements.txt" ]; then
        error "This script must be run from the LlamaTray repository root."
        error "Current directory: $(pwd)"
        exit 1
    fi

    if [ ! -d "$INSTALL_DIR/LlamaTray" ]; then
        error "LlamaTray package directory not found. Are you in the correct repository?"
        exit 1
    fi

    # Step 1: Check Python availability
    check_python

    # Step 2: Create virtual environment
    create_venv

    # Step 3: Install Python dependencies
    install_python_deps

    # Step 4: Create launcher script
    create_launcher

    # Step 5: Create .desktop file
    create_desktop_file

    echo ""
    info "Installation complete!"
    echo ""
    info "You can now launch LlamaTray in the following ways:"
    echo "  1. From application menu: search for 'LlamaTray'"
    echo "  2. From terminal: llamatray"
    echo "  3. Directly: $VENV_DIR/bin/python -m LlamaTray"
    echo ""
}

main "$@"
