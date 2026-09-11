#!/usr/bin/env bash
#
# LlamaTray — Installation Script
# Supports: Ubuntu/Debian, Fedora, Arch
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$SCRIPT_DIR/LlamaTray/version.py"
APP_VERSION="$(awk -F'"' '/^__version__ = / {print $2; exit}' "$VERSION_FILE")"
PROJECT_DIR="$SCRIPT_DIR"
INSTALL_DIR="$SCRIPT_DIR"
HOME_DIR="$HOME"
DESKTOP_DIR="$HOME_DIR/.local/share/applications"
BIN_DIR="$HOME_DIR/.local/bin"
VENV_DIR="$INSTALL_DIR/venv"
ICON_SRC="$INSTALL_DIR/LlamaTray/assets/llamatray.png"
ICON_THEME_ROOT="$HOME_DIR/.local/share/icons/hicolor"
DESKTOP_FILE="$DESKTOP_DIR/llamatray.desktop"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Use sudo only when needed and available (root or no-sudo systems)
SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo &>/dev/null; then
    SUDO="sudo"
fi

if [ -z "$APP_VERSION" ]; then
    error "Version could not be read from $VERSION_FILE"
    exit 1
fi

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
            $SUDO apt-get update
            $SUDO apt-get install -y python3-venv python3-pip
            ;;
        fedora)
            info "Detected Fedora system."
            local fedora_pkgs=(python3)
            # GNOME Shell legacy tray'i göstermez; QSystemTrayIcon için
            # AppIndicator/StatusNotifier eklentisini de kur.
            local desktop_context="${XDG_CURRENT_DESKTOP:-} ${XDG_SESSION_DESKTOP:-} ${DESKTOP_SESSION:-}"
            if [[ "$desktop_context" =~ [Gg][Nn][Oo][Mm][Ee] ]] || command -v gnome-shell &>/dev/null; then
                fedora_pkgs+=(gnome-shell-extension-appindicator)
                info "GNOME tray support: installing gnome-shell-extension-appindicator"
            fi
            $SUDO dnf install -y "${fedora_pkgs[@]}"
            if command -v gnome-extensions &>/dev/null; then
                gnome-extensions enable appindicatorsupport@rgcjonas.gmail.com \
                    >/dev/null 2>&1 || warn "Could not enable AppIndicator extension automatically."
                info "Log out/in of GNOME once if the tray icon is not visible immediately."
            fi
            ;;
        arch|archlinux)
            info "Detected Arch Linux system."
            info "Installing system dependencies: python"
            $SUDO pacman -Sy --noconfirm python
            ;;
        *)
            warn "Unknown distribution ($distro). Attempting generic installation."
            # Try apt first, then dnf, then pacman
            if command -v apt-get &>/dev/null; then
                $SUDO apt-get update
                $SUDO apt-get install -y python3-venv python3-pip
            elif command -v dnf &>/dev/null; then
                $SUDO dnf install -y python3
            elif command -v pacman &>/dev/null; then
                $SUDO pacman -Sy --noconfirm python
            else
                error "No supported package manager found. Please install Python 3 manually."
                exit 1
            fi
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Qt6/XCB runtime dependencies (Apt-based systems)
#
# PyQt6/Qt6 needs several small libxcb* libraries at runtime. Minimal X11
# desktops (XFCE, MATE, bare Xorg on Ubuntu Server) often lack them, which
# makes the app crash on start ("could not load the Qt platform plugin xcb").
# ---------------------------------------------------------------------------
install_xcb_deps() {
    if ! command -v apt-get &>/dev/null; then
        # Only Apt-based systems are in scope for this helper.
        return 0
    fi

    local pkgs=(
        libxcb-cursor0
        libxcb-xinerama0
        libxcb-icccm4
        libxcb-image0
        libxcb-keysyms1
        libxcb-render-util0
        libxkbcommon-x11-0
    )
    local missing=() p
    for p in "${pkgs[@]}"; do
        if command -v dpkg &>/dev/null && ! dpkg -s "$p" &>/dev/null 2>&1; then
            missing+=("$p")
        fi
    done

    if [ ${#missing[@]} -eq 0 ]; then
        info "Qt6/XCB runtime dependencies already present."
        return 0
    fi

    info "Installing Qt6/XCB runtime dependencies: ${missing[*]}"
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get update
    DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y "${missing[@]}"
    info "Qt6/XCB runtime dependencies installed."
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

    cat > "$BIN_DIR/llamatray" <<LAUNCHER_EOF
#!/usr/bin/env bash
# LlamaTray launcher script
PROJECT_DIR="$INSTALL_DIR"
VENV_DIR="$PROJECT_DIR/venv"

# Activate virtual environment and run
cd "$PROJECT_DIR"
exec "$VENV_DIR/bin/python" -m LlamaTray "\$@"
LAUNCHER_EOF

    chmod +x "$BIN_DIR/llamatray"
    info "Launcher script created at $BIN_DIR/llamatray"
}

# ---------------------------------------------------------------------------
# Shell-aware PATH management
#
# Makes sure ~/.local/bin is in the user's PATH using shell-native syntax:
#   bash -> export PATH="$HOME/.local/bin:$PATH"  (~/.bashrc or ~/.bash_profile)
#   zsh  -> export PATH="$HOME/.local/bin:$PATH"  (~/.zshrc)
#   fish -> fish_add_path / set -Ua fish_user_paths
# The active shell is detected via $SHELL; when detection is uncertain the
# existing user config files are scanned and every detected profile gets the
# appropriate syntax.
# ---------------------------------------------------------------------------

# Print one supported shell name per line, deduplicated, in priority order.
detect_shells() {
    local found="" s base=""
    # 1) Active shell from $SHELL
    if [ -n "${SHELL:-}" ]; then
        base="$(basename "$SHELL")"
        case "$base" in
            bash|zsh|fish) found="$base" ;;
        esac
    fi
    # 2) Fallback / extra detection: scan well-known user config files.
    [ -f "$HOME_DIR/.bashrc" ]                 && found="$found bash"
    [ -f "$HOME_DIR/.bash_profile" ]           && found="$found bash"
    [ -f "$HOME_DIR/.zshrc" ]                 && found="$found zsh"
    [ -f "$HOME_DIR/.config/fish/config.fish" ] && found="$found fish"

    # Deduplicate, preserve order
    local out="" f
    for f in $found; do
        case " $out " in
            *" $f "*) ;;
            *) out="$out $f" ;;
        esac
    done
    [ -n "$out" ] && printf '%s\n' $out
}

append_path_bash() {
    local target=""
    if [ -f "$HOME_DIR/.bashrc" ]; then
        target="$HOME_DIR/.bashrc"
    elif [ -f "$HOME_DIR/.bash_profile" ]; then
        target="$HOME_DIR/.bash_profile"
    else
        target="$HOME_DIR/.bashrc"  # create the conventional file
    fi
    local line='export PATH="$HOME/.local/bin:$PATH"'
    if grep -qF "$line" "$target" 2>/dev/null; then
        info "Bash PATH entry already present in $target"
        return 0
    fi
    {
        echo ""
        echo "# Added by LlamaTray installer — ensure ~/.local/bin is in PATH"
        printf '%s\n' "$line"
    } >> "$target"
    info "Appended PATH entry for bash to $target"
}

append_path_zsh() {
    local target="$HOME_DIR/.zshrc"
    local line='export PATH="$HOME/.local/bin:$PATH"'
    if grep -qF "$line" "$target" 2>/dev/null; then
        info "Zsh PATH entry already present in $target"
        return 0
    fi
    {
        echo ""
        echo "# Added by LlamaTray installer — ensure ~/.local/bin is in PATH"
        printf '%s\n' "$line"
    } >> "$target"
    info "Appended PATH entry for zsh to $target"
}

append_path_fish() {
    local cfg="$HOME_DIR/.config/fish/config.fish"
    # Preferred: fish_add_path is idempotent and persists the right variable.
    if command -v fish &>/dev/null; then
        if fish -c "fish_add_path '$BIN_DIR'" >/dev/null 2>&1; then
            info "Added $BIN_DIR to fish user paths (fish_add_path)."
            return 0
        fi
    fi
    # Fallback: append the persistent variable line to config.fish.
    local line="set -Ua fish_user_paths $BIN_DIR"
    if grep -qF "$line" "$cfg" 2>/dev/null; then
        info "Fish PATH entry already present in $cfg"
        return 0
    fi
    mkdir -p "$(dirname "$cfg")"
    {
        echo ""
        echo "# Added by LlamaTray installer — ensure ~/.local/bin is in PATH"
        printf '%s\n' "$line"
    } >> "$cfg"
    info "Appended PATH entry for fish to $cfg"
}

manage_path_env() {
    info "Checking PATH configuration for $BIN_DIR"

    # Already in the current session's PATH? Nothing to do.
    case ":${PATH}:" in
        *":$BIN_DIR:"*)
            info "$BIN_DIR is already in PATH."
            return 0
            ;;
    esac

    local detected=""
    detected="$(detect_shells || true)"

    if [ -z "$detected" ]; then
        # Detection uncertain and no config files found: default to bash.
        warn "Could not detect a shell profile. Falling back to ~/.bashrc."
        detected="bash"
    fi

    local shell handled=0
    while IFS= read -r shell; do
        [ -z "$shell" ] && continue
        case "$shell" in
            bash) append_path_bash ;;
            zsh)  append_path_zsh ;;
            fish) append_path_fish ;;
            *) warn "Unsupported shell '$shell' — skipped." ;;
        esac
        handled=1
    done <<< "$detected"

    if [ "$handled" -eq 0 ]; then
        warn "No shell profile could be updated. Add $BIN_DIR to your PATH manually."
    else
        info "Open a new terminal (or run 'source' on your rc file) for the PATH change to take effect."
    fi
}

# ---------------------------------------------------------------------------
# Icon & desktop entry registration
# ---------------------------------------------------------------------------
install_icon() {
    if [ ! -f "$ICON_SRC" ]; then
        warn "Application icon not found at $ICON_SRC — skipping icon registration."
        return 0
    fi

    local dest_dir="$HOME_DIR/.local/share/icons/hicolor/256x256/apps"
    mkdir -p "$dest_dir"
    cp -f "$ICON_SRC" "$dest_dir/llamatray.png"
    info "Icon installed to $dest_dir/llamatray.png"

    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -qf "$ICON_THEME_ROOT/" 2>/dev/null || true
        info "GTK icon cache updated."
    fi
}

# Create .desktop file
create_desktop_file() {
    mkdir -p "$DESKTOP_DIR"

    # Prefer the installed hicolor icon name; fall back to absolute path.
    local icon_entry="Icon=llamatray"
    if [ ! -f "$HOME_DIR/.local/share/icons/hicolor/256x256/apps/llamatray.png" ]; then
        if [ -f "$ICON_SRC" ]; then
            icon_entry="Icon=$ICON_SRC"
        else
            icon_entry="Icon=utilities-terminal"
        fi
    fi

    cat > "$DESKTOP_FILE" <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=LlamaTray
GenericName=AI Server Manager
Comment=Llama.cpp server management tool for Linux
Exec=$BIN_DIR/llamatray
$icon_entry
Categories=Utility;
Terminal=false
StartupWMClass=LlamaTray
Keywords=llama;ai;llamacpp;server;
DESKTOP_EOF

    info "Desktop file created at $DESKTOP_FILE"
}

# Main installation flow
main() {
    echo ""
    echo "========================================"
    echo "  LlamaTray v$APP_VERSION Installer"
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

    # Step 4: Qt6/XCB runtime libraries (Apt-based systems, minimal X11 desktops)
    install_xcb_deps

    # Step 5: Create launcher script
    create_launcher

    # Step 6: Register application icon
    install_icon

    # Step 7: Create .desktop file
    create_desktop_file

    # Step 8: Ensure ~/.local/bin is in the user's PATH (shell-aware)
    manage_path_env

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
