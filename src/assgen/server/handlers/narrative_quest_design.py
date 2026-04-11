"""Handler for narrative.quest.design — quest/scenario writing via Phi-3.5 Mini.

Requires ``transformers`` and ``torch``:
    pip install transformers accelerate torch
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers import pipeline as hf_pipeline
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    _TRANSFORMERS_AVAILABLE = False


ProgressCallback = Callable[[float, str], None]

_DEFAULT_MODEL = "microsoft/Phi-3.5-mini-instruct"

_SYSTEM_TEMPLATE = """\
You are a game designer writing a quest for a video game.

Topic / premise: {topic}
{context_section}
Generate a complete quest design document in JSON with this structure:
{{
  "title": "Quest name",
  "type": "{quest_type}",
  "premise": "One-sentence hook",
  "backstory": "2–3 sentences of world context",
  "objectives": [
    {{"id": 1, "description": "...", "optional": false}}
  ],
  "npcs": [
    {{"name": "...", "role": "..."}}
  ],
  "rewards": {{"experience": 0, "items": [], "story_impact": "..."}},
  "dialogue_hooks": ["NPC line 1", "NPC line 2"]
}}
Only output valid JSON — no markdown fences, no extra text."""


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate a structured quest design document."""
    if not _TRANSFORMERS_AVAILABLE:
        raise RuntimeError(
            "transformers is not installed.  "
            "Run: pip install transformers accelerate"
        )

    topic: str = params.get("topic") or params.get("description") or params.get("prompt") or "side quest"
    quest_type: str = params.get("quest_type", "side-quest")

    context_map: dict[str, str] = params.get("context_map") or {}
    context_section = ""
    if context_map:
        context_section = "\nUse the following world/scenario context:\n"
        for key, text in context_map.items():
            context_section += f"\n--- {key} ---\n{text[:2000]}\n"

    system_prompt = _SYSTEM_TEMPLATE.format(
        topic=topic,
        quest_type=quest_type,
        context_section=context_section,
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

    progress_cb(0.55, "Designing quest…")
    pipe = hf_pipeline("text-generation", model=model_obj, tokenizer=tokenizer)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": f"Design a {quest_type} about: {topic}"},
    ]
    outputs = pipe(messages, max_new_tokens=1500, do_sample=True, temperature=0.75)
    generated = outputs[0]["generated_text"]
    if isinstance(generated, list):
        raw_text: str = generated[-1].get("content", "")
    else:
        raw_text = str(generated)

    # Strip markdown fences if present
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```", 2)[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.rstrip("`").strip()

    progress_cb(0.88, "Parsing quest JSON…")
    try:
        quest_data = json.loads(raw_text)
    except json.JSONDecodeError:
        quest_data = {"topic": topic, "raw": raw_text, "parse_error": True}

    progress_cb(0.93, "Writing quest.json…")
    out_file = output_dir / "quest.json"
    out_file.write_text(json.dumps(quest_data, indent=2, ensure_ascii=False), encoding="utf-8")

    progress_cb(1.0, "Quest design complete")
    return {
        "files": [out_file.name],
        "metadata": {
            "model_id": model_id or _DEFAULT_MODEL,
            "topic": topic,
            "quest_type": quest_type,
            "parse_error": quest_data.get("parse_error", False),
        },
    }
