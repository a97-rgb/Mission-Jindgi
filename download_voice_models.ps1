# Run this once in H:\Future\agent-01\ to download the voice model files
# Takes ~2 minutes depending on connection (~80MB total)

cd H:\Future\agent-01

Write-Host "[1/2] downloading kokoro model (~80MB)..."
Invoke-WebRequest `
  -Uri "https://huggingface.co/thewh1teagle/kokoro-onnx/resolve/main/kokoro-v0_19.onnx" `
  -OutFile "kokoro-v0_19.onnx"

Write-Host "[2/2] downloading voices..."
Invoke-WebRequest `
  -Uri "https://huggingface.co/thewh1teagle/kokoro-onnx/resolve/main/voices.bin" `
  -OutFile "voices.bin"

Write-Host "done. Test with: python speak.py"
