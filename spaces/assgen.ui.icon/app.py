"""assgen.ui.icon — HuggingFace Space
Generate game UI icons from text descriptions using SDXL.
CLI equivalent: assgen gen visual ui icon
"""
from __future__ import annotations

try:
    import spaces
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run

ICON_STYLES = ["Fantasy RPG", "Sci-Fi", "Minimalist Flat", "Pixel Art", "Material Design"]


@spaces.GPU
def generate_icon(description: str, style: str, steps: int) -> list:
    result = run(
        "visual.ui.icon",
        {"prompt": description, "style": style, "steps": steps},
        device="cuda",
    )
    return result["files"]


EXAMPLES = [
    ["health potion, red bottle with cork", "Fantasy RPG", 25],
    ["energy shield, blue hexagon, power indicator", "Sci-Fi", 25],
    ["sword skill, glowing blade icon", "Fantasy RPG", 25],
    ["inventory bag, leather satchel", "Minimalist Flat", 25],
]

with gr.Blocks(title="assgen · UI Icon Generator") as demo:
    gr.Markdown(
        "# assgen · UI Icon Generator\n"
        "Generate game UI icons from text descriptions using SDXL. "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — generates icon variants._"
    )
    with gr.Row():
        with gr.Column():
            description = gr.Textbox(label="Icon Description",
                                     placeholder="health potion, red bottle with cork", lines=2)
            style = gr.Dropdown(label="Icon Style", choices=ICON_STYLES, value="Fantasy RPG")
            steps = gr.Slider(label="Steps", minimum=20, maximum=40, value=25, step=5)
            btn = gr.Button("Generate Icons", variant="primary")
        with gr.Column():
            gallery = gr.Gallery(label="Generated Icons", columns=2)
    gr.Examples(EXAMPLES, inputs=[description, style, steps], cache_examples=False)
    btn.click(fn=generate_icon, inputs=[description, style, steps], outputs=gallery)

demo.launch()
