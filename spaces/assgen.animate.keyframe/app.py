"""assgen.animate.keyframe — HuggingFace Space
Generate animation clips from text prompts using AnimateDiff.
CLI equivalent: assgen gen visual animate keyframe
"""
from __future__ import annotations

try:
    import spaces; spaces.GPU  # AttributeError if wrong package
except (ImportError, AttributeError):
    import types
    spaces = types.SimpleNamespace(GPU=lambda fn: fn)

import gradio as gr
from assgen.sdk import run


@spaces.GPU
def generate_keyframe(prompt: str, num_frames: int, guidance: float, seed: int) -> str:
    result = run(
        "visual.animate.keyframe",
        {
            "prompt": prompt,
            "num_frames": num_frames,
            "guidance_scale": guidance,
            "seed": seed if seed >= 0 else None,
            "format": "gif",
        },
        device="cuda",
    )
    return result["files"][0]


EXAMPLES = [
    ["a warrior swinging a sword, side view, game animation", 16, 7.5, 42],
    ["a mage casting a fireball spell, hands glowing", 16, 7.5, 123],
    ["a knight running and jumping, armor glinting", 16, 7.5, 456],
    ["a dragon flapping its wings slowly", 16, 7.5, 789],
]

with gr.Blocks(title="assgen · Keyframe Animation Generator") as demo:
    gr.Markdown(
        "# assgen · Keyframe Animation Generator\n"
        "Generate animated GIFs from text prompts using AnimateDiff. "
        "Powered by [AnimateDiff](https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2). "
        "Part of the [assgen](https://github.com/aallbrig/assgen) pipeline.\n\n"
        "_ZeroGPU — generates 16-frame animation clips as GIF._"
    )
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Animation Description", lines=3,
                                placeholder="a warrior swinging a sword, side view, game animation")
            with gr.Row():
                num_frames = gr.Slider(label="Frames", minimum=8, maximum=16, value=16, step=8)
                guidance = gr.Slider(label="Guidance Scale", minimum=5.0, maximum=12.0,
                                     value=7.5, step=0.5)
            seed = gr.Number(label="Seed (-1 = random)", value=42, precision=0)
            btn = gr.Button("Generate Animation", variant="primary")
        with gr.Column():
            video = gr.Image(label="Animation (GIF)", type="filepath")
    gr.Examples(EXAMPLES, inputs=[prompt, num_frames, guidance, seed], cache_examples=False)
    btn.click(fn=generate_keyframe, inputs=[prompt, num_frames, guidance, seed], outputs=video)

demo.launch()
