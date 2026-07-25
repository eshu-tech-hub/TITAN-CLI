from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from titan.config.exceptions import ConfigLoadError


def load_json(path: str | Path) -> dict[str, Any]:
    """Load configuration from a JSON file.

    Raises:
        ConfigLoadError: If the file does not exist or is invalid.
    """
    p = Path(path)
    if not p.is_file():
        raise ConfigLoadError(f"Config file not found: {p}")
    try:
        raw = p.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ConfigLoadError(f"Config file root must be a dict: {p}")
        return data
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"Invalid JSON in {p}: {e}") from e


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load configuration from a YAML file.

    Raises:
        ConfigLoadError: If PyYAML is not installed, file not found,
            or file is invalid.
    """
    p = Path(path)
    if not p.is_file():
        raise ConfigLoadError(f"Config file not found: {p}")
    try:
        import yaml  # type: ignore[import-untyped]
    except ModuleNotFoundError as e:
        raise ConfigLoadError(
            "PyYAML is required to load YAML config files. "
            "Install it with: pip install pyyaml"
        ) from e
    try:
        raw = p.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ConfigLoadError(f"Config file root must be a dict: {p}")
        return data
    except yaml.YAMLError as e:
        raise ConfigLoadError(f"Invalid YAML in {p}: {e}") from e


def load_env(prefix: str = "TITAN") -> dict[str, Any]:
    """Load configuration from environment variables.

    Reads all env vars starting with ``<prefix>_`` and converts
    double-underscore-delimited names into nested dicts.

    Single underscores within a segment are preserved as part of
    the key name.

    Examples::

        TITAN_APP__LOG_LEVEL=DEBUG     → {"app": {"log_level": "DEBUG"}}
        TITAN_RISK__MAX_DRAWDOWN=20.0  → {"risk": {"max_drawdown": 20.0}}
        TITAN_APP__NAME=MyApp          → {"app": {"name": "MyApp"}}
    """
    result: dict[str, Any] = {}
    prefix_upper = prefix.upper() + "_"
    for key, value in sorted(os.environ.items()):
        if not key.startswith(prefix_upper):
            continue
        rest = key[len(prefix_upper) :]
        parts = [p.lower() for p in rest.split("__")]
        _deep_set(result, parts, value)
    return result


def _deep_set(d: dict[str, Any], keys: list[str], value: str) -> None:
    """Set a value at a dotted key path inside a nested dict."""
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = _coerce(value)


def _coerce(value: str) -> Any:
    """Coerce a string to bool/int/float or leave as str."""
    v = value.strip()
    if v.lower() in ("true", "yes", "1"):
        return True
    if v.lower() in ("false", "no", "0"):
        return False
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def merge_sources(*sources: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge multiple configuration dicts.

    Later sources override earlier ones at the key level. Lists
    are replaced, not extended.
    """
    result: dict[str, Any] = {}
    for source in sources:
        _deep_merge(result, source)
    return result


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    """Deep-merge *overrides* into *base*."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
