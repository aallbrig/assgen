"""assgen.narrative.dialogue.npc — HuggingFace Space
Generate NPC dialogue using Phi-3.5-mini-instruct.
CLI equivalent: assgen gen support narrative dialogue npc
"""
from __future__ import annotations

import json

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run

TONES = ["Friendly", "Gruff", "Mysterious", "Terrified",
         "Arrogant", "Wise", "Comedic", "Sinister"]


@spaces.GPU
def generate_dialogue(persona: str, player_text: str,
                      tone: str, max_lines: int) -> str:
    if not persona.strip() or not player_text.strip():
        raise gr.Error("Please fill in both the NPC description and player text.")
    # Fold "tone" into the character description — the handler has no "tone" param key.
    character = f"{persona.strip()} (tone: {tone.lower()})"
    result = run(
        "narrative.dialogue.npc",
        # Handler keys: "character" (not "persona"), "context" (not "player_text"),
        # "lines" (not "max_lines").
        {"character": character, "context": player_text, "lines": max_lines},
        device="cuda",
    )
    # Dialogue content is in the JSON output file, not in metadata.
    with open(result["files"][0]) as fh:
        data = json.load(fh)
    lines_data = data.get("lines", [])
    if lines_data and isinstance(lines_data, list):
        return "\n".join(entry.get("text", "") for entry in lines_data)
    return data.get("raw", "(no dialogue generated)")


EXAMPLES = [
    ["Old blacksmith, weathered hands, no-nonsense attitude", "Do you sell swords?", "Gruff", 2],
    ["Secretive mage who knows where the artifact is hidden", "Where is the artifact?", "Mysterious", 2],
    ["Terrified peasant who just saw a monster attack", "What happened here?", "Terrified", 3],
    ["Wise elder who has survived three wars", "Is there hope for our village?", "Wise", 2],
]

with gr.Blocks(title="assgen · NPC Dialogue Generator") as demo:
    gr.Markdown(
        "# 💬 assgen · NPC Dialogue Generator\n"
        "Generate in-character NPC dialogue using Phi-3.5-mini. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — may queue briefly during high traffic._"
    )
    with gr.Row():
        with gr.Column():
            persona = gr.Textbox(label="NPC Persona / Description", lines=3,
                                 placeholder="Old blacksmith, weathered hands, no-nonsense")
            player = gr.Textbox(label="Player Says", lines=2,
                                placeholder="Do you sell swords?")
            with gr.Row():
                tone = gr.Dropdown(label="NPC Tone", choices=TONES, value="Gruff")
                lines = gr.Slider(label="Max Lines", minimum=1, maximum=4, value=2, step=1)
            btn = gr.Button("Generate Dialogue", variant="primary")
        with gr.Column():
            dialogue = gr.Textbox(label="Generated Dialogue", lines=8, interactive=False)
    gr.Examples(EXAMPLES, inputs=[persona, player, tone, lines], cache_examples=False)
    btn.click(fn=generate_dialogue, inputs=[persona, player, tone, lines], outputs=dialogue)

demo.launch()
