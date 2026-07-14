"""flg onboard command — first-run setup: env check + demo + skill install.

Solves the "installed but now what?" gap. A new user runs `flg onboard` and gets:
  1. Environment check (version, PATH, existing project, detected hosts + skills)
  2. A guided 5-minute demo of the core loop (init → closeout → review → context)
  3. Skill installation for detected hosts (symlink from repo to host skills dir)
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from .. import __version__
from ..core.files import is_flg_project

console = Console()

# Hosts we know how to detect and install skills into.
# Each entry: (host_name, marker_path_relative_to_home, skills_subdir)
# marker_path is checked relative to Path.home() to determine if the host is installed.
_KNOWN_HOSTS = [
    ("codex", ".codex", "skills"),
    ("hermes", ".hermes", "skills"),
    ("zcode", ".zcode", "skills"),
    ("agents", ".agents", "skills"),  # ZCode cross-tool default
    ("claude", ".claude", "skills"),
]

_SKILL_NAME = "flowgrid-operator"

# Built-in demo transcript for the guided closeout demo.
_DEMO_TRANSCRIPT = """# Onboard Demo Session

## Discussion

We decided to go with a single-page layout for the landing page.
Because it loads faster and has a cleaner conversion path.
We ruled out the multi-tab design because mobile experience is poor.
If the single-page bounce rate doesn't improve, we can go back to the old layout.

That legacy auth module is not being maintained this quarter.
"""


def _skill_source_path() -> Optional[Path]:
    """Locate the bundled skill directory relative to the flg package."""
    pkg_dir = Path(__file__).resolve().parent.parent  # src/flg
    repo_root = pkg_dir.parent  # framing-ledger/
    skill_dir = repo_root / "skills" / _SKILL_NAME
    if skill_dir.is_dir():
        return skill_dir
    # Fallback: try two levels up (in case of different install layouts)
    skill_dir2 = pkg_dir.parent.parent / "skills" / _SKILL_NAME
    if skill_dir2.is_dir():
        return skill_dir2
    return None


def detect_hosts() -> list[dict]:
    """Detect installed AI hosts and whether the FLG skill is present in each.

    Returns a list of dicts with keys: name, home_marker, skills_dir, skill_installed.
    """
    home = Path.home()
    hosts = []
    for name, marker_rel, skills_subdir in _KNOWN_HOSTS:
        marker = home / marker_rel
        if not marker.exists():
            continue
        skills_dir = home / marker_rel / skills_subdir
        skill_path = skills_dir / _SKILL_NAME
        # Check if skill exists (as symlink, dir, or file)
        skill_installed = skill_path.exists() or skill_path.is_symlink()
        hosts.append({
            "name": name,
            "home_marker": str(marker),
            "skills_dir": str(skills_dir),
            "skill_path": str(skill_path),
            "skill_installed": skill_installed,
        })
    return hosts


def check_skill_installed(skill_path: Path) -> bool:
    """Check if the skill is already installed at the given path."""
    return skill_path.exists() or skill_path.is_symlink()


def install_skill(host_skills_dir: Path, skill_source: Path, force: bool = False) -> bool:
    """Create a symlink from host_skills_dir/SKILL_NAME to skill_source.

    Returns True if installed (or already present), False if skipped/failed.
    """
    target = host_skills_dir / _SKILL_NAME

    # Already installed
    if check_skill_installed(target):
        if force and target.is_symlink():
            target.unlink()
        elif force and target.is_dir():
            shutil.rmtree(target)
        elif force and target.exists():
            target.unlink()
        else:
            return True  # already there, not forcing

    host_skills_dir.mkdir(parents=True, exist_ok=True)
    try:
        target.symlink_to(skill_source, target_is_directory=True)
        return True
    except OSError:
        # Symlink failed (permissions, filesystem, etc.) — fall back to copy
        try:
            shutil.copytree(skill_source, target)
            return True
        except Exception:
            return False


def run_demo(root: Path) -> None:
    """Run the guided core-loop demo in the given project root.

    Assumes the project is already initialized (or will be by the caller).
    Uses the CliRunner to invoke commands programmatically.
    """
    from typer.testing import CliRunner
    from ..cli import app

    runner = CliRunner()

    # Step 1: write demo transcript
    sessions_dir = root / ".flg" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    transcript = sessions_dir / "demo-session.md"
    transcript.write_text(_DEMO_TRANSCRIPT, encoding="utf-8")

    console.print()
    console.print("[bold cyan]Step 1/4: Closeout[/bold cyan] — extracting decisions from a demo transcript")
    console.print("[dim]  This reads raw session notes and extracts candidate decisions, risks, and actions.[/dim]")

    result = runner.invoke(app, ["closeout", "--transcript", str(transcript), "--no-llm"])
    if result.exit_code != 0:
        console.print(f"[red]  Closeout failed: {result.output}[/red]")
        return
    console.print("[green]  ✓ Patch generated with candidate decisions[/green]")

    # Find the generated patch
    import glob
    patch_files = sorted(glob.glob(str(root / ".flg" / "patches" / "closeout-*.patch.md")))
    if not patch_files:
        console.print("[red]  No closeout patch found[/red]")
        return
    patch_path = Path(patch_files[-1])

    # Step 2: review
    console.print()
    console.print("[bold cyan]Step 2/4: Review[/bold cyan] — accepting real decisions, blocking empty shells")
    console.print("[dim]  The review step separates real decisions from noise. --accept-all skips shells automatically.[/dim]")

    result = runner.invoke(app, ["review", "--patch", patch_path.name, "--accept-all"])
    if result.exit_code != 0:
        console.print(f"[yellow]  Review completed (may have skipped shells): {result.output[-100:]}[/yellow]")
    else:
        console.print("[green]  ✓ Decisions reviewed and accepted into DECISIONS.md[/green]")

    # Step 3: merge
    console.print()
    console.print("[bold cyan]Step 3/4: Merge[/bold cyan] — applying reviewed changes to the ledger")

    result = runner.invoke(app, ["merge", "--patch", patch_path.name], input="y\n")
    if result.exit_code == 0:
        console.print("[green]  ✓ Patch merged into PROGRESS.md and SNAPSHOT.md[/green]")

    # Step 4: context
    console.print()
    console.print("[bold cyan]Step 4/4: Context Pack[/bold cyan] — generating bounded startup context")
    console.print("[dim]  This is what a new agent reads to pick up the project without re-explaining everything.[/dim]")

    result = runner.invoke(app, ["context"])
    if result.exit_code == 0:
        console.print("[green]  ✓ Context Pack generated at .flg/context/startup.md[/green]")

    # Summary
    console.print()
    console.print("[bold green]✓ Demo complete![/bold green]")
    console.print("Your project now has:")
    decisions = (root / "DECISIONS.md").read_text(encoding="utf-8") if (root / "DECISIONS.md").exists() else ""
    d_count = decisions.count("## D-")
    console.print(f"  - DECISIONS.md ({d_count} decision entries)")
    console.print(f"  - SNAPSHOT.md (current project state)")
    console.print(f"  - .flg/context/startup.md (bounded agent startup context)")
    console.print(f"  - PROGRESS.md (session progress log)")
    console.print()
    console.print("[dim]This is the core FLG loop: closeout → review → merge → context.[/dim]")
    console.print("[dim]In real use, you work in natural language, then run closeout at the end of a session.[/dim]")


def onboard(
    skip_demo: bool = typer.Option(False, "--skip-demo", help="Skip the guided demo"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Auto-confirm all prompts (non-interactive)"),
) -> None:
    """First-run onboarding: environment check, guided demo, and skill installation."""
    root = Path.cwd()

    # ── Phase 1: Environment check ────────────────────────────────────
    console.print()
    console.print("[bold]═══ Phase 1: Environment Check ═══[/bold]")
    console.print()

    # Version + PATH
    flg_in_path = shutil.which("flg") is not None
    console.print(f"  FLG version: [bold]{__version__}[/bold]")
    console.print(f"  flg on PATH: {'[green]✓ yes[/green]' if flg_in_path else '[yellow]⚠ no (use full path or fix PATH)[/yellow]'}")

    # Current directory
    is_project = is_flg_project(root)
    if is_project:
        console.print(f"  Current dir: [green]✓ FLG project detected[/green]")
    else:
        console.print(f"  Current dir: [dim]not an FLG project[/dim]")

    # Host detection
    hosts = detect_hosts()
    console.print()

    if hosts:
        host_table = Table(title="Detected AI Hosts")
        host_table.add_column("Host", style="cyan")
        host_table.add_column("Skill Installed", style="bold")

        for h in hosts:
            status = "[green]✓ yes[/green]" if h["skill_installed"] else "[yellow]✗ no[/yellow]"
            host_table.add_row(h["name"], status)

        console.print(host_table)
    else:
        console.print("[dim]  No known AI hosts detected.[/dim]")

    # ── Phase 2: Guided demo ──────────────────────────────────────────
    if not skip_demo:
        console.print()
        console.print("[bold]═══ Phase 2: Guided Demo ═══[/bold]")
        console.print()

        if is_project:
            do_demo = yes or Confirm.ask(
                "This directory is already an FLG project. Run the demo here?",
                default=False,
            )
        else:
            do_demo = yes or Confirm.ask(
                "Run a 5-minute guided demo of the core FLG loop?",
                default=True,
            )

        if do_demo:
            if not is_project:
                from typer.testing import CliRunner
                from ..cli import app as flg_app
                runner = CliRunner()
                console.print()
                console.print("[dim]  Initializing a demo project in the current directory...[/dim]")
                runner.invoke(flg_app, ["init", "Onboard Demo", "--type", "proposal"])

            run_demo(root)
    else:
        console.print()
        console.print("[dim]Skipping demo (--skip-demo)[/dim]")

    # ── Phase 3: Skill installation ───────────────────────────────────
    console.print()
    console.print("[bold]═══ Phase 3: Skill Installation ═══[/bold]")
    console.print()

    skill_source = _skill_source_path()
    if skill_source is None:
        console.print("[yellow]⚠ Standard skill not found in flg installation.[/yellow]")
        console.print("[dim]The skill ships with the repo under skills/flowgrid-operator/.[/dim]")
    elif not hosts:
        console.print("[dim]No hosts detected — skipping skill installation.[/dim]")
        console.print(f"[dim]The skill is available at: {skill_source}[/dim]")
    else:
        installed_count = 0
        for h in hosts:
            if h["skill_installed"]:
                console.print(f"  [green]✓ {h['name']}: skill already installed[/green]")
                installed_count += 1
                continue

            should_install = yes or Confirm.ask(
                f"Install flowgrid-operator skill into {h['name']}?",
                default=True,
            )
            if should_install:
                skills_dir = Path(h["skills_dir"])
                success = install_skill(skills_dir, skill_source)
                if success:
                    console.print(f"  [green]✓ {h['name']}: skill installed (symlink)[/green]")
                    installed_count += 1
                else:
                    console.print(f"  [red]✗ {h['name']}: installation failed[/red]")
            else:
                console.print(f"  [dim]{h['name']}: skipped[/dim]")

        console.print()
        console.print(f"[bold]Skill installed in {installed_count}/{len(hosts)} host(s).[/bold]")

    # ── Summary ───────────────────────────────────────────────────────
    console.print()
    console.print("[bold green]✓ Onboarding complete![/bold green]")
    console.print()
    console.print("Next steps:")
    if not is_project and not (skip_demo is False and locals().get("do_demo")):
        console.print("  1. Start a real project: [cyan]flg init \"My Project\"[/cyan]")
        console.print("  2. Define the problem: [cyan]flg frame[/cyan]")
    console.print("  3. Work in natural language with your AI host")
    console.print("  4. Close out sessions: [cyan]flg closeout --transcript <file>[/cyan]")
    console.print("  5. Review and merge: [cyan]flg review[/cyan] then [cyan]flg merge[/cyan]")
