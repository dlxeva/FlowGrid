"""Checks for the machine-readable real-case evidence registry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "evals" / "case-registry.json"


def test_case_registry_has_bounded_evidence_and_existing_sources():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    cases = data["cases"]
    known_kinds = {
        "real_project_controlled_eval",
        "customer_field_use",
        "cross_project_dogfood",
        "host_acceptance",
        "project_orchestration_dogfood",
        "external_adoption",
    }

    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert data["evidence_boundary"]["supported"]
    assert data["evidence_boundary"]["not_supported"]

    for case in cases:
        assert case["kind"] in known_kinds
        assert case["case_count"] > 0
        assert case["projects"]
        assert case["objective_metrics"]
        assert case["claim_supported"]
        assert case["limits"]
        assert not Path(case["source"]).is_absolute()
        source_path = ROOT / case["source"]
        assert source_path.is_file()
        if locator := case.get("source_locator"):
            assert locator in source_path.read_text(encoding="utf-8")


def test_registry_distinguishes_real_cases_from_external_adoption():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    cases = data["cases"]

    real_continuation_projects = sum(
        case["case_count"]
        for case in cases
        if case["kind"] == "real_project_controlled_eval"
    )
    external_adoption_cases = sum(
        case["case_count"]
        for case in cases
        if case["kind"] == "external_adoption"
    )

    assert real_continuation_projects == 5
    assert external_adoption_cases == 0
