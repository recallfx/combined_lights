"""Production configuration contract tests."""

from pathlib import Path

import yaml

from custom_components.combined_lights import CONFIG_SCHEMA


def test_checked_in_production_config_is_valid_and_has_unique_ids():
    """Validate the production YAML with the integration's real schema."""
    config_path = Path(__file__).resolve().parents[2] / "combined_lights.yaml"
    combined_lights = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    validated = CONFIG_SCHEMA({"combined_lights": combined_lights})[
        "combined_lights"
    ]
    ids = [entry["id"] for entry in validated]

    assert len(ids) == len(set(ids))
    assert "entrance" in ids
