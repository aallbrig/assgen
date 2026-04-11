"""
assgen.<domain>.<command> — HuggingFace Space
<one-line description>

CLI equivalent: assgen gen <domain> <command> [args]
"""
from __future__ import annotations

try:
    import spaces                # pre-installed in HF Spaces environment
except (ImportError, AttributeError):              # running locally — no-op shim
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run

JOB_TYPE = "domain.subdomain.command"   # ← change this


@spaces.GPU   # ← remove this decorator for CPU-only Spaces
def _run(param1: str, param2: float) -> str:
    result = run(JOB_TYPE, {"param1": param1, "param2": param2})
    return result["files"][0]   # or result["files"] for multiple outputs


with gr.Blocks(title="assgen · <Title>") as demo:
    gr.Markdown(
        "# assgen · <Title>\n"
        "<Short description of what this Space demonstrates.>\n"
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline."
    )
    with gr.Row():
        with gr.Column():
            input1 = gr.Textbox(label="Input 1")
            input2 = gr.Slider(minimum=1, maximum=10, value=3, label="Input 2")
            btn = gr.Button("Generate", variant="primary")
        with gr.Column():
            output = gr.Audio(label="Output")   # ← change component type as needed

    btn.click(fn=_run, inputs=[input1, input2], outputs=output)

demo.launch()
