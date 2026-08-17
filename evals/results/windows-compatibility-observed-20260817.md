# Windows 11 compatibility observation and failure disposition

Date: 2026-08-17

Tested base: `4cd893b5b8198b7e74426fd0c3bde9e3d2e99b92`

## Evidence boundary

This record summarizes an externally executed Windows report supplied to the
project owner. The original report and its real marketing transcript remain
outside this repository. They establish observed behavior on one Windows host;
they do not establish user satisfaction, broad Windows compatibility, or a
successful rerun of the candidate fixes.

Observed environment:

- Windows 11 Pro, 64-bit, build 26200
- PowerShell 5.1 with console code page 936 (GBK)
- PortableGit Git Bash
- Python 3.13.14
- FlowGrid v0.3.0 at merge commit `4cd893b`

Observed baseline results:

- `flg version`: passed
- repository smoke test: passed
- full pytest: `7 failed, 221 passed`
- `C:\` and `C:/` session paths: passed
- Chinese and spaced project directory: files were created, then `init` exited
  with `UnicodeEncodeError`
- Git Bash `/c/` init target: created under `C:\c\...` instead of the intended
  drive root

## Runtime defects

| Observation | Assessment | Candidate action |
| --- | --- | --- |
| `init` prints a literal checkmark that code page 936 cannot encode | Runtime defect. The command fails after writing project files. | Use an ASCII first-run success marker and add a GBK-encodable output regression. |
| `init --dir /c/...` resolves to `C:\c\...` | Runtime defect. The existing MSYS normalizer was not used by `init`. | Route `--dir` through `normalize_user_path` and add an init wiring regression. |

## Seven pytest failures

The seven failures were reviewed individually. They do not share one cause.

| Reported failure | Disposition | Reason and action |
| --- | --- | --- |
| Windows path spelling expected `C:/...` but received `C:\...` | Test portability defect | Native `Path` display is platform-specific. Compare with `PureWindowsPath`. |
| Source-tree smoke `PYTHONPATH` expected `:` | Test portability defect | The implementation correctly uses `os.pathsep`; make the assertion do the same. |
| Forced-source smoke `PYTHONPATH` expected `:` | Test portability defect | Same path-separator issue as above. |
| Manifest metadata expected `/` separators | Test portability defect | Validate native `Path.parts` instead of a POSIX suffix string. |
| Status table expected the full `pending_review` cell | Rendering-sensitive test | Rich may truncate a cell at detected terminal width. Fix the test width while retaining the warning and lifecycle assertion. |
| Current-state classifier included its own state document in product drift | Script portability defect | `str(Path(...))` used backslashes on Windows while Git paths use `/`. Normalize Git-style paths in the classifier. |
| Current-state non-product case returned its own state document | Script portability defect | Same classifier defect as above. |

## Doctor boundary

The report attributed `doctor --strict` exit 1 to a missing
`.flg/repo-map.json`. Current FlowGrid semantics explicitly keep an unmapped
project compatible: no repo-map is displayed as informational and does not by
itself make strict mode fail. The report does not provide enough machine-readable
doctor output to identify another failing integrity item. This candidate does
not change doctor semantics.

## Local candidate verification

- focused Windows regressions: `10 passed`
- full repository suite: `231 passed`
- forced repository source-tree smoke: passed
- current-state freshness check: passed with the state document refresh
- workflow YAML parse and `git diff --check`: passed
- Windows Python 3.12 GitHub Actions job: added, not executed locally

The first remote Windows job at `fef01e0` produced `38 failed, 193 passed`.
Log review assigned 37 failures to unqualified test and fixture I/O using the
runner's `cp1252` default, plus one failure to Rich table-cell truncation. The
follow-up defines `PYTHONUTF8=1` as the Windows repository test-process contract
and changes the status regression to assert the warning behavior rather than a
fully rendered table cell.

The original PowerShell and Git Bash commands still need a Windows-host rerun
before the two runtime defects can be described as fixed in the field.
