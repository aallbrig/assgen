# Configuration

`assgen` uses plain YAML files stored under `~/.config/assgen/`.  All settings
have sane defaults so the tool works out-of-the-box without any manual
configuration.

---

## Files

| File | Who reads it | Purpose |
|------|--------------|---------|
| `~/.config/assgen/server.yaml` | `assgen-server` | Server behaviour, model allow-list |
| `~/.config/assgen/client.yaml` | `assgen` (client) | Server URL, output preferences |
| `~/.config/assgen/models.yaml` | Both | Override the built-in model catalog |

---

## server.yaml

```yaml
host: "127.0.0.1"      # Listen address
port: 8742             # TCP port
device: "auto"         # auto | cuda | mps | cpu
log_level: "INFO"

# If non-empty, only these model IDs can be downloaded/used.
# Empty list = allow everything.
allow_list: []

# Set true to skip the HuggingFace pipeline-tag compatibility check.
# The allow_list is ALWAYS enforced regardless of this setting.
skip_model_validation: false
```

Manage with:

```bash
assgen server config show
assgen server config set allow_list '["stabilityai/TripoSR"]'
assgen server config set skip_model_validation true
```

---

## client.yaml

```yaml
server_url: null       # null = auto-start a local server
output_dir: "."        # Default output directory for generated files
```

Manage with:

```bash
assgen client config show
assgen client config set server_url "http://192.168.1.50:8742"
```

Setting `server_url` to a remote address means the client will never
auto-start a local server — useful when your GPU workstation runs the server
and you submit jobs from a laptop.

---

## models.yaml — User Catalog Overrides

Override any built-in model mapping by adding entries under the `catalog:` key:

```yaml
catalog:
  visual.model.create:
    model_id: "my-org/my-custom-triposr"
    name: "Custom TripoSR Fine-tune"
    task: "image-to-3d"
  audio.sfx.generate:
    model_id: "facebook/audiogen-large"
    name: "AudioGen Large"
    task: "text-to-audio"
```

Keys must exactly match a built-in job type (run `assgen tasks` for the full
list).  After editing, restart the server — the catalog is loaded at startup.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ASSGEN_CONFIG_DIR` | `~/.config/assgen` | Override the config directory |
| `ASSGEN_DATA_DIR` | `~/.local/share/assgen` | Override the model cache root |
| `ASSGEN_SERVER_URL` | *(from client.yaml)* | Runtime server URL override |
| `ASSGEN_LOG_LEVEL` | `INFO` | Logging verbosity |
