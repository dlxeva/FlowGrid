"""Tests for flg audit command."""

import os

from typer.testing import CliRunner

from flg.cli import app

runner = CliRunner()


def test_audit_ignores_docs_directory(tmp_path):
    """audit must NOT flag files in docs/ as conflicts (发现 6).

    docs/ is the user's free zone for project materials. FLG does not
    scan or audit docs/. A file in docs/ with a similar name to a root
    file must not trigger a multi-version conflict warning.
    """
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Audit Docs Test"])

        # Create a root file and a docs/ file with similar stems.
        # Pre-merge: if audit scanned docs/, these would look like
        # two versions of the same doc.
        (tmp_path / "research.md").write_text("# Root research", encoding="utf-8")
        (tmp_path / "docs" / "research.md").write_text("# Docs research", encoding="utf-8")

        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        # The docs/ file should NOT appear in conflict warnings
        assert "docs/research.md" not in result.output
    finally:
        os.chdir(old_cwd)


def test_audit_ignores_generated_dependency_and_build_directories(tmp_path):
    """Generated files must not create false multi-version conflicts."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Generated Files Audit Test"]).exit_code == 0
        (tmp_path / "node_modules" / "package-a").mkdir(parents=True)
        (tmp_path / "node_modules" / "package-a" / "README.md").write_text("# dependency", encoding="utf-8")
        (tmp_path / "dist").mkdir()
        (tmp_path / "index.html").write_text("<main>source</main>", encoding="utf-8")
        (tmp_path / "dist" / "index.html").write_text("<main>build</main>", encoding="utf-8")

        result = runner.invoke(app, ["audit"])

        assert result.exit_code == 0
        assert "node_modules/package-a/README.md" not in result.output
        assert "dist/index.html" not in result.output
        assert "Fix 2 high-risk multi-version conflict" not in result.output
    finally:
        os.chdir(old_cwd)


def test_audit_warns_when_evidence_basis_is_secondary(tmp_path):
    """Audit should surface a low-confidence framing basis without blocking."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        runner.invoke(app, ["init", "Evidence Audit Test"])
        framing_path = tmp_path / "FRAMING.md"
        content = framing_path.read_text(encoding="utf-8")
        content = content.replace("(to be defined)", "Real content here")
        content = content.replace("(to be filled)", "Real content here")
        content = content.replace("(to be hypothesized)", "Real hypothesis")
        content = content.replace("(to be identified)", "- Question 1")
        content = content.replace("(none yet)", "- Risk 1")
        content = content.replace("(direct / verified / secondary / speculative)", "secondary")
        framing_path.write_text(content, encoding="utf-8")

        result = runner.invoke(app, ["audit"])

        assert result.exit_code == 0
        assert "secondary evidence" in result.output.lower()
    finally:
        os.chdir(old_cwd)


def test_audit_reports_missing_authoritative_anchor(tmp_path):
    """A complete ledger is not ready while an authoritative anchor is missing."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Missing Anchor Audit Test"]).exit_code == 0
        (tmp_path / "ANCHORS.md").write_text(
            """# Authoritative Anchors\n\n### Product\n\n- **File:** missing/README.md\n- **Role:** product truth\n- **Authority:** authoritative\n- **Provenance:** internal\n- **Lifecycle:** active\n""",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["audit"])
        assert result.exit_code == 0
        assert "Anchor Health" in result.output
        assert "missing/README.md" in result.output
        assert "Ready for FLG workflow" not in result.output
    finally:
        os.chdir(old_cwd)


def test_audit_resolves_markdown_code_span_anchor_paths(tmp_path):
    """Backticks are presentation syntax, not part of an anchor path."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert runner.invoke(app, ["init", "Code Span Anchor Audit Test"]).exit_code == 0
        (tmp_path / "lambda").mkdir()
        (tmp_path / "lambda" / "app.mjs").write_text("export default {};", encoding="utf-8")
        (tmp_path / "ANCHORS.md").write_text(
            """# Authoritative Anchors

### Runtime

- **File:** `lambda/app.mjs`
- **Role:** runtime truth
- **Authority:** authoritative
- **Provenance:** internal
- **Lifecycle:** active
""",
            encoding="utf-8",
        )

        result = runner.invoke(app, ["audit"])

        assert result.exit_code == 0
        assert "1 anchor(s) resolve to existing files" in result.output
        assert "point to missing files" not in result.output
    finally:
        os.chdir(old_cwd)
