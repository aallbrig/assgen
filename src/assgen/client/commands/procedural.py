"""assgen gen procedural — procedural generation tools.

  assgen gen procedural terrain heightmap   Perlin/fractal/ridged heightmap
  assgen gen procedural texture noise       tileable noise texture
  assgen gen procedural level dungeon       BSP/cellular dungeon layout
  assgen gen procedural level voronoi       Voronoi region map
  assgen gen procedural foliage scatter     Poisson disk foliage scatter
  assgen gen procedural tileset wfc         Wave Function Collapse tileset
  assgen gen procedural plant lsystem       L-system plant skeleton
"""
from __future__ import annotations

import typer

from assgen.client.commands.submit import submit_job

# ── terrain sub-app ──────────────────────────────────────────────────────────
terrain_app = typer.Typer(help="Procedural terrain heightmap generation.")


@terrain_app.command("heightmap")
def terrain_heightmap(
    width: int  = typer.Option(512, "--width",   "-W"),
    height: int = typer.Option(512, "--height",  "-H"),
    type: str   = typer.Option("fractal", "--type", "-t",
                               help="perlin | fractal | ridged"),
    seed: int   = typer.Option(42,  "--seed",    "-s"),
    scale: float = typer.Option(100.0, "--scale"),
    octaves: int = typer.Option(6, "--octaves"),
    output: str | None = typer.Option(None, "--output", "-o"),
    wait: bool | None  = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate a procedural heightmap PNG (Perlin/fractal/ridged noise)."""
    submit_job("procedural.terrain.heightmap", {
        "width": width, "height": height, "type": type,
        "seed": seed, "scale": scale, "octaves": octaves, "output": output,
    }, wait=wait)


# ── texture sub-app ──────────────────────────────────────────────────────────
texture_app = typer.Typer(help="Procedural noise texture generation.")


@texture_app.command("noise")
def texture_noise(
    width:      int   = typer.Option(512,   "--width",      "-W"),
    height:     int   = typer.Option(512,   "--height",     "-H"),
    noise_type: str   = typer.Option("fbm", "--noise-type", "-n",
                                     help="perlin | voronoi | fbm"),
    seed:       int   = typer.Option(42,    "--seed",       "-s"),
    scale:      float = typer.Option(100.0, "--scale"),
    octaves:    int   = typer.Option(6,     "--octaves"),
    output: str | None = typer.Option(None, "--output", "-o"),
    wait: bool | None  = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate a tileable noise texture PNG (Perlin/Voronoi/fBm)."""
    submit_job("procedural.texture.noise", {
        "width": width, "height": height, "noise_type": noise_type,
        "seed": seed, "scale": scale, "octaves": octaves, "output": output,
    }, wait=wait)


# ── level sub-app ────────────────────────────────────────────────────────────
level_app = typer.Typer(help="Procedural level layout generation.")


@level_app.command("dungeon")
def level_dungeon(
    width:     int = typer.Option(64,    "--width",     "-W"),
    height:    int = typer.Option(64,    "--height",    "-H"),
    rooms:     int = typer.Option(10,    "--rooms",     "-r"),
    algorithm: str = typer.Option("bsp", "--algorithm", "-a",
                                   help="bsp | cellular"),
    seed:      int = typer.Option(42,    "--seed",      "-s"),
    output: str | None = typer.Option(None, "--output", "-o"),
    wait: bool | None  = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate a BSP or cellular-automata dungeon layout."""
    submit_job("procedural.level.dungeon", {
        "width": width, "height": height, "rooms": rooms,
        "algorithm": algorithm, "seed": seed, "output": output,
    }, wait=wait)


@level_app.command("voronoi")
def level_voronoi(
    width:   int = typer.Option(512, "--width",   "-W"),
    height:  int = typer.Option(512, "--height",  "-H"),
    regions: int = typer.Option(12,  "--regions", "-r"),
    seed:    int = typer.Option(42,  "--seed",    "-s"),
    output: str | None = typer.Option(None, "--output", "-o"),
    wait: bool | None  = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate a Voronoi region map (colour PNG + regions JSON)."""
    submit_job("procedural.level.voronoi", {
        "width": width, "height": height, "regions": regions,
        "seed": seed, "output": output,
    }, wait=wait)


# ── foliage sub-app ──────────────────────────────────────────────────────────
foliage_app = typer.Typer(help="Procedural foliage and object scatter.")


@foliage_app.command("scatter")
def foliage_scatter(
    density_map: str   = typer.Argument(..., help="Greyscale density map image"),
    count:       int   = typer.Option(100, "--count",    "-n"),
    min_dist:    float = typer.Option(1.0, "--min-dist", "-d"),
    seed:        int   = typer.Option(42,  "--seed",     "-s"),
    output: str | None = typer.Option(None, "--output", "-o"),
    wait: bool | None  = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Scatter foliage instances using Poisson disk sampling on a density map."""
    submit_job("procedural.foliage.scatter", {
        "density_map": density_map, "count": count,
        "min_dist": min_dist, "seed": seed, "output": output,
    }, wait=wait)


# ── tileset sub-app ──────────────────────────────────────────────────────────
tileset_app = typer.Typer(help="Procedural tileset synthesis.")


@tileset_app.command("wfc")
def tileset_wfc(
    sample:    str = typer.Argument(..., help="Sample tileset image"),
    width:     int = typer.Option(20, "--width",     "-W"),
    height:    int = typer.Option(20, "--height",    "-H"),
    tile_size: int = typer.Option(16, "--tile-size", "-t"),
    seed:      int = typer.Option(42, "--seed",      "-s"),
    output: str | None = typer.Option(None, "--output", "-o"),
    wait: bool | None  = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Synthesise a new tileset using Wave Function Collapse from a sample image."""
    submit_job("procedural.tileset.wfc", {
        "sample": sample, "width": width, "height": height,
        "tile_size": tile_size, "seed": seed, "output": output,
    }, wait=wait)


# ── plant sub-app ────────────────────────────────────────────────────────────
plant_app = typer.Typer(help="Procedural plant and vegetation generation.")


@plant_app.command("lsystem")
def plant_lsystem(
    axiom:      str   = typer.Option("F",                   "--axiom",      "-a"),
    rules:      str   = typer.Option('{"F":"F[+F]F[-F]F"}', "--rules",      "-r",
                                      help="JSON mapping symbol→replacement"),
    iterations: int   = typer.Option(4,    "--iterations", "-i"),
    angle:      float = typer.Option(25.0, "--angle",      "-g",
                                      help="Turn angle in degrees"),
    step:       float = typer.Option(10.0, "--step",       "-s",
                                      help="Segment length in pixels"),
    output: str | None = typer.Option(None, "--output", "-o"),
    wait: bool | None  = typer.Option(None, "--wait/--no-wait"),
) -> None:
    """Generate an L-system plant skeleton (SVG + branches JSON)."""
    submit_job("procedural.plant.lsystem", {
        "axiom": axiom, "rules": rules, "iterations": iterations,
        "angle": angle, "step": step, "output": output,
    }, wait=wait)


# ── top-level proc app ────────────────────────────────────────────────────────
app = typer.Typer(
    name="procedural",
    help="Procedural generation: terrain, textures, levels, foliage, tilesets, plants.",
    no_args_is_help=True,
)
app.add_typer(terrain_app, name="terrain", help="Procedural terrain heightmaps")
app.add_typer(texture_app, name="texture", help="Procedural noise textures")
app.add_typer(level_app,   name="level",   help="Procedural level layouts (dungeon, Voronoi)")
app.add_typer(foliage_app, name="foliage", help="Foliage and object scatter")
app.add_typer(tileset_app, name="tileset", help="Wave Function Collapse tileset synthesis")
app.add_typer(plant_app,   name="plant",   help="L-system plant skeleton generation")
