#!/usr/bin/env bash
#
# LlamaTray — Uninstall Script
# Removes everything install.sh created for the current user:
#   - ~/.local/bin/llamatray launcher
#   - ~/.local/share/applications/llamatray.desktop
#   - hicolor icon entry (+ icon cache refresh)
#   - PATH entries added to shell rc files (bash/zsh/fish)
# NOTE: ~/.llamatray (saved settings & profiles) is NEVER removed by this script.
# System packages (python3, libxcb*) are shared dependencies and are kept.
#
set -euo pipefail

HOME_DIR="$HOME"
BIN_DIR="$HOME_DIR/.local/bin"
LAUNCHER="$BIN_DIR/llamatray"
DESKTOP_FILE="$HOME_DIR/.local/share/applications/llamatray.desktop"
ICON_FILE="$HOME_DIR/.local/share/icons/hicolor/256x256/apps/llamatray.png"
ICON_THEME_ROOT="$HOME_DIR/.local/share/icons/hicolor"
CONFIG_DIR="$HOME_DIR/.llamatray"
MARKER_PREFIX='# Added by LlamaTray installer'
BASH_EXPORT_LINE='export PATH="$HOME/.local/bin:$PATH"'

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

for arg in "$@"; do
    case "$arg" in
        -h|--help)
            echo "Usage: ./uninstall.sh"
            echo ""
            echo "  Removes the launcher, desktop entry, icon and installer-added"
            echo "  PATH entries. ~/.llamatray (settings & profiles) is always kept."
            exit 0
            ;;
        *) error "Unknown option: $arg"; exit 1 ;;
    esac
done

remove_launcher() {
    if [ -f "$LAUNCHER" ]; then
        rm -f "$LAUNCHER"
        info "Removed launcher: $LAUNCHER"
    fi
}

remove_desktop_entry() {
    if [ -f "$DESKTOP_FILE" ]; then
        rm -f "$DESKTOP_FILE"
        update-desktop-database "$HOME_DIR/.local/share/applications" 2>/dev/null || true
        info "Removed desktop entry: $DESKTOP_FILE"
    fi
}

remove_icon() {
    local removed=0
    if [ -f "$ICON_FILE" ]; then
        rm -f "$ICON_FILE"
        removed=1
        info "Removed icon: $ICON_FILE"
    fi
    # Also remove a stray llamatray.png from other hicolor sizes, if any.
    local size_dir f
    for size_dir in "$HOME_DIR/.local/share/icons/hicolor"/*/apps; do
        [ -d "$size_dir" ] || continue
        for f in "$size_dir/llamatray".*; do
            [ -f "$f" ] || continue
            rm -f "$f"
            removed=1
            info "Removed icon: $f"
        done
    done
    if [ "$removed" -eq 1 ] && command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -qf "$ICON_THEME_ROOT/" 2>/dev/null || true
    fi
}

# Delete the installer marker lines and, when present, the PATH line
# immediately below each marker. Everything else is preserved.
strip_path_entries() {
    local file="$1" pattern_line="$2"
    [ -f "$file" ] || return 0
    local tmp
    tmp="$(mktemp)"
    awk -v expline="$pattern_line" '
        $0 ~ "^# Added by LlamaTray installer" { skip_next = 1; next }
        {
            if (skip_next) {
                if ($0 == expline) { skip_next = 0; next }
                skip_next = 0
            }
            print
        }
    ' "$file" > "$tmp"
    mv -f "$tmp" "$file"
}

remove_path_entries() {
    info "Removing PATH entries added by the installer..."
    local f
    for f in "$HOME_DIR/.bashrc" "$HOME_DIR/.bash_profile" "$HOME_DIR/.zshrc"; do
        if [ -f "$f" ] && grep -qF "$MARKER_PREFIX" "$f"; then
            strip_path_entries "$f" "$BASH_EXPORT_LINE"
            info "Cleaned: $f"
        fi
    done

    local fish_cfg="$HOME_DIR/.config/fish/config.fish"
    if [ -f "$fish_cfg" ]; then
        # fish_add_path / installer fallback writes 'set -Ua fish_user_paths <dir>'
        local fish_line="set -Ua fish_user_paths $BIN_DIR"
        if grep -qF "$MARKER_PREFIX" "$fish_cfg"; then
            strip_path_entries "$fish_cfg" "$fish_line"
            info "Cleaned: $fish_cfg"
        elif grep -qF "$fish_line" "$fish_cfg"; then
            # No marker (entry came from fish_add_path) — remove the exact line.
            local tmp
            tmp="$(mktemp)"
            grep -vF "$fish_line" "$fish_cfg" > "$tmp" || true
            mv -f "$tmp" "$fish_cfg"
            info "Cleaned: $fish_cfg (fish_user_paths entry)"
        fi
    fi
}

# NOTE: remove_config intentionally does not exist — ~/.llamatray is never deleted.

main() {
    echo ""
    echo "========================================"
    echo "  LlamaTray Uninstaller"
    echo "========================================"
    echo ""

    remove_launcher
    remove_desktop_entry
    remove_icon
    remove_path_entries

    echo ""
    info "Uninstall complete."
    if [ -d "$CONFIG_DIR" ]; then
        info "Saved settings & profiles kept: $CONFIG_DIR (never removed by this script)"
    fi
    echo "  - System packages (python3, libxcb*) are shared dependencies and were kept."
    echo "  - If you installed from a cloned repository, remove it manually:"
    echo "      rm -rf <LlamaTray repository directory>"
    echo ""
}

main
