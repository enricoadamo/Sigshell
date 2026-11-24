# Software Engineering submission material

This directory lets both project members review the material for the course
submission. The code is the repository itself. The course brief asks for code,
a report of about one page, and relevant supporting material by **Friday,
27 November 2026 at 23:59**. Since this repository is private, upload a source
archive to Blackboard unless the course staff has been granted GitHub access.

| Item | Purpose |
|---|---|
| [`short-report.pdf`](short-report.pdf) | One-page project report for Blackboard |
| [`short-report.md`](short-report.md) | Editable source of the report |
| [`demo/`](demo/) | Synthetic vignette inputs, screenshot, score output, plot, and replayable `session.R` |
| [`presentation-draft.pdf`](presentation-draft.pdf) | Seven-slide class presentation draft; revise after the topic reply |
| [`topic-update-email.md`](topic-update-email.md) | Draft message to the course instructor; it has not been sent |
| [`TESTING.md`](TESTING.md) | Local verification record and its limits |

The existing video demonstration is here: <https://drive.google.com/file/d/1ICPxVu_TY1JgsI8G86Ytw-A2lHF6SIvg/view?usp=sharing>.
Check access in a private browser window before sharing it with course staff.

The report and presentation currently describe the **local web workbench as the
main product** and the implemented MCP server as an optional interface. We
plan to ask the course instructor whether the final submission can focus solely on
the web application. If approved, revise the report and presentation before
uploading them. The underlying `sigscores` package is unchanged.

The demo data come from a synthetic vignette example. Their scores verify the
software workflow and have no biological interpretation. Installation and use
are documented in [`docs/INSTALL.md`](../docs/INSTALL.md) and
[`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md); they are separate from the short
report as requested by the course brief.
