"""Handler for narrative.lore.generate — world-building lore via Phi-3.5 Mini.

Requires ``transformers`` and ``torch``:
    pip install transformers accelerate torch
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline as hf_pipeline
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False


ProgressCallback = Callable[[float, str], None]

_DEFAULT_MODEL = "microsoft/Phi-3.5-mini-instruct"

_FORMATS = {
    "prose":             "flowing narrative prose",
    "codex":             "a codex entry with a title, body, and 'Known to Scholars' sidebar",
    "item-description":  "a game item description with name, flavour text, and stats block",
    "quest":             "a quest description with objectives, backstory, and rewards",
}


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate world-building lore text in the requested format."""
    if not _TRANSFORMERS_AVAILABLE:
        raise RuntimeError(
            "transformers is not installed.  "
            "Run: pip install transformers accelerate"
        )

    topic: str = params.get("topic") or params.get("prompt") or "world lore"
    word_count: int = int(params.get("length", 500))
    fmt: str = params.get("format", "prose")
    fmt_desc = _FORMATS.get(fmt, "prose")

    # Incorporate any upstream context (from --from-job or --context flags)
    context_map: dict[str, str] = params.get("context_map") or {}
    context_section = ""
    if context_map:
        context_section = "\n\nUse the following world context to ensure consistency:\n"
        for key, text in context_map.items():
            context_section += f"\n--- {key} ---\n{text[:2000]}\n"

    system_prompt = (
        f"You are a creative writer for a video game. "
        f"Write approximately {word_count} words of lore about: {topic}. "
        f"Format it as {fmt_desc}.{context_section}"
        f"\nOnly output the lore text itself — no meta-commentary."
    )

    progress_cb(0.25, "Loading Phi-3.5 Mini Instruct…")
    load_from = model_path or model_id or _DEFAULT_MODEL
    tokenizer = AutoTokenizer.from_pretrained(load_from, trust_remote_code=True)
    model_obj = AutoModelForCausalLM.from_pretrained(
        load_from,
        device_map=device,
        torch_dtype="auto",
        trust_remote_code=True,
    )

    progress_cb(0.55, "Generating lore…")
    pipe = hf_pipeline("text-generation", model=model_obj, tokenizer=tokenizer)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Write lore about: {topic}"},
    ]
    outputs = pipe(messages, max_new_tokens=min(word_count * 2, 2048), do_sample=True, temperature=0.85)
    generated = outputs[0]["generated_text"]
    if isinstance(generated, list):
        lore_text: str = generated[-1].get("content", "")
    else:
        lore_text = str(generated)

    progress_cb(0.90, "Writing lore.txt…")
    out_file = output_dir / "lore.txt"
    out_file.write_text(lore_text.strip(), encoding="utf-8")

    # Also write a JSON envelope for machine chaining
    meta_file = output_dir / "lore.json"
    meta_file.write_text(
        json.dumps({"topic": topic, "format": fmt, "text": lore_text.strip()}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    progress_cb(1.0, "Lore generation complete")
    return {
        "files": ["lore.txt", "lore.json"],
        "metadata": {
            "model_id": model_id or _DEFAULT_MODEL,
            "topic": topic,
            "format": fmt,
            "approx_words": len(lore_text.split()),
        },
    }
