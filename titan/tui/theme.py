"""TITAN TUI theme definitions.

All colors and style constants live here. No hardcoded colors elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThemeColors:
    """Color palette for a single theme."""

    bg: str = "#1a1a2e"
    bg_sidebar: str = "#16213e"
    bg_header: str = "#0f3460"
    bg_status: str = "#1a1a2e"
    bg_active: str = "#0f3460"
    bg_hover: str = "#1a1a3e"

    text: str = "#e0e0e0"
    text_muted: str = "#808080"
    text_header: str = "#ffffff"
    text_active: str = "#ffffff"
    text_dim: str = "#606060"

    primary: str = "#4a9eff"
    success: str = "#4caf50"
    warning: str = "#ff9800"
    error: str = "#f44336"
    info: str = "#2196f3"

    border: str = "#333366"
    border_active: str = "#4a9eff"
    border_dim: str = "#222244"


DARK = ThemeColors()

LIGHT = ThemeColors(
    bg="#ffffff",
    bg_sidebar="#f0f0f5",
    bg_header="#e0e0e8",
    bg_status="#f5f5f5",
    bg_active="#d0d0e0",
    bg_hover="#e8e8f0",
    text="#1a1a1a",
    text_muted="#666666",
    text_header="#000000",
    text_active="#000000",
    text_dim="#999999",
    primary="#0066cc",
    success="#2e7d32",
    warning="#e65100",
    error="#c62828",
    info="#1565c0",
    border="#cccccc",
    border_active="#0066cc",
    border_dim="#dddddd",
)

_DEFAULT_THEME = DARK


def get_theme() -> ThemeColors:
    """Return the current theme. Future: read from config."""
    return _DEFAULT_THEME


def set_theme(theme: ThemeColors) -> None:
    """Set the current theme."""
    global _DEFAULT_THEME
    _DEFAULT_THEME = theme
