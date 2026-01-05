# grafl

A text-to-speech application with pause, resume, and stop controls using multiple TTS engines and a GTK4 floating window interface.

## Features

- **Multiple TTS Engines**: 
  - **Piper TTS** (default) - Local, offline, high-quality neural voices
  - **AWS Polly** - Cloud-based neural voices (requires AWS credentials)
- **GTK4 Interface**: Modern floating window with playback controls
- **Playback Control**: Pause, resume, skip forward/backward, and stop
- **In-App Settings**: Hamburger menu to switch voice providers and log levels
- **Clipboard Integration**: Automatically reads selected text from clipboard
- **Cross-Platform Audio**: Uses sounddevice for reliable audio playback
- **Configurable Logging**: Rotating log files with adjustable verbosity

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
- `boto3` (for AWS Polly support)

## Installation

### Quick Install (Recommended)

Install grafl with a single command:

```bash
curl -sS https://raw.githubusercontent.com/gabepsilva/grafl/refs/heads/master/install.sh | sh
```

Or if you prefer to review the script first:

```bash
curl -sS https://raw.githubusercontent.com/gabepsilva/grafl/refs/heads/master/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

Install from a different branch:

```bash
# Using environment variable
GRAFL_BRANCH=develop curl -sS https://raw.githubusercontent.com/gabepsilva/grafl/refs/heads/master/install.sh | sh

# Using command-line argument (after downloading script)
curl -sS https://raw.githubusercontent.com/gabepsilva/grafl/refs/heads/master/install.sh -o install.sh
chmod +x install.sh
./install.sh --branch develop
```

### Installation Options

```bash
# Standard installation
./install.sh

# Reinstall (removes existing installation)
./install.sh --reinstall

# Skip voice model download
./install.sh --no-models

# Install from specific branch
./install.sh --branch develop

# Use custom repository and branch
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
- Configuration files at `~/.config/grafl/`
- Log files at `~/.local/share/grafl/logs/`
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

# Download voice models (optional, for Piper)
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

### In-App Settings

While the grafl window is open, click the **☰** (hamburger menu) button to access:
- **Voice Provider**: Switch between Piper (local) and AWS Polly (cloud)
- **Log Level**: Adjust logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Settings are saved automatically and persist across sessions.

## Configuration

### Configuration File

grafl stores user preferences in `~/.config/grafl/config.json`:

```json
{
  "voice_provider": "piper",
  "log_level": "INFO"
}
```

| Setting | Values | Default | Description |
|---------|--------|---------|-------------|
| `voice_provider` | `piper`, `polly` | `piper` | TTS engine to use |
| `log_level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` | Logging verbosity |

### Voice Providers

#### Piper TTS (Default)

Piper is a local, offline TTS engine. No internet connection or API keys required.

**Model Location**: grafl looks for voice models in:
1. `~/.local/share/grafl/models/` (user installation)
2. Project root directory (development)

Models are automatically downloaded during installation. To add more voices:
1. Download from [Piper Voices](https://huggingface.co/rhasspy/piper-voices)
2. Place `.onnx` and `.onnx.json` files in `~/.local/share/grafl/models/`

#### AWS Polly

AWS Polly provides high-quality cloud-based neural voices. Requires AWS credentials.

**Setting up AWS Credentials:**

1. **Environment Variables** (recommended for temporary use):
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_REGION="us-east-1"  # optional, defaults to us-east-1
   ```

2. **AWS Credentials File** (recommended for persistent use):
   ```bash
   # Create credentials file
   mkdir -p ~/.aws
   cat > ~/.aws/credentials << EOF
   [default]
   aws_access_key_id = your-access-key
   aws_secret_access_key = your-secret-key
   EOF

   # Optionally set region in config file
   cat > ~/.aws/config << EOF
   [default]
   region = us-east-1
   EOF
   ```

3. **Using AWS Profiles**:
   ```bash
   # Set a specific profile
   export AWS_PROFILE=my-profile
   ```

**Credential Priority** (checked in order):
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. Shared credentials file (`~/.aws/credentials`)

**IAM Permissions Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "polly:SynthesizeSpeech",
      "Resource": "*"
    }
  ]
}
```

**Automatic Fallback**: If AWS Polly is not configured or unavailable, grafl automatically falls back to Piper TTS.

### Logging

grafl writes logs to `~/.local/share/grafl/logs/grafl.log` with automatic rotation.

**Log Settings:**
- **Max file size**: 10 MB
- **Backup files**: 5 (grafl.log.1, grafl.log.2, etc.)
- **Format**: `2025-01-05 12:34:56 [INFO    ] module:line - message`

**Log Levels:**
| Level | Value | Description |
|-------|-------|-------------|
| DEBUG | 10 | Detailed diagnostic information |
| INFO | 20 | General operational messages (default) |
| WARNING | 30 | Something unexpected but not critical |
| ERROR | 40 | A serious problem occurred |
| CRITICAL | 50 | The application may not continue |

**Viewing Logs:**
```bash
# View recent logs
tail -f ~/.local/share/grafl/logs/grafl.log

# View with less
less ~/.local/share/grafl/logs/grafl.log
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAFL_HOME` | Override installation directory | `~/.local/share/grafl` |
| `GDK_BACKEND` | GTK backend (`wayland` or `x11`) | Auto-detected |
| `AWS_ACCESS_KEY_ID` | AWS access key for Polly | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for Polly | - |
| `AWS_REGION` | AWS region for Polly | `us-east-1` |
| `AWS_DEFAULT_REGION` | Alternative region variable | `us-east-1` |
| `AWS_PROFILE` | AWS credentials profile name | `default` |

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

**For Piper:**
1. Ensure voice models are downloaded to `~/.local/share/grafl/models/`
2. Verify the `piper` binary is available in the virtual environment
3. Check that model files have `.onnx` and `.onnx.json` extensions

**For AWS Polly:**
1. Verify AWS credentials are configured (see [AWS Polly](#aws-polly) section)
2. Check that `boto3` is installed: `pip install boto3`
3. Ensure your IAM user has `polly:SynthesizeSpeech` permission
4. Check logs for detailed error messages: `~/.local/share/grafl/logs/grafl.log`

### "AWS Polly not available" / Fallback to Piper

This means AWS credentials are missing or invalid. grafl will automatically use Piper instead. To use Polly:
1. Configure AWS credentials (see [AWS Polly](#aws-polly) section)
2. Select "AWS Polly" from the in-app menu

### PATH Issues

If `grafl` command is not found, add `~/.local/bin` to your PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

### Debugging

Enable debug logging to see detailed information:

1. **Via in-app menu**: Click ☰ → Set Log Level to "10 - DEBUG"
2. **Via config file**: Edit `~/.config/grafl/config.json`:
   ```json
   {
     "log_level": "DEBUG"
   }
   ```

Then check logs at `~/.local/share/grafl/logs/grafl.log`.

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
