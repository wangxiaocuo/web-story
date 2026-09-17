---
name: web-story
description: Create, continue, revise, review, or prepare original Chinese web novels for submission. Use when the user wants a coherent short, medium, or serialized web-fiction project rather than one-off prose help.
---

# web-story

Create and maintain original Chinese web-fiction projects through a single natural-language workflow. Keep the author in control of story-defining choices, persist accepted facts locally, and never claim a chapter or book is complete unless the corresponding files exist.

## Use this skill

Use this skill for a new novel, outline, chapter, revision, review, continuation of an existing manuscript, or a submission-preparation request. Do not use it for poetry, screenplay-only work, translating a book, or imitating a living author's distinctive style.

Treat `/web-story` as an explicit user-facing entry point, but infer the same workflow from clear fiction requests. The user should not have to name internal modes or commands.

## Find the project state

1. If the user names a book or gives a folder, resolve that folder. Otherwise, inspect the working directory for exactly one `*.web-story/manifest.json` or `.web-story/manifest.json` before asking.
2. For an existing book, run `scripts/storyctl.py status` and then `preflight` before a mutating chapter operation. If a prior run is unfinished or views disagree, run `reconcile` and report the recovery result before proceeding.
3. Never load a whole long manuscript by default. Follow [context policy](references/context-policy.md).

## Route the request

- **New book / premise / platform fit:** read [workflows](references/workflows.md), then collect only the minimum creative brief before creating files.
- **Plan or redirect a book:** read [workflows](references/workflows.md). Update future intent, not accepted canon, unless the author explicitly accepts a retcon.
- **Draft or continue a chapter:** read [chapter pipeline](references/chapter-pipeline.md) and [review rubric](references/review-rubric.md). A chapter must pass through a staging workspace and be committed by `storyctl`; do not write directly into `正文/`.
- **Review or revise:** read [review rubric](references/review-rubric.md). For an existing chapter, explain material downstream impact before any structural change; preserve author-approved facts unless instructed otherwise.
- **Import and continue:** read [workflows](references/workflows.md). Imported analysis is proposed canon until the author confirms it.
- **Submission package:** read [submission policy](references/submission-policy.md). Prepare materials and open questions; never guarantee eligibility, contract, review, or revenue.

## Non-negotiable invariants

- Accepted prose and confirmed canon are authoritative. Summaries, indexes, statistics, and projections are derived and rebuildable.
- Record facts that a draft establishes before accepting it. Do not silently resolve a contradiction: explain it and ask the author when it changes the story.
- Separate reader-visible knowledge from author knowledge. A character can act only on information available in the scene.
- Use scripts for deterministic work: schema checks, word counts, state recovery, reconciliation, commits, and exports. Keep narrative judgment with the model and author.
- Pause for author direction when a request changes the book's premise, ending posture, core motivation, accepted chapter text, or a major canon conflict.
- Do not offer AI-detector evasion, misrepresent authorship, copy protected prose, or mimic a living author's voice. Support original work, transparent human revision, and current-platform verification instead.

## Completion reports

Report the files actually written or changed, the current book/chapter status, unresolved review findings, and the next author decision. Do not expose internal traces unless the author asks for them.
