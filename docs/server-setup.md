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
Environment=ASSGEN_LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now assgen-server
sudo journalctl -u assgen-server -f
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
