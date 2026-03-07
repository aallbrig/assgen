"""Mesh post-processing utilities for game-ready output.

Applied after any handler that produces a triangle mesh (.glb / .ply / .obj).
Uses ``trimesh`` (listed under the ``inference`` optional-dependency group).

Typical pipeline
----------------
1. ``fill_holes``   — patch open boundaries so the mesh is watertight
2. ``fix_normals``  — unify winding order and flip inverted face normals
3. ``decimate``     — quadric-error simplification to a target face count

All functions operate in-place on the provided *path* and return the same
path so they can be chained or called independently.
"""
from __future__ import annotations

import logging
from pathlib import Path

import trimesh  # intentional module-level: ImportError if not installed

logger = logging.getLogger(__name__)

# Face counts that produce reasonable results for common game asset LODs.
DEFAULT_TARGET_FACES = 10_000
HIGH_LOD_FACES = 30_000
LOW_LOD_FACES = 2_000


def clean_mesh(
    path: Path,
    target_faces: int = DEFAULT_TARGET_FACES,
    *,
    fill_holes: bool = True,
    fix_normals: bool = True,
    decimate: bool = True,
) -> Path:
    """Load *path*, post-process, overwrite, and return *path*.

    Args:
        path: Local path to a mesh file (.glb / .ply / .obj / .stl).
        target_faces: Maximum triangle count after decimation.  Meshes
            already at or below this count are not modified.
        fill_holes: Patch open-boundary loops (makes mesh watertight).
        fix_normals: Unify winding order and flip degenerate normals.
        decimate: Simplify to *target_faces* via quadric-error metric.

    Returns:
        The same *path* after in-place overwrite.

    Raises:
        ValueError: If the file could not be interpreted as a triangle mesh.
    """
    logger.info("Post-processing mesh", extra={"path": str(path), "target_faces": target_faces})

    mesh = trimesh.load(str(path), force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        # Scene with multiple meshes — concatenate into one
        if isinstance(mesh, trimesh.Scene) and mesh.geometry:
            mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
        else:
            raise ValueError(f"Could not load a triangle mesh from {path}")

    original_faces = len(mesh.faces)
    logger.debug("Loaded mesh", extra={"faces": original_faces, "vertices": len(mesh.vertices)})

    if fill_holes:
        trimesh.repair.fill_holes(mesh)
        logger.debug("Filled holes", extra={"faces_after": len(mesh.faces)})

    if fix_normals:
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fix_winding(mesh)
        logger.debug("Fixed normals")

    if decimate and len(mesh.faces) > target_faces:
        mesh = mesh.simplify_quadric_decimation(target_faces)
        logger.debug(
            "Decimated mesh",
            extra={"faces_before": original_faces, "faces_after": len(mesh.faces)},
        )

    mesh.export(str(path))
    logger.info(
        "Mesh post-processing complete",
        extra={
            "path": str(path),
            "faces_in": original_faces,
            "faces_out": len(mesh.faces),
        },
    )
    return path


def mesh_stats(path: Path) -> dict:
    """Return a lightweight summary dict for a mesh file (no post-processing)."""
    mesh = trimesh.load(str(path), force="mesh")
    if isinstance(mesh, trimesh.Scene) and mesh.geometry:
        mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        return {}
    return {
        "faces": len(mesh.faces),
        "vertices": len(mesh.vertices),
        "watertight": bool(mesh.is_watertight),
        "volume": float(mesh.volume) if mesh.is_watertight else None,
        "bounds": mesh.bounds.tolist(),
    }
