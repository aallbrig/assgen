"""Handler for narrative.dialogue.npc — NPC dialogue generation via Phi-3.5 Mini.

Requires ``transformers`` and ``torch``:
    pip install transformers torch

Falls back to the stub handler if transformers is not installed.
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

_SYSTEM_TEMPLATE = """\
You are {character}, an NPC in a video game.
{context_block}
Generate {lines} lines of in-character dialogue{branching_note}.
Format your response as a JSON object with this structure:
{{
  "npc": "{character}",
  "lines": [
    {{"id": 1, "text": "...", "emotion": "neutral"}},
    ...
  ]{player_options_block}
}}
Only output valid JSON — no markdown, no code fences, no extra text."""

_BRANCHING_EXTRA = """\
,
  "player_options": [
    {{"id": "A", "text": "...", "leads_to_line": 1}},
    {{"id": "B", "text": "...", "leads_to_line": 2}}
  ]"""


def run(
    job_type: str,
    params: dict[str, Any],
    model_id: str | None,
    model_path: str | None,
    device: str,
    progress_cb: ProgressCallback,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate NPC dialogue as a structured JSON dialogue tree."""
    if not _TRANSFORMERS_AVAILABLE:
        raise RuntimeError(
            "transformers is not installed.  "
            "Run: pip install transformers accelerate"
        )

    character: str = params.get("character") or "Generic NPC"
    context: str = params.get("context") or ""
    lines: int = max(1, int(params.get("lines", 10)))
    branching: bool = bool(params.get("branching", False))

    context_block = f"Scene context: {context}" if context else ""
    # Incorporate any --context named slots (lore, scenario, world, etc.)
    context_map: dict[str, str] = params.get("context_map") or {}
    if context_map:
        context_block += "\n\nWorld/scenario reference material:\n"
        for key, text in context_map.items():
            context_block += f"\n--- {key} ---\n{text[:2000]}\n"
    branching_note = " as a branching dialogue tree" if branching else ""
    player_options_block = _BRANCHING_EXTRA if branching else ""

    system_prompt = _SYSTEM_TEMPLATE.format(
        character=character,
        context_block=context_block,
        lines=lines,
        branching_note=branching_note,
        player_options_block=player_options_block,
    )

    progress_cb(0.25, "Loading Phi-3.5 Mini Instruct…")
    load_from = model_path or model_id or _DEFAULT_MODEL
    tokenizer = AutoTokenizer.from_pretrained(load_from, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        load_from,
        device_map=device,
        torch_dtype="auto",
        trust_remote_code=True,
    )

    progress_cb(0.55, "Generating NPC dialogue…")
    pipe = hf_pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Generate dialogue for {character}."},
    ]
    outputs = pipe(messages, max_new_tokens=1024, do_sample=True, temperature=0.8)
    generated = outputs[0]["generated_text"]
    # `generated_text` from the pipeline is the full message list; grab the last assistant turn
    if isinstance(generated, list):
        raw_text: str = generated[-1].get("content", "")
    else:
        raw_text = str(generated)

    progress_cb(0.85, "Parsing and validating dialogue JSON…")
    # Extract JSON — the model may wrap it in markdown fences despite instructions
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```", 2)[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.rstrip("`").strip()

    try:
        dialogue_data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback: store raw text so the user gets something useful
        dialogue_data = {"npc": character, "raw": raw_text, "parse_error": True}

    progress_cb(0.92, "Writing dialogue.json…")
    out_file = output_dir / "dialogue.json"
    out_file.write_text(json.dumps(dialogue_data, indent=2, ensure_ascii=False), encoding="utf-8")

    progress_cb(1.0, "Dialogue generation complete")
    return {
        "files": [out_file.name],
        "metadata": {
            "model_id": model_id or _DEFAULT_MODEL,
            "character": character,
            "lines": lines,
            "branching": branching,
            "parse_error": dialogue_data.get("parse_error", False),
        },
    }
