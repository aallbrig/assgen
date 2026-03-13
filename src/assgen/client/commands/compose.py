"""assgen compose — multi-step asset pipeline commands.

Compose commands run a complete, multi-step generation pipeline from a single
command. Each step waits for the previous to complete and passes its output
files into the next step as upstream context — no manual job chaining required.

Available compose pipelines:

  assgen compose npc      Full NPC creation: concept → mesh → rig → animate → texture → export
  assgen compose weapon   Weapon asset: concept → mesh → LOD → texture → collider → export
  assgen compose building Building: blockout → mesh → LOD → texture → collider → navmesh → export

The cost of a compose command equals the sum of its individual steps — there is
no additional inference overhead beyond what you would run manually.
"""
from __future__ import annotations

from typing import Optional

import typer

from assgen.client.output import console

app = typer.Typer(
    help="Multi-step asset pipeline commands (NPC, weapon, building, …).",
    no_args_is_help=True,
)

_ENGINE_OPT = typer.Option("unity", "--engine", help="unity | unreal | godot")
_WAIT_OPT   = typer.Option(True,  "--wait/--no-wait",
                            help="Block until the full pipeline completes (default: on)")
_OUT_OPT    = typer.Option(None, "--output", "-o", help="Output directory")
_QUALITY_OPT = typer.Option("standard", "--quality", "-q", help="draft | standard | high")


# ── NPC ──────────────────────────────────────────────────────────────────────

@app.command("npc")
def compose_npc(
    prompt: str = typer.Argument(
        ...,
        help="Character description, e.g. 'pig shopkeeper with apron, medieval fantasy'",
    ),
    style: Optional[str] = typer.Option(
        None, "--style",
        help="Visual style applied to all generation steps, e.g. 'painterly, warm tones'",
    ),
    voice: Optional[str] = typer.Option(
        None, "--voice",
        help="TTS voice description for NPC dialog lines, e.g. 'gruff male merchant, aged'",
    ),
    animations: str = typer.Option(
        "idle,walk,talk",
        "--animations", "-a",
        help="Comma-separated animation clips to retarget onto the character",
    ),
    skeleton: str = typer.Option(
        "humanoid", "--skeleton",
        help="biped | humanoid (humanoid = Unity-compatible 55-bone naming)",
    ),
    engine: str = _ENGINE_OPT,
    lod: bool = typer.Option(True,  "--lod/--no-lod",     help="Generate LOD 0/1/2 levels"),
    collider: bool = typer.Option(True, "--collider/--no-collider", help="Generate collision mesh"),
    multiview: bool = typer.Option(
        True, "--multiview/--no-multiview",
        help="Use Zero123++ multi-view for better mesh quality (slower)",
    ),
    quality: str = _QUALITY_OPT,
    output: Optional[str] = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run", help="Print pipeline steps without executing"),
) -> None:
    """Generate a complete game NPC from a text description.

    Runs a multi-step pipeline:
      1. Concept art (SDXL)
      2. Multi-view turnaround (Zero123++)  [--no-multiview to skip]
      3. 3D mesh reconstruction (TripoSR)
      4. UV unwrap
      5. Concept-guided texture generation (IP-Adapter)
      6. Auto-rig with humanoid skeleton (UniRig)
      7. Animation retargeting (bundled BVH clips)
      8. LOD levels 0/1/2  [--no-lod to skip]
      9. Collision mesh    [--no-collider to skip]
      10. NPC dialog text generation
      11. Text-to-speech for dialog lines
      12. Engine export

    Examples:
        assgen compose npc "pig shopkeeper with apron, medieval fantasy" --wait
        assgen compose npc "dark elf archer" --style "gritty realistic" --engine unreal --wait
        assgen compose npc "robot guard" --no-multiview --animations idle,walk,attack_light --wait
    """
    style_tag = f", {style}" if style else ""
    full_prompt = f"{prompt}{style_tag}"
    anim_list = [a.strip() for a in animations.split(",") if a.strip()]
    global_params = {"_quality": quality} if quality != "standard" else {}
    if output:
        global_params["output_dir"] = output

    steps: list[dict] = [
        {
            "id": "concept",
            "job_type": "visual.concept.generate",
            "params": {
                "prompt": f"{full_prompt}, character concept art, front view, full body, white background",
                "width": 768, "height": 1024,
            },
        },
    ]

    if multiview:
        steps.append({
            "id": "multiview",
            "job_type": "visual.model.multiview",
            "from_step": "concept",
            "params": {"prompt": full_prompt},
        })
        mesh_from = "multiview"
    else:
        mesh_from = "concept"

    steps += [
        {
            "id": "mesh",
            "job_type": "visual.model.splat",
            "from_step": mesh_from,
            "params": {"prompt": full_prompt},
        },
        {
            "id": "uv",
            "job_type": "visual.uv.auto",
            "from_step": "mesh",
        },
        {
            "id": "texture",
            "job_type": "visual.texture.from_concept",
            "from_step": "uv",
            "params": {
                "prompt": full_prompt,
                "concept_step": "concept",  # hint to handler to look for concept image
            },
        },
        {
            "id": "rig",
            "job_type": "visual.rig.auto",
            "from_step": "mesh",
            "params": {"skeleton": skeleton},
        },
        {
            "id": "animations",
            "job_type": "visual.animate.retarget",
            "from_step": "rig",
            "params": {"clips": anim_list, "skeleton": skeleton},
        },
    ]

    if lod:
        steps.append({
            "id": "lod",
            "job_type": "visual.lod.generate",
            "from_step": "mesh",
            "params": {"levels": 3},
        })

    if collider:
        steps.append({
            "id": "collider",
            "job_type": "scene.physics.collider",
            "from_step": "mesh",
        })

    dialog_prompt = voice or f"{prompt}, NPC merchant greeting the player"
    steps += [
        {
            "id": "dialog",
            "job_type": "narrative.dialogue.npc",
            "params": {
                "prompt": dialog_prompt,
                "character": prompt,
                "line_count": 5,
            },
        },
        {
            "id": "voice",
            "job_type": "audio.voice.tts",
            "from_step": "dialog",
            "params": {"voice": voice or "en_default"},
        },
        {
            "id": "export",
            "job_type": "pipeline.integrate.export",
            "from_step": "mesh",
            "params": {"engine": engine},
        },
    ]

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="NPC")


# ── Weapon ───────────────────────────────────────────────────────────────────

@app.command("weapon")
def compose_weapon(
    prompt: str = typer.Argument(..., help="Weapon description, e.g. 'rusted iron longsword'"),
    style: Optional[str] = typer.Option(None, "--style"),
    engine: str = _ENGINE_OPT,
    lod: bool = typer.Option(True,  "--lod/--no-lod"),
    collider: bool = typer.Option(True, "--collider/--no-collider"),
    quality: str = _QUALITY_OPT,
    output: Optional[str] = _OUT_OPT,
    wait: bool = _WAIT_OPT,
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Generate a complete weapon asset: concept → mesh → LOD → texture → collider → export.

    Examples:
        assgen compose weapon "rusted iron longsword, dark fantasy" --wait
        assgen compose weapon "plasma rifle" --style "sci-fi, chrome" --engine unreal --wait
    """
    style_tag = f", {style}" if style else ""
    full_prompt = f"{prompt}{style_tag}"
    global_params = {"_quality": quality} if quality != "standard" else {}

    steps: list[dict] = [
        {
            "id": "concept",
            "job_type": "visual.concept.generate",
            "params": {
                "prompt": f"{full_prompt}, weapon concept art, isolated on white, side view",
                "width": 1024, "height": 512,
            },
        },
        {
            "id": "mesh",
            "job_type": "visual.model.splat",
            "from_step": "concept",
            "params": {"prompt": full_prompt},
        },
        {
            "id": "uv",
            "job_type": "visual.uv.auto",
            "from_step": "mesh",
        },
        {
            "id": "texture",
            "job_type": "visual.texture.from_concept",
            "from_step": "uv",
            "params": {"prompt": full_prompt},
        },
    ]

    if lod:
        steps.append({"id": "lod", "job_type": "visual.lod.generate",
                       "from_step": "mesh", "params": {"levels": 3}})
    if collider:
        steps.append({"id": "collider", "job_type": "scene.physics.collider",
                       "from_step": "mesh"})

    steps.append({"id": "export", "job_type": "pipeline.integrate.export",
                   "from_step": "mesh", "params": {"engine": engine}})

    _execute_or_dry_run(steps, global_params, dry_run, wait, pipeline_name="Weapon")


# ── Shared execution helper ───────────────────────────────────────────────────

def _execute_or_dry_run(
    steps: list[dict],
    global_params: dict,
    dry_run: bool,
    wait: bool,
    pipeline_name: str,
) -> None:
    if dry_run:
        console.print(f"\n[bold]{pipeline_name} pipeline[/bold]  ({len(steps)} steps, dry-run)\n")
        for step in steps:
            src = f"  ← from [italic]{step['from_step']!r}[/italic]" if step.get("from_step") else ""
            p = step.get("params", {})
            p_str = f"  [dim]{p}[/dim]" if p else ""
            console.print(f"  [cyan]{step['id']:12}[/cyan]  {step['job_type']}{src}{p_str}")
        console.print()
        return

    if not wait:
        console.print(
            "[yellow]Note:[/yellow] compose pipelines always wait for each step — "
            "--no-wait is ignored. Use [italic]assgen pipeline workflow[/italic] for fire-and-forget."
        )

    console.print(f"\n[bold]Starting {pipeline_name} pipeline[/bold]  ({len(steps)} steps)\n")

    from assgen.client.compose import run_pipeline

    def _on_step(step_id: str, status: str, msg: str) -> None:
        icons = {"SUBMITTING": "⏳", "RUNNING": "🔄", "DONE": "✅"}
        icon = icons.get(status, " ")
        console.print(f"  {icon}  [cyan]{step_id:12}[/cyan]  {msg}")

    try:
        results = run_pipeline(steps, global_params=global_params, on_step=_on_step)
        total = len(results)
        console.print(f"\n[green]✓ {pipeline_name} pipeline complete[/green]  ({total} steps)")
    except RuntimeError as exc:
        console.print(f"\n[red]✗ {pipeline_name} pipeline failed:[/red] {exc}", err=True)
        raise typer.Exit(1)
