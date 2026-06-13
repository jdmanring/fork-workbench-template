# Upstream Filing Guide

How to file a professional, complete upstream issue and pull request from a contribution workbench.

**You file. Agents stage.** This guide is for the human author when they are ready to submit.

---

## Part 1: Filing an Upstream Issue

### Before You File

1. Search existing issues on the upstream repo for the bug or feature. Duplicate issues are closed without comment.
2. Check `docs/fork/upstream/pr-status.md` — if a staging branch already fixes this, the issue draft is in `docs/fork/upstream/issue-drafts/`.
3. Verify the fix is not already in `upstream-mirror`: `git diff upstream-mirror develop -- <relevant file>`

### Bug Issue Template

```
**Install method:** [Docker | manual | WSL | native | etc.]

**OS / device:** [e.g. "Ubuntu 22.04, X11, AMD Radeon" or "macOS 14.4, M1" or "Windows 11, RTX 4080"]

**Browser (if applicable):** [Chrome 124 | Firefox 125 | Safari 17 | n/a]

**Steps to Reproduce:**
1. [First action]
2. [Second action]
3. [What you observe]

**Expected:** [What should have happened]

**Actual:** [What actually happened]

**Logs / Error Output:**
```
[paste relevant log lines or console errors — not a paraphrase]
```

**Additional context:** [GPU type, backend, config state, etc.]
```

**Rules for bug issues:**
- Steps must be numbered and exact. "It doesn't work" is not a step.
- Paste the actual error text, not a paraphrase.
- For server/API issues: include backend, model name, GPU/CPU and OS.

### Feature Request Template

```
**Area:** [which component or subsystem]

**Problem / Motivation:**
[What gap or pain point does this address? Be specific.]

**Proposed Solution:**
[What would you add/change/remove? What does the user experience look like after?]

**Alternatives Considered:**
[What else did you consider and why did you rule it out?]
```

### Issue Title Conventions

- Bug: short description of the broken behavior — e.g. `[Component] Download crashes on SSL error mid-transfer`
- Feature: what you want to add — e.g. `[Component] Add pause/resume for downloads`
- Under 80 characters. Do not start with "Bug:" or "Feature:".

---

## Part 2: Filing an Upstream Pull Request

### Before You File

- [ ] Branch starts from `upstream-mirror`, not `develop`
- [ ] Single clean commit (verify: `git log --oneline upstream-mirror..fix/branch-name`)
- [ ] Diff contains only intended files: `git diff upstream-mirror..fix/branch-name --name-only`
- [ ] No hardcoded paths, usernames, or tokens
- [ ] Tests pass locally
- [ ] For UI changes: screenshots captured and ready to attach
- [ ] PR draft has a complete "How to Test" section
- [ ] Read Filing Notes in the PR draft — check for required upstream issue

### PR Title

Use [Conventional Commits](https://www.conventionalcommits.org) format:

```
type(scope): short imperative summary
```

Common types: `fix`, `feat`, `refactor`, `docs`, `test`, `chore`, `ci`

Keep under 72 characters. Put the "why" in the body, not the title.

### PR Base Branch

**Always target the upstream's development branch (usually `dev` or `main`), not your fork.** Check the upstream CONTRIBUTING.md to confirm which branch receives PRs.

### PR Description Bot

Many upstream projects run an automated bot that checks every new PR for required sections. A PR that fails the bot check will be flagged and often closed without review. Common bot-checked sections include:

- **`## Summary`** — must exist and be non-empty
- **`## Linked Issue`** — must contain `Fixes #NNN`, a bare `#NNN`, or an issue URL
- **`## Type of Change`** — at least one checkbox must be checked
- **`## Checklist`** — specific checkboxes (e.g. duplicate-search) must be checked
- **`## How to Test`** — must contain real test steps, not just "tested locally"

Check the upstream repo's `.github/pull_request_template.md` for the exact sections that are required. **Even if no bot runs, including all these sections is good practice** — it signals a professional, reviewable contribution.

**All PR draft files in `docs/fork/upstream/pr-drafts/` should already include these sections pre-filled.** Paste the draft body and the checks will pass.

### PR Description Sections (in order)

Write these sections in this order. This matches the standard upstream PR template used by most open-source projects.

#### 1. Summary

One to two paragraphs explaining what changed and why — written for a reviewer who hasn't seen your issue.

Do not open with "This PR...". Start with the problem or the change.

#### 2. Target Branch

`- [x] This PR targets **\`dev\`** (or whichever branch), not \`main\`.`

Pre-check this in draft files so filing is a copy-paste operation.

#### 3. Linked Issue

`Fixes #NNN` — fill in the upstream issue number before filing. This auto-closes the issue on merge. If filing without a corresponding issue, use `Related: #NNN` to reference a discussion.

The bot rejects a bare `Fixes #` with no number — always fill in the issue number first.

#### 4. Type of Change

Check at least one box. Pre-check the correct type in draft files:

```markdown
- [ ] Bug fix (non-breaking — fixes a confirmed issue)
- [ ] New feature (non-breaking — adds new behaviour)
- [ ] Breaking change (changes or removes existing behaviour)
- [ ] Refactor / cleanup (behaviour unchanged)
- [ ] Documentation only
- [ ] CI / tooling / configuration
```

#### 5. Detail Sections (optional but recommended for non-trivial PRs)

Detail sections go between Type of Change and Checklist. Common subheadings:

**Problem:** What the user experiences, root cause, symptom.

**Solution / Change:** What you changed and why this approach over alternatives.

**Files Changed:** A table for any PR touching more than 2 files:

```markdown
| File | Change |
|------|--------|
| `src/foo.py` | New helper function |
| `routes/bar.py` (new) | New endpoint |
```

#### 6. Checklist

Pre-fill and pre-check in draft files. Typical checklist:

```markdown
- [x] I searched open issues and open PRs — this is not a duplicate.
- [x] This PR targets `dev` (or whichever branch)
- [x] My changes are limited to the scope described above.
- [x] I actually ran the app and verified the change works end-to-end.
```

You can pre-check these when writing the draft because you know the branch is clean, the app runs, and you've confirmed it's not a duplicate. The human filing the PR reviews each box before submitting.

#### 7. How to Test

**Required.** A PR without numbered test steps will be sent back.

Format: numbered steps, starting from a defined state. Write so that a reviewer who has never seen your fix can follow them cold.

```markdown
## How to Test

1. [Setup — what state to start in]
2. [Action — what to do]
3. [Verification — what you should observe]
4. [Optional: how to confirm the old broken behavior is gone]
```

Rules:
- Must describe running the actual app, not just unit tests (unit test results are supporting evidence)
- Cover the golden path and regression path
- State what platform/OS you tested on
- If you couldn't test on a platform, say so explicitly

#### 8. Visual / UI changes

Required for any UI-touching PR. For non-UI PRs, include: "None — no HTML, CSS, or DOM-writing JS was changed." See Part 3 for screenshot requirements.

---

## Part 3: Screenshots

### What Requires a Screenshot

Any change that affects:
- CSS files
- HTML files
- JS files that write to the DOM, modify classes, or control visibility
- Any button, modal, dropdown, card, panel, badge, or color

If you're unsure, treat it as visual and attach a screenshot.

### What the Screenshot Must Show

- The running app, not a mockup
- The changed element in context
- Before and after for modifications to existing UI (two screenshots, labeled)
- Mobile screenshot if the change affects mobile layout

### How to Attach

Drag and drop into the GitHub PR description text box. Do not link to files in your fork — upstream reviewers may not have access to your repo.

### Never file a UI PR with "screenshots pending"

The PR will be sent back. Capture before opening the PR form.

---

## Part 4: The LLM Agent Note

Many upstream projects warn about bulk AI-generated PR submissions. This typically targets unreviewed, agent-filed PRs — not contributions developed with AI assistance and reviewed by a human.

**You reviewed every change, ran the tests, tested the app manually, and are the human author.** This is no different from using an autocomplete tool.

When filing:
- Do not add AI/agent disclosure to the PR description unless asked
- Write the PR in first person as yourself
- If a reviewer asks directly: "I developed this with AI coding assistance, but I reviewed and tested all changes myself before submitting"

---

## Part 5: Cross-Platform Notes

If you couldn't test on all platforms your change might affect, say so:
- "Tested on Linux (Ubuntu 22.04, Wayland). Not tested on macOS or Windows."
- "Docker path not verified — change is native-install only."

This is acceptable. Do not omit a code path because you can't test it on a platform you don't have — just disclose.

---

## Part 6: Draft Files

### PR Drafts

One file per staging branch in `docs/fork/upstream/pr-drafts/`. See `example-pr-draft.md` in that directory for the full format. Each draft contains:

| Section | Purpose |
|---------|---------|
| **Title** | Paste into GitHub PR title field |
| **Description** | Paste into GitHub PR body (above "Filing Notes") |
| **How to Test** | Already in the description body |
| **Filing Notes** | Internal instructions — **do not paste upstream** |

The description body should contain all 8 sections from Part 2, pre-filled and ready to paste.

### Issue Drafts

Every staging branch also needs a corresponding issue draft in `docs/fork/upstream/issue-drafts/`. This is a **separate file** from the PR draft — it contains the exact upstream issue title and body, pre-written and ready to paste into the upstream project's new issue form.

See `example-issue-draft.md` in that directory for the full format.

**Issue draft format:**

```
# Upstream Issue Draft: <name>

**File on:** <upstream repo>
**Related PR draft:** docs/fork/upstream/pr-drafts/<name>.md
**Branch:** <branch-name>
**Type:** Bug | Enhancement | Refactor
**References:** Related to #NNN (if applicable)

---

## Title

`[exact title to paste into GitHub]`

---

## Body

[complete issue body — paste into the upstream new-issue text box]
```

The body uses the upstream bug or feature request template, **fully filled out** — not a skeleton with empty brackets. For bugs: Install method, OS/device, Steps to Reproduce, Expected, Actual, Logs, Additional context. For features: Area, Problem/Motivation, Proposed Solution, Alternatives Considered.

**Every PR needs its own new upstream issue.** Even when a related issue already exists (filed by someone else, or covering a broader topic), file a new one scoped to your specific contribution. Reference the existing issue with `Related to #NNN` in the body — but `Fixes #` goes on your own new issue, not on someone else's.

### Filing Workflow

**Step 1 — File the upstream issue:**

1. Open `docs/fork/upstream/issue-drafts/<name>.md`
2. Go to the upstream project's new issue page
3. Paste the **Title** from the issue draft
4. Paste the **Body** from the issue draft
5. Submit and note the issue number assigned
6. Open `docs/fork/upstream/pr-drafts/<name>.md` and fill in `Fixes #NNN`

**Step 2 — File the PR:**

1. Open the PR draft for the branch
2. Read **Filing Notes** — confirm issue number is filled in and screenshots are ready
3. Open: `<your-fork>:<branch>` → `<upstream>:<dev-branch>`
4. Paste title and description body (not Filing Notes)
5. Attach screenshots by drag-and-drop
6. Submit
7. Update `docs/fork/upstream/pr-status.md` with the upstream PR number

---

## Part 7: Common Mistakes That Get PRs Closed

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| No "How to Test" section | PR sent back | Write numbered steps from a cold start |
| UI change without screenshot | PR closed | Capture and attach before filing |
| PR against `main` instead of dev branch | Redirected/closed | Change base branch before submitting |
| Issue not filed first (when required) | Reviewer asks for it | Check Filing Notes; file issue, add its # to PR |
| Vague problem description | Closed as not actionable | Write exact symptoms and numbered steps |
| Upstream issue already exists | Duplication | Search first; link to existing instead |
| Mixing unrelated changes | Hard to review; rejected | One fix per PR |
| Missing required template sections | Bot flags; maintainer closes | Use the full 8-section template |
| Unchecked required checkboxes | Bot flags | Pre-check appropriate boxes in draft |
| Screenshot links to fork repo files | Reviewer can't see it | Drag-and-drop into GitHub text box |
| AI-disclosure boilerplate in PR body | Looks bot-generated | Write naturally, first-person, no disclosure |
