---
name: web-story
description: Create, deconstruct, continue, revise, review, or prepare original Chinese web novels for submission. Use for coherent short, medium, or serialized web-fiction projects, including craft-focused analysis of reference works that will inform original writing.
---

# web-story

Create and maintain original Chinese web-fiction projects through a single natural-language workflow. Keep the author in control of story-defining choices, persist accepted facts locally, and never claim a chapter or book is complete unless the corresponding files exist. This is a standard Agent Skill: do not assume a particular host application or ask the author to operate its internal tooling.

## Use this skill

Use this skill for a new novel, outline, chapter, revision, review, continuation of an existing manuscript, a craft-focused book deconstruction, or a submission-preparation request. Do not use it for poetry, screenplay-only work, translating a book, general literary scholarship unrelated to web-fiction creation, or imitating a living author's distinctive style.

Treat `/web-story` as an explicit user-facing entry point, but infer the same workflow from clear fiction requests. The user should not have to name internal modes or commands.

## Find the project state

1. If the user names a book or gives a folder, resolve that folder. Otherwise, inspect the working directory for exactly one `.web-story/manifest.json` before asking.
2. For an existing book, use `scripts/storyctl.py` automatically when Python 3 is available: run `status` and then `preflight` before a mutating chapter operation. If a prior run is unfinished or views disagree, run `reconcile` and report the recovery result before proceeding.
3. If Python 3 is unavailable, keep the same file contract with ordinary agent file tools, perform the checks in the relevant reference manually, and clearly say that deterministic validation was unavailable. Never tell the author to run a command merely to use the skill.
4. Never load a whole long manuscript by default. Follow [context policy](references/context-policy.md).

## Route the request

- **New book / premise / platform fit:** read [workflows](references/workflows.md) and, for serialized fiction, [serial story engine](references/serial-story-engine.md); then collect only the minimum creative brief before creating files.
- **Plan or redirect a book:** read [workflows](references/workflows.md) and the [serial story engine](references/serial-story-engine.md) when planning a serial. Update future intent, not accepted canon, unless the author explicitly accepts a retcon.
- **Draft or continue a chapter:** read [chapter pipeline](references/chapter-pipeline.md), which routes to prose and continuity guidance, and [review rubric](references/review-rubric.md). Use a staging workspace; when the helper is available, let it commit the chapter. Do not write directly into `正文/` before review and settlement.
- **Review or revise:** read [review rubric](references/review-rubric.md) and its relevant prose/continuity guidance. For an existing chapter, explain material downstream impact before any structural change; preserve author-approved facts unless instructed otherwise.
- **Deconstruct one or more books:** read [book deconstruction](references/book-deconstruction.md). Analyze only the requested scope, distinguish evidence from inference, and convert findings into abstract craft patterns rather than a disguised copy. Keep reference analysis outside canon and obtain author confirmation before applying it to an active book.
- **Import and continue:** read [workflows](references/workflows.md). Imported analysis is proposed canon until the author confirms it.
- **Submission package:** read [submission policy](references/submission-policy.md). Prepare materials and open questions; never guarantee eligibility, contract, review, or revenue.

## Non-negotiable invariants

- Accepted prose and confirmed canon are authoritative. Summaries, indexes, statistics, and projections are derived and rebuildable.
- Record facts that a draft establishes before accepting it. Do not silently resolve a contradiction: explain it and ask the author when it changes the story.
- Separate objective facts, narrator access, reader knowledge, and each character's knowledge. Trace consequential dialogue and reactions to an available information channel; text visible to the reader is not automatically perceptible to a character.
- Default to mobile-friendly paragraphs and concrete, character-specific prose. Write Chinese prose with full-width Chinese punctuation by default; keep half-width marks inside numbers, units, and embedded English. Apply [prose quality](references/prose-quality.md) through drafting and revision, respecting the author's chosen style rather than enforcing phrase bans or uniform sentence lengths.
- Before reusing an entity, retrieve its established identity, relevant attributes, and state with source evidence. Apply [continuity](references/continuity.md); a new fact ID or a plausible synonym does not establish a valid change.
- Ground everyday details in the story's time, place, person, and immediate activity. Check physical prerequisites and state transitions within a chapter as well as across chapters; first appearances and scene cuts do not exempt a detail from plausibility checks. Common habits are defaults, not universal laws, and exceptions need proportionate support.
- When available, use the bundled helper for deterministic work: schema checks, word counts, state recovery, reconciliation, commits, and exports. Keep narrative judgment with the model and author; retain a transparent manual fallback for agents without Python.
- Pause for author direction when a request changes the book's premise, ending posture, core motivation, accepted chapter text, or a major canon conflict.
- Do not offer AI-detector evasion, misrepresent authorship, copy protected prose, or mimic a living author's voice. Support original work, transparent human revision, and current-platform verification instead.
- Do not fetch unauthorized full texts or reconstruct a source book from an analysis. Prefer material supplied by the author, public-domain or licensed sources, and brief evidence descriptions over reproduced passages.

## Completion reports

Report the files actually written or changed, the current book/chapter status, unresolved review findings, and the next author decision. Do not expose internal traces unless the author asks for them.
