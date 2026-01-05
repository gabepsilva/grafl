# grafl

A text-to-speech application with pause, resume, and stop controls using Piper TTS and a GTK4 floating window interface.

## Features

- **Text-to-Speech**: Uses Piper TTS engine for high-quality speech synthesis
- **GTK4 Interface**: Modern floating window with playback controls
- **Playback Control**: Pause, resume, and stop functionality
- **Clipboard Integration**: Automatically reads selected text from clipboard
- **Cross-Platform Audio**: Uses sounddevice for reliable audio playback

## Requirements

### System Dependencies

- **Python 3.9+**
- **GTK4** and related libraries:
  - Arch Linux: `gtk4 python-gobject python-cairo`
  - Debian/Ubuntu: `libgtk-4-1 gir1.2-gtk-4.0 python3-gi python3-cairo`
  - Fedora/RHEL: `gtk4 python3-gobject python3-cairo`
- **Clipboard tools** (one of):
  - `xsel` or `xclip` (X11)
  - `wl-clipboard` (Wayland)

### Python Dependencies

All Python dependencies are automatically installed into an isolated virtual environment:
- `piper-tts`
- `PyGObject`
- `pycairo`
- `sounddevice`
- `numpy`

## Installation

### Quick Install (Recommended)

Install grafl with a single command:

```bash
curl -sS https://raw.githubusercontent.com/gabepsilva/grafl/master/install.sh | sh
```

Or if you prefer to review the script first:

```bash
curl -sS https://raw.githubusercontent.com/gabepsilva/grafl/master/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

### Installation Options

```bash
# Standard installation
./install.sh

# Reinstall (removes existing installation)
./install.sh --reinstall

# Skip voice model download
./install.sh --no-models

# Use custom repository
./install.sh --repo https://github.com/gabepsilva/grafl.git --branch develop
```

### Uninstallation

To completely remove grafl and all its files:

```bash
# Interactive uninstall (with confirmation)
./uninstall.sh

# Force uninstall (no confirmation)
./uninstall.sh --force

# Quiet mode (minimal output)
./uninstall.sh --quiet
```

The uninstall script removes:
- Wrapper script at `~/.local/bin/grafl`
- Installation directory `~/.local/share/grafl/` (venv, models, repo)
- Desktop entries
- Configuration files
- Cache files
- All other grafl-related files

### Manual Installation

If you prefer to install manually:

```bash
# Clone the repository
git clone https://github.com/gabepsilva/grafl.git
cd grafl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Download voice models (optional)
./download_models.sh
```

## Usage

### Basic Commands

```bash
# Speak currently selected text
grafl speak-selection

# Speak text directly
grafl speak "Hello, world!"

# Speak text from stdin
echo "Hello, world!" | grafl speak

# Get selected text (for testing)
grafl get-clipboard

# Show help
grafl help
```

### Voice Models

Voice models are downloaded to `~/.local/share/grafl/models/` during installation. If you need to download additional models or re-download, you can:

1. Use the `download_models.sh` script in the repository
2. Manually download from [Piper Voices](https://huggingface.co/rhasspy/piper-voices)
3. Place `.onnx` and `.onnx.json` files in `~/.local/share/grafl/models/`

## Configuration

### Model Location

grafl looks for voice models in the following locations (in order):

1. Path specified in configuration
2. `~/.local/share/grafl/models/` (user installation)
3. Project root directory (development)

### Environment Variables

- `GRAFL_HOME`: Override installation directory (default: `~/.local/share/grafl`)
- `GDK_BACKEND`: Set to `wayland` for Wayland (auto-detected)

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## Troubleshooting

### "No selected text found"

Make sure you have a clipboard tool installed:
- X11: `xsel` or `xclip`
- Wayland: `wl-clipboard`

### "Window transparency may not work correctly"

This warning appears on X11. For best results, use Wayland or set `GDK_BACKEND=wayland`.

### "TTS provider is not properly configured"

Ensure that:
1. Voice models are downloaded to `~/.local/share/grafl/models/`
2. The `piper` binary is available in the virtual environment
3. Model files have `.onnx` and `.onnx.json` extensions

### PATH Issues

If `grafl` command is not found, add `~/.local/bin` to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## Development

```bash
# Clone repository
git clone https://github.com/gabepsilva/grafl.git
cd grafl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Run tests (if available)
python -m pytest
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

