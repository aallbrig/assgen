"""assgen.narrative.lore.generate — HuggingFace Space
Generate game world lore entries from topic descriptions using Phi-3.5.
CLI equivalent: assgen gen support narrative lore generate
"""
from __future__ import annotations

from pathlib import Path

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run

LORE_TYPES = ["History", "Faction", "Location", "Artifact", "Myth/Legend", "Religion"]


@spaces.GPU
def generate_lore(topic: str, lore_type: str, word_count: int) -> str:
    full_topic = f"{lore_type}: {topic}" if lore_type else topic
    result = run(
        "narrative.lore.generate",
        {"topic": full_topic, "length": word_count},
        device="cuda",
    )
    txt_files = [f for f in result["files"] if f.endswith(".txt")]
    if txt_files:
        return Path(txt_files[0]).read_text(encoding="utf-8")
    return result.get("metadata", {}).get("text", "(no output)")


EXAMPLES = [
    ["a steampunk empire in perpetual smog", "History", 200],
    ["the Order of the Silver Flame", "Faction", 200],
    ["the Sunken City of Valdris", "Location", 200],
    ["the Obsidian Crown of the Fallen King", "Artifact", 150],
]

with gr.Blocks(title="assgen · Lore Generator") as demo:
    gr.Markdown(
        "# assgen · Lore Generator\n"
        "Generate rich game world lore entries from text descriptions using Phi-3.5-mini. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — generation takes 15–30 s on first run (model cold start)._"
    )
    with gr.Row():
        with gr.Column():
            topic = gr.Textbox(label="World/Setting Description",
                               placeholder="a steampunk empire in perpetual smog", lines=3)
            lore_type = gr.Dropdown(label="Lore Type", choices=LORE_TYPES, value="History")
            word_count = gr.Slider(label="Target Word Count",
                                   minimum=100, maximum=400, value=200, step=50)
            btn = gr.Button("Generate Lore", variant="primary")
        with gr.Column():
            output = gr.Textbox(label="Generated Lore", lines=20, max_lines=30)
    gr.Examples(EXAMPLES, inputs=[topic, lore_type, word_count], cache_examples=False)
    btn.click(fn=generate_lore, inputs=[topic, lore_type, word_count], outputs=output)

demo.launch()
