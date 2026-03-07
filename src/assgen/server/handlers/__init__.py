"""Job handler modules.

Each module must expose a ``run(job_type, params, model_id, model_path,
device, progress_cb, output_dir)`` callable.  The worker imports handler
modules dynamically: ``assgen.server.handlers.<job_type_dots_to_underscores>``.
A module-level ``ImportError`` (e.g. missing optional inference deps) causes
the worker to fall back to the generic stub handler automatically.
"""
