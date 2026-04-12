#!/usr/bin/env python3
"""
Sync all spaces/ subdirectories to HuggingFace Hub.
Generates requirements.txt (and packages.txt where needed) for each Space before uploading.

Usage:
    python scripts/sync_spaces.py --version 0.2.0
    python scripts/sync_spaces.py --version 0.2.0 --space assgen.audio.sfx.generate
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

REPO_ROOT = Path(__file__).parent.parent
SPACES_DIR = REPO_ROOT / "spaces"

# Spaces that need audiocraft (not on PyPI — requires git install).
# NOTE: The four original audio generation spaces now use transformers directly
# (MusicgenForConditionalGeneration / AudiogenForConditionalGeneration) so they
# no longer need audiocraft.  Only add a space here if it truly imports audiocraft.
AUDIOCRAFT_SPACES: set[str] = set()

# Spaces that are CPU-only (no ZeroGPU needed)
CPU_SPACES = {
    "assgen.procedural.terrain.heightmap",
    "assgen.mesh.validate",
    "assgen.mesh.convert",
    "assgen.mesh.bounds",
    "assgen.mesh.center",
    "assgen.mesh.scale",
    "assgen.mesh.flipnormals",
    "assgen.mesh.weld",
    "assgen.mesh.merge",
    "assgen.texture.pbr",
    "assgen.texture.channel_pack",
    "assgen.texture.atlas_pack",
    "assgen.texture.mipmap",
    "assgen.texture.normalmap_convert",
    "assgen.texture.seamless",
    "assgen.texture.resize",
    "assgen.texture.report",
    "assgen.texture.convert",
    "assgen.audio.process.normalize",
    "assgen.audio.process.trim_silence",
    "assgen.audio.process.convert",
    "assgen.audio.process.downmix",
    "assgen.audio.process.resample",
    "assgen.audio.process.loop_optimize",
    "assgen.audio.process.waveform",
    "assgen.procedural.level.dungeon",
    "assgen.procedural.texture.noise",
    "assgen.procedural.level.voronoi",
    "assgen.procedural.foliage.scatter",
    "assgen.procedural.plant.lsystem",
    "assgen.procedural.tileset.wfc",
    "assgen.scene.physics.collider",
    "assgen.lod.generate",
    "assgen.uv.auto",
    "assgen.sprite.pack",
    "assgen.vfx.particle",
    "assgen.narrative.dialogue.validate",
    "assgen.narrative.quest.validate",
}

# Spaces that need ffmpeg apt package
FFMPEG_SPACES = {
    "assgen.audio.process.convert",
    "assgen.audio.process.downmix",
    "assgen.audio.process.normalize",
    "assgen.audio.process.resample",
    "assgen.audio.process.trim_silence",
    "assgen.audio.process.loop_optimize",
    "assgen.audio.process.waveform",
}

# Per-Space extra pip packages (beyond assgen[spaces]).
# Heavy or fragile packages are listed here rather than in the [spaces] extra
# so a broken package only breaks the one Space that needs it, not all of them.
EXTRA_PIP: dict[str, list[str]] = {
    # Real-ESRGAN upscaling — basicsr conflicts with torchvision>=0.16 on some builds
    "assgen.texture.upscale": [
        "opencv-python-headless>=4.9",
        "basicsr>=1.4.2",
        "realesrgan>=0.3.0",
    ],
    # Coqui TTS — large dependency tree (~1.5 GB), only needed for voice spaces
    "assgen.audio.voice.tts": ["TTS>=0.22"],
    "assgen.audio.voice.clone": ["TTS>=0.22"],
    # LOD generation — pyfqmr is a C extension, build may fail on some platforms
    "assgen.lod.generate": ["pyfqmr>=0.2"],
    # UV unwrapping — xatlas Python bindings
    "assgen.uv.auto": ["xatlas>=0.0.9"],
    # TripoSR — image-to-3D (git install, not on PyPI)
    "assgen.model.splat": [
        "tsr @ git+https://github.com/VAST-AI-Research/TripoSR.git",
        "rembg>=2.0.57",
    ],
    # AnimateDiff needs imageio for GIF/MP4 export
    "assgen.animate.keyframe": [
        "imageio>=2.34.0",
        "imageio-ffmpeg>=0.4.9",
    ],
    # UI mockup uses ControlNet auxiliary preprocessors
    "assgen.ui.mockup": ["controlnet-aux>=0.0.7"],
}


def make_requirements(space_name: str, version: str) -> str:
    """Generate requirements.txt content for a Space."""
    lines = [f"assgen[spaces]=={version}"]
    if space_name in AUDIOCRAFT_SPACES:
        lines.append(
            "audiocraft @ git+https://github.com/facebookresearch/audiocraft.git"
        )
    lines.extend(EXTRA_PIP.get(space_name, []))
    return "\n".join(lines) + "\n"


def make_packages_txt(space_name: str) -> str | None:
    """Generate packages.txt for apt dependencies (if needed)."""
    if space_name in FFMPEG_SPACES:
        return "ffmpeg\n"
    return None


def get_hf_username(api: HfApi) -> str:
    """Return the authenticated HF username."""
    return api.whoami()["name"]


def sync_space(space_name: str, version: str, hf_username: str, api: HfApi) -> None:
    space_dir = SPACES_DIR / space_name
    if not space_dir.exists():
        print(f"  SKIP  {space_name} (directory not found)")
        return

    repo_id = f"{hf_username}/{space_name}"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Copy app.py and README.md
        shutil.copy(space_dir / "app.py", tmp_path / "app.py")
        shutil.copy(space_dir / "README.md", tmp_path / "README.md")

        # Generate requirements.txt
        (tmp_path / "requirements.txt").write_text(
            make_requirements(space_name, version)
        )

        # Generate packages.txt if needed
        pkgs = make_packages_txt(space_name)
        if pkgs:
            (tmp_path / "packages.txt").write_text(pkgs)

        # Push to HF Hub via stable Python API
        try:
            api.upload_folder(
                folder_path=str(tmp_path),
                repo_id=repo_id,
                repo_type="space",
                commit_message=f"assgen {version}",
            )
            print(f"  OK    {space_name}")
        except Exception as exc:
            print(f"  ERROR {space_name}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync assgen Spaces to HuggingFace Hub")
    parser.add_argument("--version", required=True, help="assgen version tag, e.g. v0.2.0")
    parser.add_argument("--space", help="sync only this space (for manual use)")
    args = parser.parse_args()

    version = args.version.lstrip("v")  # strip leading 'v' for pip version string

    if args.space:
        spaces_to_sync = [args.space]
    else:
        spaces_to_sync = sorted(
            d.name for d in SPACES_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

    api = HfApi()
    hf_username = get_hf_username(api)
    print(f"Syncing {len(spaces_to_sync)} space(s) — assgen {version} → {hf_username}")
    for space_name in spaces_to_sync:
        sync_space(space_name, version, hf_username, api)

    print("Done.")


if __name__ == "__main__":
    main()
