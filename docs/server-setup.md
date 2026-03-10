# Remote Server Setup

Running the `assgen-server` on a dedicated GPU workstation lets you submit jobs
from any machine on your network while keeping heavy inference off your laptop.

---

## Quick Start

On the GPU machine:

```bash
pip install assgen
assgen-server start --host 0.0.0.0 --port 8742
```

On the client machine:

```bash
pip install assgen
assgen client config set server_url "http://192.168.1.50:8742"
assgen jobs list   # confirms connectivity
```

---

## Running as a systemd Service

Create `/etc/systemd/system/assgen-server.service`:

```ini
[Unit]
Description=assgen inference server
After=network.target

[Service]
Type=simple
User=youruser
ExecStart=/home/youruser/.venv/bin/assgen-server start \
    --host 0.0.0.0 --port 8742
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
assgen client config set server_url "http://localhost:8742"
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
CUDA_VISIBLE_DEVICES=0 assgen-server start --host 127.0.0.1 --port 8742 --daemon

# GPU 1 — audio / narrative tasks
CUDA_VISIBLE_DEVICES=1 assgen-server start --host 127.0.0.1 --port 8743 --daemon
```

Then in client scripts route by job type:

```bash
assgen client config set server_url "http://localhost:8742"
assgen gen visual model create "sword" --wait

assgen client config set server_url "http://localhost:8743"
assgen gen audio music compose "battle theme" --wait
```

---

## Firewall

The server listens on TCP 8742 by default.

```bash
# UFW
sudo ufw allow from 192.168.1.0/24 to any port 8742

# iptables
sudo iptables -A INPUT -p tcp --dport 8742 -s 192.168.1.0/24 -j ACCEPT
```

!!! warning "Do not expose port 8742 to the public internet."
    There is no authentication in the current version.  Use a VPN or
    SSH tunnel for remote access outside your LAN.

---

## SSH Tunnel (remote access)

```bash
# On the client machine:
ssh -N -L 8742:localhost:8742 user@gpu-machine &
assgen client config set server_url "http://localhost:8742"
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
