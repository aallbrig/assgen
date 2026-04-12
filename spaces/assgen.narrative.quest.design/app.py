"""assgen.narrative.quest.design — HuggingFace Space
Generate game quest designs from world context using Phi-3.5.
CLI equivalent: assgen gen support narrative quest design
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run

QUEST_TYPES = [
    "Main Story", "Side Quest", "Bounty", "Fetch",
    "Escort", "Investigation", "Boss Hunt",
]


@spaces.GPU
def design_quest(context: str, quest_type: str, num_objectives: int) -> str:
    qt = quest_type.lower().replace(" ", "-")
    result = run(
        "narrative.quest.design",
        {"topic": context, "quest_type": qt, "num_objectives": num_objectives},
        device="cuda",
    )
    json_files = [f for f in result["files"] if f.endswith(".json")]
    if json_files:
        try:
            data = json.loads(Path(json_files[0]).read_text(encoding="utf-8"))
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            return Path(json_files[0]).read_text(encoding="utf-8")
    return str(result.get("metadata", {}))


EXAMPLES = [
    ["a corrupt nobleman hoarding grain during a famine", "Side Quest", 3],
    ["recover a stolen magic tome from a thieves' guild", "Bounty", 4],
    ["investigate disappearances near the old lighthouse", "Investigation", 3],
]

with gr.Blocks(title="assgen · Quest Designer") as demo:
    gr.Markdown(
        "# assgen · Quest Designer\n"
        "Generate structured quest designs with objectives from a world context. "
        "Powered by [Phi-3.5-mini-instruct](https://huggingface.co/microsoft/Phi-3.5-mini-instruct). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — generation takes 15–30 s on first run (model cold start)._"
    )
    with gr.Row():
        with gr.Column():
            context = gr.Textbox(label="Quest Context",
                                 placeholder="a corrupt nobleman hoarding grain during a famine",
                                 lines=3)
            quest_type = gr.Dropdown(label="Quest Type", choices=QUEST_TYPES, value="Side Quest")
            num_objectives = gr.Slider(label="Number of Objectives",
                                       minimum=2, maximum=6, value=3, step=1)
            btn = gr.Button("Design Quest", variant="primary")
        with gr.Column():
            output = gr.Code(label="Quest JSON", language="json", lines=25)
    gr.Examples(EXAMPLES, inputs=[context, quest_type, num_objectives], cache_examples=False)
    btn.click(fn=design_quest, inputs=[context, quest_type, num_objectives], outputs=output)

demo.launch()
