#!/bin/bash
# grafl installation script
# Install grafl TTS application to ~/.local/bin with isolated venv

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GRAFL_HOME="${GRAFL_HOME:-$HOME/.local/share/grafl}"
GRAFL_BIN="$HOME/.local/bin/grafl"
GRAFL_VENV="$GRAFL_HOME/venv"
GRAFL_MODELS="$GRAFL_HOME/models"
GRAFL_REPO="${GRAFL_REPO:-https://github.com/gabepsilva/grafl.git}"
GRAFL_BRANCH="${GRAFL_BRANCH:-master}"
DOWNLOAD_MODELS="${DOWNLOAD_MODELS:-}"

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

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_python() {
    if check_command python3; then
        local version
        version=$(python3 --version 2>&1 | awk '{print $2}')
        local major minor
        IFS='.' read -r major minor _ <<< "$version"
        if [ "$major" -eq 3 ] && [ "${minor:-0}" -ge 9 ]; then
            success "Found Python $version"
            return 0
        fi
    fi
    error "Python 3.9+ is required but not found"
    return 1
}

check_system_deps() {
    local missing=()
    local distro=""
    
    # Detect distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        distro="$ID"
    fi
    
    # Check for GTK4 and related packages
    case "$distro" in
        arch|manjaro|endeavouros)
            if ! pacman -Qi gtk4 >/dev/null 2>&1; then
                missing+=("gtk4")
            fi
            if ! pacman -Qi python-gobject >/dev/null 2>&1; then
                missing+=("python-gobject")
            fi
            if ! pacman -Qi python-cairo >/dev/null 2>&1; then
                missing+=("python-cairo")
            fi
            ;;
        debian|ubuntu|mint)
            if ! dpkg -l | grep -q "^ii.*libgtk-4-"; then
                missing+=("libgtk-4-1 gir1.2-gtk-4.0")
            fi
            if ! dpkg -l | grep -q "^ii.*python3-gi"; then
                missing+=("python3-gi")
            fi
            if ! dpkg -l | grep -q "^ii.*python3-cairo"; then
                missing+=("python3-cairo")
            fi
            ;;
        fedora|rhel|centos)
            if ! rpm -q gtk4 >/dev/null 2>&1; then
                missing+=("gtk4")
            fi
            if ! rpm -q python3-gobject >/dev/null 2>&1; then
                missing+=("python3-gobject")
            fi
            if ! rpm -q python3-cairo >/dev/null 2>&1; then
                missing+=("python3-cairo")
            fi
            ;;
        *)
            warning "Unknown distribution, skipping system dependency checks"
            ;;
    esac
    
    if [ ${#missing[@]} -gt 0 ]; then
        warning "Some system dependencies may be missing:"
        for dep in "${missing[@]}"; do
            echo "  - $dep"
        done
        echo ""
        echo "Please install them using your package manager, for example:"
        case "$distro" in
            arch|manjaro|endeavouros)
                echo "  sudo pacman -S gtk4 python-gobject python-cairo"
                ;;
            debian|ubuntu|mint)
                echo "  sudo apt-get install libgtk-4-1 gir1.2-gtk-4.0 python3-gi python3-cairo"
                ;;
            fedora|rhel|centos)
                echo "  sudo dnf install gtk4 python3-gobject python3-cairo"
                ;;
        esac
        echo ""
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "System dependencies check passed"
    fi
}

clone_repo() {
    local temp_dir
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT
    
    info "Cloning grafl repository..."
    if [ -d "$GRAFL_HOME/repo" ]; then
        info "Repository already exists, updating..."
        cd "$GRAFL_HOME/repo"
        git fetch origin "$GRAFL_BRANCH" || true
        git checkout "$GRAFL_BRANCH" || true
        git pull origin "$GRAFL_BRANCH" || true
    else
        git clone --branch "$GRAFL_BRANCH" --depth 1 "$GRAFL_REPO" "$GRAFL_HOME/repo" || {
            error "Failed to clone repository"
            exit 1
        }
    fi
    success "Repository cloned/updated"
}

create_venv() {
    info "Creating virtual environment..."
    if [ -d "$GRAFL_VENV" ]; then
        if [ "${REINSTALL:-}" = "1" ]; then
            info "Removing existing venv (--reinstall flag set)"
            rm -rf "$GRAFL_VENV"
        else
            success "Virtual environment already exists"
            return 0
        fi
    fi
    
    python3 -m venv "$GRAFL_VENV" || {
        error "Failed to create virtual environment"
        exit 1
    }
    success "Virtual environment created"
}

install_dependencies() {
    info "Installing Python dependencies..."
    
    # Activate venv and upgrade pip
    source "$GRAFL_VENV/bin/activate"
    pip install --upgrade pip --quiet || {
        error "Failed to upgrade pip"
        exit 1
    }
    
    # Install dependencies from requirements.txt
    if [ -f "$GRAFL_HOME/repo/requirements.txt" ]; then
        pip install -r "$GRAFL_HOME/repo/requirements.txt" || {
            error "Failed to install dependencies"
            exit 1
        }
    else
        error "requirements.txt not found in repository"
        exit 1
    fi
    
    # Install grafl package itself
    pip install -e "$GRAFL_HOME/repo" || {
        error "Failed to install grafl package"
        exit 1
    }
    
    deactivate
    success "Dependencies installed"
}

create_wrapper() {
    info "Creating wrapper script..."
    
    # Ensure ~/.local/bin exists
    mkdir -p "$HOME/.local/bin"
    
    # Create wrapper script
    cat > "$GRAFL_BIN" << 'EOF'
#!/bin/bash
# grafl wrapper script - activates venv and runs grafl

GRAFL_VENV="$HOME/.local/share/grafl/venv"

if [ ! -d "$GRAFL_VENV" ]; then
    echo "Error: grafl virtual environment not found at $GRAFL_VENV" >&2
    echo "Please run the install script again." >&2
    exit 1
fi

# Change to home directory to avoid conflicts with development files
cd "$HOME" || cd /

# Activate venv
source "$GRAFL_VENV/bin/activate"

# Use Python isolated mode to prevent importing from current directory
# This avoids conflicts with development grafl.py files
python -I -m grafl.cli "$@"
EOF
    
    chmod +x "$GRAFL_BIN"
    success "Wrapper script created at $GRAFL_BIN"
}

download_models() {
    if [ "$DOWNLOAD_MODELS" = "0" ] || [ "$DOWNLOAD_MODELS" = "no" ]; then
        info "Skipping model download (DOWNLOAD_MODELS=no)"
        return 0
    fi
    
    if [ -f "$GRAFL_MODELS/en_US-lessac-medium.onnx" ] && [ -f "$GRAFL_MODELS/en_US-lessac-medium.onnx.json" ]; then
        success "Voice models already exist"
        return 0
    fi
    
    if [ -z "$DOWNLOAD_MODELS" ]; then
        echo ""
        read -p "Download voice models? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            info "Skipping model download"
            return 0
        fi
    fi
    
    info "Downloading voice models..."
    mkdir -p "$GRAFL_MODELS"
    
    cd "$GRAFL_MODELS"
    
    if check_command wget; then
        wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx || {
            error "Failed to download model file"
            return 1
        }
        wget -q https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json || {
            error "Failed to download model config"
            return 1
        }
    elif check_command curl; then
        curl -sSL -o en_US-lessac-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx || {
            error "Failed to download model file"
            return 1
        }
        curl -sSL -o en_US-lessac-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json || {
            error "Failed to download model config"
            return 1
        }
    else
        error "Neither wget nor curl found. Please install one to download models."
        return 1
    fi
    
    success "Voice models downloaded to $GRAFL_MODELS"
}

check_path() {
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        warning "$HOME/.local/bin is not in your PATH"
        echo ""
        echo "Add this line to your shell configuration file (~/.bashrc, ~/.zshrc, etc.):"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
        echo "Then reload your shell or run:"
        echo "  source ~/.bashrc  # or ~/.zshrc"
        echo ""
    else
        success "PATH configuration looks good"
    fi
}

verify_installation() {
    info "Verifying installation..."
    
    if [ ! -f "$GRAFL_BIN" ]; then
        error "Wrapper script not found"
        return 1
    fi
    
    if [ ! -d "$GRAFL_VENV" ]; then
        error "Virtual environment not found"
        return 1
    fi
    
    # Test if grafl can be imported
    source "$GRAFL_VENV/bin/activate"
    if python -c "import grafl" 2>/dev/null; then
        success "Installation verified"
        deactivate
        return 0
    else
        error "Failed to import grafl module"
        deactivate
        return 1
    fi
}

show_help() {
    cat << EOF
grafl installation script

Usage: $0 [OPTIONS]

Options:
    --help, -h          Show this help message
    --reinstall         Remove existing installation and reinstall
    --no-models         Skip voice model download
    --repo URL          Use custom repository URL (default: $GRAFL_REPO)
    --branch BRANCH     Use custom branch (default: $GRAFL_BRANCH)

Environment variables:
    GRAFL_HOME          Installation directory (default: ~/.local/share/grafl)
    GRAFL_REPO          Repository URL
    GRAFL_BRANCH        Branch to clone
    DOWNLOAD_MODELS     Set to 'no' to skip model download

Examples:
    $0
    $0 --reinstall
    $0 --no-models
    DOWNLOAD_MODELS=no $0

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --reinstall)
            REINSTALL=1
            shift
            ;;
        --no-models)
            DOWNLOAD_MODELS=no
            shift
            ;;
        --repo)
            GRAFL_REPO="$2"
            shift 2
            ;;
        --branch)
            GRAFL_BRANCH="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main installation flow
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   grafl Installation Script          ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
    echo ""
    
    check_python || exit 1
    check_system_deps
    clone_repo
    create_venv
    install_dependencies
    create_wrapper
    download_models
    verify_installation || exit 1
    check_path
    
    echo ""
    success "Installation complete!"
    echo ""
    echo "grafl has been installed to: $GRAFL_BIN"
    echo ""
    echo "Try it out:"
    echo "  grafl speak-selection    # Speak selected text"
    echo "  grafl speak 'Hello!'     # Speak text directly"
    echo "  grafl help               # Show help"
    echo ""
}

main

