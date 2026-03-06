# API Reference

All public Python APIs in `assgen` are documented here, auto-generated from
source-code docstrings using [mkdocstrings](https://mkdocstrings.github.io/).
Every function, class, and attribute shown below includes its type signature,
parameter descriptions, and return/raises information derived directly from the
code — no separate doc-maintenance required.

---

## Catalog

Job-type → HuggingFace model ID mapping.  Users can override entries in
`~/.config/assgen/models.yaml`.

::: assgen.catalog
    options:
      members:
        - load_catalog
        - get_model_for_job
        - all_job_types
        - all_model_ids

---

## Database

SQLite persistence layer for jobs, models, and usage records.

::: assgen.db
    options:
      members:
        - JobStatus
        - get_connection
        - transaction
        - init_db
        - create_job
        - get_job
        - list_jobs
        - update_job_status
        - reset_stale_running_jobs
        - upsert_model
        - record_model_usage

---

## Configuration

Platform-aware config directory resolution and YAML load/save helpers.

::: assgen.config
    options:
      members:
        - get_config_dir
        - get_db_path
        - get_models_cache_dir
        - load_server_config
        - save_server_config
        - load_client_config
        - save_client_config

---

## Server — Model Manager

Downloads, caches, and tracks HuggingFace models on the server side.

::: assgen.server.model_manager
    options:
      members:
        - ModelManager
        - detect_device

---

## Server — Validation

Allow-list enforcement and model↔task compatibility checks.

::: assgen.server.validation
    options:
      members:
        - TASK_COMPATIBLE_TAGS
        - check_allow_list
        - fetch_hf_pipeline_tag
        - validate_model_task_compatibility
        - validate_job_model

---

## Version

::: assgen.version
    options:
      members:
        - get_version_info
        - format_version_string
