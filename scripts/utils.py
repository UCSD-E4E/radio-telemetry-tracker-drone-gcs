"""Shared utility functions for build and development scripts."""

import logging
import platform
import shutil
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NPM_CMD = "npm.cmd" if platform.system() == "Windows" else "npm"

ALLOWED_COMMANDS = {
    NPM_CMD: ["install", "run", "build"],
}


def validate_command(cmd: list[str]) -> bool:
    """Ensure the command is in the allowed list for security reasons."""
    if not cmd:
        return False
    program = cmd[0]
    return program in ALLOWED_COMMANDS and all(arg in ALLOWED_COMMANDS[program] for arg in cmd[1:])


def _install_frontend_dependencies(frontend_dir: Path) -> None:
    """Install frontend dependencies using npm."""
    install_cmd = [NPM_CMD, "install"]
    if not validate_command(install_cmd):
        msg = "Invalid or disallowed command for installing frontend dependencies."
        raise ValueError(msg)

    logger.info("Installing frontend dependencies...")
    result = subprocess.run(install_cmd, cwd=frontend_dir, check=True, capture_output=True, text=True)  # noqa: S603
    if result.stdout:
        logger.info("npm install output:\n%s", result.stdout)
    if result.stderr:
        logger.warning("npm install warnings/errors:\n%s", result.stderr)


def _build_frontend_dist(frontend_dir: Path) -> None:
    """Build the frontend using npm."""
    build_cmd = [NPM_CMD, "run", "build"]
    if not validate_command(build_cmd):
        msg = "Invalid or disallowed command for building frontend."
        raise ValueError(msg)

    logger.info("Building frontend...")
    result = subprocess.run(build_cmd, cwd=frontend_dir, check=True, capture_output=True, text=True)  # noqa: S603
    if result.stdout:
        logger.info("npm build output:\n%s", result.stdout)
    if result.stderr:
        logger.warning("npm build warnings/errors:\n%s", result.stderr)


def _copy_frontend_to_package(frontend_dir: Path, package_dist: Path) -> Path:
    """Copy built frontend to package directory."""
    dist_dir = frontend_dir / "dist"
    if not dist_dir.exists() or not any(dist_dir.iterdir()):
        msg = "Frontend build did not produce any output files"
        raise RuntimeError(msg)

    # Copy to package directory
    if package_dist.exists():
        shutil.rmtree(package_dist)
    shutil.copytree(dist_dir, package_dist)

    logger.info("Frontend build copied to package at: %s", package_dist)
    return package_dist


def build_frontend() -> Path:
    """Build the frontend using npm and copy to package directory.

    Returns:
        Path: The path to the copied frontend dist directory
    """
    frontend_dir = Path(__file__).parent.parent / "frontend"
    package_dist = Path(__file__).parent.parent / "radio_telemetry_tracker_drone_gcs" / "frontend_dist"

    logger.info("Building frontend in %s...", frontend_dir)

    _install_frontend_dependencies(frontend_dir)
    _build_frontend_dist(frontend_dir)
    return _copy_frontend_to_package(frontend_dir, package_dist)
