#!/bin/bash
# Download Piper TTS voice models
# These files are not tracked in git due to their size

echo "Downloading Piper TTS voice model files..."

# Download the ONNX model file
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx

# Download the ONNX model config/metadata
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

echo "Model files downloaded successfully!"

