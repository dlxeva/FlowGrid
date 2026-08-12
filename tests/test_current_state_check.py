"""Unit checks for the current-state freshness classifier."""

from scripts.check_current_state import product_changes_after_state_update


def test_current_state_classifier_reports_product_drift():
    assert product_changes_after_state_update(
        [
            "README.md",
            "src/flg/commands/decision_cmd.py",
            "docs/product/current-state.md",
            "docs/product/case-registry.md",
        ]
    ) == [
        "docs/product/case-registry.md",
        "src/flg/commands/decision_cmd.py",
    ]


def test_current_state_classifier_ignores_non_product_changes():
    assert product_changes_after_state_update(
        ["README.md", "ITERATION_LOG.md", "docs/product/current-state.md"]
    ) == []
