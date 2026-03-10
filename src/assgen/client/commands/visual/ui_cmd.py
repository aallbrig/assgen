"""assgen visual ui — UI/HUD elements and 2D overlays.

  assgen visual ui icon      generate icons and sprites
  assgen visual ui hud       health bars, minimaps, meters
  assgen visual ui overlay   2D canvas elements for 3D games
  assgen visual ui button    styled buttons and controls
  assgen visual ui panel     dialog boxes, frames, panel chrome
  assgen visual ui widget    sliders, toggles, checkboxes, progress bars
  assgen visual ui mockup    full-screen UI mockups and wireframe renders
  assgen visual ui layout    grid-based HUD and menu layout compositions
  assgen visual ui iconset   themed icon packs with style consistency
  assgen visual ui theme     coordinated UI theme kit (icons+buttons+panels)
  assgen visual ui screen    complete game screen compositions
"""
from __future__ import annotations
from typing import Optional
import typer
from assgen.client.commands.submit import submit_job

app = typer.Typer(help="UI icons, HUD elements, and 2D overlays.", no_args_is_help=True)

_WAIT_OPT = typer.Option(None, "--wait/--no-wait", help="Block until the job completes and stream live progress")
_OUT_OPT  = typer.Option(None, "--output", "-o", help="Output file or directory path")
_STYLE_OPT = typer.Option(None, "--style", help="Visual style hint, e.g. 'flat', 'pixel-art', 'gothic'")
_STEPS_OPT = typer.Option(25, "--steps", help="Inference steps (quality vs. speed)")


@app.command("icon")
def ui_icon(
    prompt: str = typer.Argument(..., help="Icon description, e.g. 'crossed swords inventory icon'"),
    size: int = typer.Option(256, "--size", "-s", help="Icon size in pixels"),
    style: Optional[str] = _STYLE_OPT,
    count: int = typer.Option(1, "--count", "-n", help="Number of variants to generate"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate game UI icons or inventory sprites."""
    submit_job("visual.ui.icon", {
        "prompt": prompt,
        "size": size,
        "style": style,
        "count": count,
        "output": output,
    }, wait=wait)


@app.command("hud")
def ui_hud(
    prompt: str = typer.Argument(..., help="HUD element description, e.g. 'health bar sci-fi'"),
    width: int = typer.Option(512, "--width"),
    height: int = typer.Option(128, "--height"),
    style: Optional[str] = _STYLE_OPT,
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate HUD elements (health bars, minimaps, meters)."""
    submit_job("visual.ui.icon", {
        "mode": "hud",
        "prompt": prompt,
        "width": width,
        "height": height,
        "style": style,
        "output": output,
    }, wait=wait)


@app.command("overlay")
def ui_overlay(
    prompt: str = typer.Argument(..., help="Overlay description"),
    width: int = typer.Option(1920, "--width"),
    height: int = typer.Option(1080, "--height"),
    transparent: bool = typer.Option(True, "--transparent/--opaque"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a 2D overlay for a 3D game canvas."""
    submit_job("visual.ui.icon", {
        "mode": "overlay",
        "prompt": prompt,
        "width": width,
        "height": height,
        "transparent": transparent,
        "output": output,
    }, wait=wait)


@app.command("button")
def ui_button(
    prompt: str = typer.Argument(..., help="Button description, e.g. 'medieval stone START button'"),
    style: Optional[str] = _STYLE_OPT,
    width: int = typer.Option(256, "--width"),
    height: int = typer.Option(128, "--height"),
    states: Optional[str] = typer.Option(
        "normal", "--states",
        help="Comma-separated state variants: normal,hover,pressed,disabled,focused,selected,locked",
    ),
    nine_slice: str = typer.Option(
        "off", "--nine-slice",
        help="'auto' → emit .meta.json sidecar with 9-slice inset margins; 'off' to skip",
    ),
    nine_slice_inset: Optional[int] = typer.Option(
        None, "--nine-slice-inset",
        help="Override 9-slice border inset in px (default: ~16%% of shortest edge)",
    ),
    dpi: str = typer.Option(
        "1x", "--dpi",
        help="Comma-separated DPI scale variants to output, e.g. '1x,2x,3x'",
    ),
    greyscale_base: bool = typer.Option(
        False, "--greyscale-base/--no-greyscale-base",
        help="Output greyscale+alpha so the engine can tint at runtime",
    ),
    steps: int = _STEPS_OPT,
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate styled game buttons with state variants, DPI scales, and optional 9-slice metadata.

    State choices: normal, hover, pressed, disabled, focused, selected, locked

    Examples:
        assgen gen visual ui button "stone RPG button" --states normal,hover,pressed --wait
        assgen gen visual ui button "sci-fi button" --nine-slice auto --dpi 1x,2x --wait
        assgen gen visual ui button "fantasy button" --greyscale-base --states normal,disabled --wait
    """
    submit_job("visual.ui.button", {
        "prompt": prompt,
        "style": style,
        "width": width,
        "height": height,
        "states": [s.strip() for s in states.split(",") if s.strip()],
        "nine_slice": nine_slice,
        "nine_slice_inset": nine_slice_inset,
        "dpi": dpi,
        "greyscale_base": greyscale_base,
        "steps": steps,
        "output": output,
    }, wait=wait)


@app.command("panel")
def ui_panel(
    prompt: str = typer.Argument(..., help="Panel description, e.g. 'gothic stone dialog frame'"),
    panel_type: str = typer.Option("dialog", "--type", "-t", help="dialog|inventory|tooltip|frame|border"),
    style: Optional[str] = _STYLE_OPT,
    width: int = typer.Option(512, "--width"),
    height: int = typer.Option(256, "--height"),
    steps: int = _STEPS_OPT,
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate dialog boxes, inventory frames, and panel chrome."""
    submit_job("visual.ui.panel", {
        "prompt": prompt,
        "panel_type": panel_type,
        "style": style,
        "width": width,
        "height": height,
        "steps": steps,
        "output": output,
    }, wait=wait)


@app.command("widget")
def ui_widget(
    prompt: str = typer.Argument(..., help="Widget description, e.g. 'fantasy scroll health bar'"),
    widget_type: str = typer.Option("slider", "--type", "-t", help="slider|toggle|checkbox|progressbar|spinner|radio|knob"),
    style: Optional[str] = _STYLE_OPT,
    width: int = typer.Option(320, "--width"),
    height: int = typer.Option(64, "--height"),
    steps: int = _STEPS_OPT,
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate individual UI controls (sliders, toggles, checkboxes, progress bars)."""
    submit_job("visual.ui.widget", {
        "prompt": prompt,
        "widget_type": widget_type,
        "style": style,
        "width": width,
        "height": height,
        "steps": steps,
        "output": output,
    }, wait=wait)


@app.command("mockup")
def ui_mockup(
    prompt: str = typer.Argument(..., help="Screen description, e.g. 'fantasy RPG main menu dark castle'"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Path to sketch/wireframe reference image"),
    width: int = typer.Option(1280, "--width"),
    height: int = typer.Option(720, "--height"),
    controlnet_scale: float = typer.Option(0.8, "--cn-scale", help="ControlNet strength (0.0–1.0)"),
    steps: int = typer.Option(30, "--steps"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate full-screen UI mockups, optionally guided by a sketch reference.

    Examples:
        assgen gen visual ui mockup "dark fantasy RPG main menu" --wait
        assgen gen visual ui mockup "sci-fi HUD" --reference wireframe.png --wait
    """
    submit_job("visual.ui.mockup", {
        "prompt": prompt,
        "reference": reference,
        "width": width,
        "height": height,
        "controlnet_scale": controlnet_scale,
        "steps": steps,
        "output": output,
    }, wait=wait)


@app.command("layout")
def ui_layout(
    prompt: str = typer.Argument(..., help="Layout description, e.g. 'sci-fi HUD minimap top-right, health bottom-left'"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Path to layout sketch or depth reference"),
    width: int = typer.Option(1280, "--width"),
    height: int = typer.Option(720, "--height"),
    controlnet_scale: float = typer.Option(0.7, "--cn-scale"),
    steps: int = typer.Option(30, "--steps"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate grid-based HUD and menu layout compositions.

    Examples:
        assgen gen visual ui layout "medieval RPG inventory grid, 6x4 item slots" --wait
        assgen gen visual ui layout "space game HUD" --reference grid_sketch.png --wait
    """
    submit_job("visual.ui.layout", {
        "prompt": prompt,
        "reference": reference,
        "width": width,
        "height": height,
        "controlnet_scale": controlnet_scale,
        "steps": steps,
        "output": output,
    }, wait=wait)


@app.command("iconset")
def ui_iconset(
    prompt: str = typer.Argument(..., help="Icon theme, e.g. 'fantasy RPG inventory icons'"),
    icon_names: Optional[str] = typer.Option(
        None, "--icons",
        help="Comma-separated icon names, e.g. 'sword,shield,potion,key'",
    ),
    style_image: Optional[str] = typer.Option(None, "--style-image", help="Reference icon for style consistency"),
    count: int = typer.Option(8, "--count", "-n", help="Number of icons (when --icons not specified)"),
    size: int = typer.Option(128, "--size", "-s", help="Icon size in pixels (square)"),
    steps: int = _STEPS_OPT,
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a themed icon pack with visual consistency across all icons.

    Examples:
        assgen gen visual ui iconset "fantasy RPG" --icons "sword,shield,potion,map,key" --wait
        assgen gen visual ui iconset "sci-fi HUD" --count 12 --style-image ref_icon.png --wait
    """
    submit_job("visual.ui.iconset", {
        "prompt": prompt,
        "icon_names": icon_names,
        "style_image": style_image,
        "count": count,
        "size": size,
        "steps": steps,
    }, wait=wait)


@app.command("theme")
def ui_theme(
    prompt: str = typer.Argument(..., help="Theme description, e.g. 'dark souls gothic stone medieval'"),
    style_image: str = typer.Argument(..., help="Reference image that defines the visual style"),
    elements: Optional[str] = typer.Option(
        None, "--elements",
        help="Comma-separated elements to generate: icon,button,panel,widget (default: all)",
    ),
    ip_adapter_scale: float = typer.Option(0.65, "--ip-scale", help="Style influence (0.0–1.0)"),
    steps: int = typer.Option(30, "--steps"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a coordinated UI theme kit (icons + buttons + panels) from a style reference.

    Examples:
        assgen gen visual ui theme "dark souls gothic stone" style_ref.png --wait
        assgen gen visual ui theme "pixel art retro" ref.png --elements "icon,button" --wait
    """
    submit_job("visual.ui.theme", {
        "prompt": prompt,
        "style_image": style_image,
        "elements": elements,
        "ip_adapter_scale": ip_adapter_scale,
        "steps": steps,
        "output": output,
    }, wait=wait)


@app.command("screen")
def ui_screen(
    prompt: str = typer.Argument(..., help="Screen description, e.g. 'fantasy RPG combat with health bars and minimap'"),
    screen_type: str = typer.Option("gameplay", "--type", "-t", help="gameplay|mainmenu|pause|inventory|loading|cutscene"),
    width: int = typer.Option(1920, "--width"),
    height: int = typer.Option(1080, "--height"),
    steps: int = typer.Option(35, "--steps"),
    guidance_scale: float = typer.Option(7.5, "--guidance"),
    output: Optional[str] = _OUT_OPT,
    wait: Optional[bool] = _WAIT_OPT,
) -> None:
    """Generate a complete game screen composition at full resolution.

    Examples:
        assgen gen visual ui screen "fantasy RPG combat HUD" --type gameplay --wait
        assgen gen visual ui screen "space game main menu" --type mainmenu --wait
    """
    submit_job("visual.ui.screen", {
        "prompt": prompt,
        "screen_type": screen_type,
        "width": width,
        "height": height,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "output": output,
    }, wait=wait)
