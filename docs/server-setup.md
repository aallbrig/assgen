# Remote Server Setup

Running the `assgen-server` on a dedicated GPU workstation lets you submit jobs
from any machine on your network while keeping heavy inference off your laptop.

---

## Quick Start (Linux)

On the GPU machine:

```bash
pip install "assgen[inference]"
assgen server config set host "0.0.0.0"   # accept LAN connections
assgen server config set device cuda
assgen-server start --daemon
```

On the client machine (laptop):

```bash
pip install assgen
assgen client config set-server http://192.168.1.50:8432
assgen client config show    # verify health check passes

# Pre-download recommended models (~25 GB)
assgen models install --recommended
```

---

## Quick Start (Windows)

On your Windows desktop with an NVIDIA GPU:

### 1. Install Python and CUDA

1. Install [Python 3.11+](https://python.org/downloads/) (check "Add to PATH")
2. Install [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-downloads) matching your GPU driver
3. Verify CUDA is available:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
# Should print: True
```

### 2. Install assgen with inference extras

```powershell
# Create a virtual environment
python -m venv C:\assgen-venv
C:\assgen-venv\Scripts\activate

# Install with CUDA-enabled PyTorch first, then assgen
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install "assgen[inference]"
```

### 3. Configure and start the server

```powershell
# Accept connections from your LAN
assgen server config set host "0.0.0.0"
assgen server config set device cuda

# Start the server
assgen-server start

# Pre-download recommended models (~25 GB)
assgen models install --recommended
```

### 4. Allow through Windows Firewall

```powershell
# Run PowerShell as Administrator
New-NetFirewallRule -DisplayName "assgen-server" `
    -Direction Inbound -Protocol TCP -LocalPort 8432 `
    -Action Allow -Profile Private
```

Or via the GUI: **Windows Defender Firewall** > **Advanced Settings** >
**Inbound Rules** > **New Rule** > Port 8432 > Allow > Private network only.

### 5. Run as a background service (optional)

Use [NSSM](https://nssm.cc/) (Non-Sucking Service Manager) to run assgen as a Windows service:

```powershell
# Download nssm and place it in PATH, then:
nssm install assgen-server C:\assgen-venv\Scripts\assgen-server.exe start
nssm set assgen-server AppParameters "--host 0.0.0.0"
nssm set assgen-server AppEnvironmentExtra "ASSGEN_DEVICE=cuda"
nssm start assgen-server
```

Or use **Task Scheduler**: create a task that runs at logon with action
`C:\assgen-venv\Scripts\assgen-server.exe start`.

### Windows troubleshooting

| Issue | Fix |
|---|---|
| `torch.cuda.is_available()` returns False | Reinstall PyTorch with the correct CUDA version: `pip install torch --index-url https://download.pytorch.org/whl/cu121` |
| Port 8432 blocked | Add Windows Firewall rule (see above) or temporarily disable firewall to test |
| Antivirus quarantines model files | Add `%LOCALAPPDATA%\assgen` to your antivirus exclusions |
| `assgen-server` not found after pip install | Ensure the venv Scripts dir is on PATH, or use full path: `C:\assgen-venv\Scripts\assgen-server.exe` |
| Server crashes on large models | Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512` environment variable |

---

## Running as a systemd Service (Linux)

Create `/etc/systemd/system/assgen-server.service`:

```ini
[Unit]
Description=assgen inference server
After=network.target

[Service]
Type=simple
User=youruser
ExecStart=/home/youruser/.venv/bin/assgen-server start \
    --host 0.0.0.0 --port 8432
Restart=on-failure
RestartSec=5

# --- GPU / CUDA environment ---
Environment=ASSGEN_LOG_LEVEL=INFO
# Prevents CUDA from re-initialising the GPU on every restart
Environment=CUDA_MODULE_LOADING=LAZY
# Reduces fragmentation when loading large models sequentially
Environment=PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
# Pin to a specific GPU if you have more than one (0-indexed)
# Environment=CUDA_VISIBLE_DEVICES=0

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now assgen-server
sudo journalctl -u assgen-server -f
```

### NVIDIA CUDA persistence (recommended for gaming GPUs)

Without persistence mode the driver re-initialises the GPU on every request,
adding 5–15 s to the first job after an idle period.  Enable it once at boot:

```bash
# Add to /etc/rc.local or a separate oneshot systemd unit:
nvidia-smi -pm 1          # persistence mode ON
nvidia-smi --auto-boost-default=0   # disable boost to keep clocks stable
```

Or as its own systemd unit (`/etc/systemd/system/nvidia-persist.service`):

```ini
[Unit]
Description=NVIDIA persistence mode
Before=assgen-server.service

[Service]
Type=oneshot
ExecStart=/usr/bin/nvidia-smi -pm 1
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

### Model pre-warm on startup

The first job after a server restart downloads and loads models, which can
take minutes.  Add a pre-warm step that loads your most-used models before
serving any requests:

```bash
# /home/youruser/assgen-prewarm.sh
#!/bin/bash
set -e
# Wait for the server to be ready
sleep 5
assgen client config set server_url "http://localhost:8432"
# Enqueue lightweight warm-up jobs (they complete quickly and prime the cache)
assgen gen audio sfx generate "test" --wait --timeout 120 || true
echo "assgen server warmed up"
```

Add to the service unit:

```ini
ExecStartPost=/home/youruser/assgen-prewarm.sh
```

### Multi-GPU: assigning specific tasks to specific GPUs

Run two server instances on different ports, each pinned to a different GPU:

```bash
# GPU 0 — visual / 3D tasks
CUDA_VISIBLE_DEVICES=0 assgen-server start --host 127.0.0.1 --port 8432 --daemon

# GPU 1 — audio / narrative tasks
CUDA_VISIBLE_DEVICES=1 assgen-server start --host 127.0.0.1 --port 8743 --daemon
```

Then in client scripts route by job type:

```bash
assgen client config set server_url "http://localhost:8432"
assgen gen visual model create "sword" --wait

assgen client config set server_url "http://localhost:8743"
assgen gen audio music compose "battle theme" --wait
```

---

## API Key Authentication

By default the server has no authentication.  When binding to `0.0.0.0` on a
LAN, you should enable API key auth to prevent unauthorized access.

### Enable on the server

```bash
# Generate a random key and save it
assgen server config set api_key "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# Restart the server for the change to take effect
assgen-server stop && assgen-server start --daemon
```

Or set it directly in `~/.config/assgen/server.yaml`:

```yaml
api_key: "your-secret-key-here"
```

### Configure the client

```bash
# Option 1: environment variable
export ASSGEN_API_KEY="your-secret-key-here"

# Option 2: client config file (~/.config/assgen/client.yaml)
# Add: api_key: "your-secret-key-here"
```

The `/health`, `/docs`, `/redoc`, and `/openapi.json` endpoints are always
accessible without authentication.

---

## Firewall

The server listens on TCP 8432 by default.

```bash
# UFW
sudo ufw allow from 192.168.1.0/24 to any port 8432

# iptables
sudo iptables -A INPUT -p tcp --dport 8432 -s 192.168.1.0/24 -j ACCEPT
```

!!! warning "Do not expose port 8432 to the public internet."
    Enable [API key authentication](#api-key-authentication) when binding to
    `0.0.0.0`.  Use a VPN or SSH tunnel for remote access outside your LAN.

---

## SSH Tunnel (remote access)

```bash
# On the client machine:
ssh -N -L 8432:localhost:8432 user@gpu-machine &
assgen client config set server_url "http://localhost:8432"
```

---

## Hardware Guide

| GPU | VRAM | Notes |
|-----|------|-------|
| RTX 4070 | 12 GB | Excellent for image-to-3D, audio, texturing |
| RTX 3090 | 24 GB | Runs larger music/video models comfortably |
| RTX 4090 | 24 GB | Fastest single-GPU option |
| A100 40 GB | 40 GB | Production-grade; full models without quantisation |

Enable `fp16` inference where the handler supports it by adding to `server.yaml`:

```yaml
device: cuda
# handlers read this key
inference_dtype: float16
```
