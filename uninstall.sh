#!/bin/bash
# grafl uninstall script
# Completely remove all traces of grafl from the system

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - must match install.sh
GRAFL_HOME="${GRAFL_HOME:-$HOME/.local/share/grafl}"
GRAFL_BIN="$HOME/.local/bin/grafl"

# Additional locations to check
GRAFL_DESKTOP="$HOME/.local/share/applications/grafl.desktop"
GRAFL_CONFIG="$HOME/.config/grafl"
GRAFL_CACHE="$HOME/.cache/grafl"

# Functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1" >&2
}

# Check if grafl is installed
check_installation() {
    local found=0
    
    if [ -f "$GRAFL_BIN" ]; then
        found=1
    fi
    
    if [ -d "$GRAFL_HOME" ]; then
        found=1
    fi
    
    if [ -f "$GRAFL_DESKTOP" ]; then
        found=1
    fi
    
    if [ -d "$GRAFL_CONFIG" ]; then
        found=1
    fi
    
    if [ -d "$GRAFL_CACHE" ]; then
        found=1
    fi
    
    return $found
}

# List all files/directories that will be removed
list_files() {
    echo ""
    info "The following will be removed:"
    echo ""
    
    local count=0
    
    if [ -f "$GRAFL_BIN" ]; then
        echo "  - $GRAFL_BIN"
        ((count++)) || true
    fi
    
    if [ -d "$GRAFL_HOME" ]; then
        echo "  - $GRAFL_HOME/ (entire directory)"
        echo "    Including:"
        [ -d "$GRAFL_HOME/venv" ] && echo "      - venv/ (virtual environment)"
        [ -d "$GRAFL_HOME/models" ] && echo "      - models/ (voice models)"
        [ -d "$GRAFL_HOME/repo" ] && echo "      - repo/ (cloned repository)"
        ((count++)) || true
    fi
    
    if [ -f "$GRAFL_DESKTOP" ]; then
        echo "  - $GRAFL_DESKTOP"
        ((count++)) || true
    fi
    
    if [ -d "$GRAFL_CONFIG" ]; then
        echo "  - $GRAFL_CONFIG/ (configuration directory)"
        ((count++)) || true
    fi
    
    if [ -d "$GRAFL_CACHE" ]; then
        echo "  - $GRAFL_CACHE/ (cache directory)"
        ((count++)) || true
    fi
    
    # Check for any other grafl-related files
    if [ -d "$HOME/.local/bin" ]; then
        local other_bins
        other_bins=$(find "$HOME/.local/bin" -name "*grafl*" 2>/dev/null || true)
        if [ -n "$other_bins" ]; then
            echo "$other_bins" | while read -r bin; do
                if [ "$bin" != "$GRAFL_BIN" ]; then
                    echo "  - $bin"
                    ((count++)) || true
                fi
            done
        fi
    fi
    
    if [ $count -eq 0 ]; then
        warning "No grafl installation found"
        return 1
    fi
    
    echo ""
    return 0
}

# Remove files and directories
remove_files() {
    local removed=0
    local errors=0
    
    # Remove wrapper script
    if [ -f "$GRAFL_BIN" ]; then
        info "Removing wrapper script..."
        if rm -f "$GRAFL_BIN"; then
            success "Removed $GRAFL_BIN"
            ((removed++)) || true
        else
            error "Failed to remove $GRAFL_BIN"
            ((errors++)) || true
        fi
    fi
    
    # Remove main installation directory
    if [ -d "$GRAFL_HOME" ]; then
        info "Removing installation directory..."
        if rm -rf "$GRAFL_HOME"; then
            success "Removed $GRAFL_HOME/"
            ((removed++)) || true
        else
            error "Failed to remove $GRAFL_HOME/"
            ((errors++)) || true
        fi
    fi
    
    # Remove desktop entry
    if [ -f "$GRAFL_DESKTOP" ]; then
        info "Removing desktop entry..."
        if rm -f "$GRAFL_DESKTOP"; then
            success "Removed $GRAFL_DESKTOP"
            ((removed++)) || true
        else
            error "Failed to remove $GRAFL_DESKTOP"
            ((errors++)) || true
        fi
    fi
    
    # Remove config directory
    if [ -d "$GRAFL_CONFIG" ]; then
        info "Removing configuration directory..."
        if rm -rf "$GRAFL_CONFIG"; then
            success "Removed $GRAFL_CONFIG/"
            ((removed++)) || true
        else
            error "Failed to remove $GRAFL_CONFIG/"
            ((errors++)) || true
        fi
    fi
    
    # Remove cache directory
    if [ -d "$GRAFL_CACHE" ]; then
        info "Removing cache directory..."
        if rm -rf "$GRAFL_CACHE"; then
            success "Removed $GRAFL_CACHE/"
            ((removed++)) || true
        else
            error "Failed to remove $GRAFL_CACHE/"
            ((errors++)) || true
        fi
    fi
    
    # Remove any other grafl-related binaries
    if [ -d "$HOME/.local/bin" ]; then
        find "$HOME/.local/bin" -name "*grafl*" -type f 2>/dev/null | while read -r bin; do
            if [ "$bin" != "$GRAFL_BIN" ]; then
                info "Removing $bin..."
                if rm -f "$bin"; then
                    success "Removed $bin"
                    ((removed++)) || true
                else
                    error "Failed to remove $bin"
                    ((errors++)) || true
                fi
            fi
        done
    fi
    
    # Clean up empty parent directories if they're only for grafl
    if [ -d "$HOME/.local/share" ] && [ -z "$(ls -A "$HOME/.local/share" 2>/dev/null)" ]; then
        info "Removing empty share directory..."
        rmdir "$HOME/.local/share" 2>/dev/null || true
    fi
    
    if [ -d "$HOME/.local/bin" ] && [ -z "$(ls -A "$HOME/.local/bin" 2>/dev/null)" ]; then
        info "Removing empty bin directory..."
        rmdir "$HOME/.local/bin" 2>/dev/null || true
    fi
    
    if [ -d "$HOME/.local" ] && [ -z "$(ls -A "$HOME/.local" 2>/dev/null)" ]; then
        info "Removing empty .local directory..."
        rmdir "$HOME/.local" 2>/dev/null || true
    fi
    
    return $errors
}

# Verify removal
verify_removal() {
    info "Verifying removal..."
    
    local remaining=0
    
    if [ -f "$GRAFL_BIN" ] || [ -d "$GRAFL_HOME" ] || [ -f "$GRAFL_DESKTOP" ] || \
       [ -d "$GRAFL_CONFIG" ] || [ -d "$GRAFL_CACHE" ]; then
        remaining=1
    fi
    
    # Check for any remaining grafl files
    if [ -d "$HOME/.local/bin" ]; then
        if find "$HOME/.local/bin" -name "*grafl*" 2>/dev/null | grep -q .; then
            remaining=1
        fi
    fi
    
    if [ $remaining -eq 0 ]; then
        success "All grafl files have been removed"
        return 0
    else
        warning "Some files may still remain. Please check manually:"
        [ -f "$GRAFL_BIN" ] && echo "  - $GRAFL_BIN"
        [ -d "$GRAFL_HOME" ] && echo "  - $GRAFL_HOME/"
        [ -f "$GRAFL_DESKTOP" ] && echo "  - $GRAFL_DESKTOP"
        [ -d "$GRAFL_CONFIG" ] && echo "  - $GRAFL_CONFIG/"
        [ -d "$GRAFL_CACHE" ] && echo "  - $GRAFL_CACHE/"
        return 1
    fi
}

# Check for running processes
check_processes() {
    if command -v pgrep >/dev/null 2>&1; then
        if pgrep -f "grafl" >/dev/null 2>&1; then
            warning "grafl processes are currently running:"
            pgrep -f "grafl" | while read -r pid; do
                ps -p "$pid" -o pid,cmd --no-headers 2>/dev/null || true
            done
            echo ""
            echo "Please stop these processes before uninstalling."
            return 1
        fi
    fi
    return 0
}

show_help() {
    cat << EOF
grafl uninstall script

Usage: $0 [OPTIONS]

Options:
    --help, -h          Show this help message
    --force, -f         Skip confirmation prompt
    --quiet, -q         Quiet mode (minimal output)

Environment variables:
    GRAFL_HOME          Installation directory (default: ~/.local/share/grafl)

This script will remove:
    - $GRAFL_BIN
    - $GRAFL_HOME/ (entire directory)
    - Desktop entries
    - Configuration files
    - Cache files
    - Any other grafl-related files

Examples:
    $0
    $0 --force
    $0 --quiet

EOF
}

# Parse arguments
FORCE=0
QUIET=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --force|-f)
            FORCE=1
            shift
            ;;
        --quiet|-q)
            QUIET=1
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main uninstall flow
main() {
    if [ $QUIET -eq 0 ]; then
        echo ""
        echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║   grafl Uninstall Script             ║${NC}"
        echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
        echo ""
    fi
    
    # Check for running processes
    if ! check_processes; then
        exit 1
    fi
    
    # Check if installed
    if ! check_installation; then
        if [ $QUIET -eq 0 ]; then
            warning "grafl does not appear to be installed"
        fi
        exit 0
    fi
    
    # List files to be removed
    if [ $QUIET -eq 0 ]; then
        if ! list_files; then
            exit 0
        fi
    fi
    
    # Confirmation
    if [ $FORCE -eq 0 ] && [ $QUIET -eq 0 ]; then
        echo ""
        warning "This will permanently delete all grafl files and data."
        read -p "Are you sure you want to continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "Uninstall cancelled"
            exit 0
        fi
        echo ""
    fi
    
    # Remove files
    if [ $QUIET -eq 0 ]; then
        info "Starting removal..."
    fi
    
    if remove_files; then
        if [ $QUIET -eq 0 ]; then
            echo ""
            success "Removal completed successfully"
        fi
    else
        if [ $QUIET -eq 0 ]; then
            echo ""
            error "Some errors occurred during removal"
        fi
        exit 1
    fi
    
    # Verify
    if [ $QUIET -eq 0 ]; then
        verify_removal
        echo ""
        success "grafl has been completely uninstalled"
        echo ""
        info "Note: If you added ~/.local/bin to your PATH, you may want to remove that line from your shell configuration."
        echo ""
    fi
}

main

