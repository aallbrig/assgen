# Model Validation

`assgen` validates model–task compatibility at **job-submission time** before
any model is downloaded.  There are two independent checks:

1. **Allow-list** — the server admin can restrict which models may be used.
2. **Pipeline-tag check** — verifies the HuggingFace `pipeline_tag` is sensible
   for the requested task (e.g. an audio model can't generate 3D meshes).

Both checks are fast: they hit the lightweight HF Hub REST API with no ML
dependencies and no GPU involvement.

---

## Allow-List

Set `allow_list` in `server.yaml` to a non-empty list to restrict models:

```yaml
allow_list:
  - "stabilityai/TripoSR"
  - "cvssp/audioldm2"
  - "facebook/musicgen-medium"
```

Any job submitted with a `--model-id` not on this list is rejected with HTTP
422 **before** any download is attempted.  An empty list (the default) allows
all models.

```bash
# Add a model to the allow-list
assgen server config set allow_list '["stabilityai/TripoSR","cvssp/audioldm2"]'

# Check current list
assgen server config show
```

---

## Pipeline-Tag Compatibility

When `skip_model_validation: false` (the default), the server queries:

```
https://huggingface.co/api/models/{model_id}?fields=pipeline_tag
```

It then checks whether the returned `pipeline_tag` (e.g. `text-to-audio`) is
in the allowable set for the requested catalog task (e.g. `music-generation`
allows `text-to-audio`, `audio-generation`, `music-generation`).

The full task → allowed-tags map lives in
[`assgen.server.validation.TASK_COMPATIBLE_TAGS`](api-reference.md#server-validation).

### Failure example

```bash
$ assgen visual model create --prompt "sword" --model-id "cvssp/audioldm2"
Error 422: Model 'cvssp/audioldm2' has pipeline_tag='text-to-audio'
which is not compatible with task 'image-to-3d'.
Expected one of: ['image-to-3d', 'text-to-3d'].
Set skip_model_validation: true in server.yaml to override.
```

### Disabling the check

```bash
assgen server config set skip_model_validation true
```

!!! warning
    `allow_list` is **always** enforced even when `skip_model_validation: true`.
    Disabling tag-checking does not bypass the allow-list.

### Offline / unreachable HF Hub

If the HF Hub API cannot be reached, the pipeline-tag check is **skipped and
the job is allowed**.  This keeps the tool usable in air-gapped environments.
The allow-list check (which is purely local) still runs.

---

## Validation Flow

```
POST /jobs
  │
  ├─ model_id provided? ──No──► use catalog default
  │
  ├─ check_allow_list()  ──Fail──► 422 ValueError
  │
  ├─ skip_model_validation? ──Yes──► enqueue job
  │
  ├─ fetch_hf_pipeline_tag()  ──None (offline)──► enqueue job
  │
  └─ pipeline_tag ∈ compatible_tags? ──No──► 422 ValueError
       │
       └─ Yes ──► enqueue job
```
