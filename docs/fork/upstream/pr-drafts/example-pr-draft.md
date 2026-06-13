# PR Draft: fix/example-fix → upstream:dev

**Fork issue:** [#N](https://github.com/<you>/<your-fork>/issues/N)
**Branch:** `fix/example-fix` (from `upstream-mirror`)
**Target:** `<upstream-org>/<project>:dev`

---

## Proposed title

`fix(component): short imperative summary of what changed`

---

<!--
  DESCRIPTION BODY — paste everything between here and "Filing Notes" into the GitHub PR form.
  Do not paste the Filing Notes block.
-->

## Summary

One to two paragraphs describing what changed and why. Write for a reviewer who hasn't seen your issue.

What was broken or missing? What does the fix do? Why is this approach correct?

Do not open with "This PR...". Start with the problem.

### Problem

[Describe the user-visible symptom and root cause.]

### Solution

[Describe what you changed and why this approach over alternatives. Note what you explicitly did NOT change.]

### Files Changed

| File | Change |
|------|--------|
| `src/example.py` | Fixed the broken behavior |

## Target branch

- [x] This PR targets **`dev`**, not `main`. All PRs land in `dev`; `main` is curated by the maintainer at each release.

## Linked Issue

Fixes # <!-- Fill in the upstream issue number before filing -->

## Type of Change

- [x] Bug fix (non-breaking — fixes a confirmed issue)
- [ ] New feature (non-breaking — adds new behaviour)
- [ ] Breaking change (changes or removes existing behaviour)
- [ ] Refactor / cleanup (behaviour unchanged)
- [ ] Documentation only
- [ ] CI / tooling / configuration

## Checklist

- [x] I searched [open issues](https://github.com/<upstream-org>/<project>/issues) and [open PRs](https://github.com/<upstream-org>/<project>/pulls) — this is not a duplicate.
- [x] This PR targets `dev`
- [x] My changes are limited to the scope described above — no unrelated refactors or whitespace changes mixed in.
- [x] I actually ran the app and verified the change works end-to-end. Type-checks and unit tests are not enough.

## How to Test

1. [Start the app — describe the exact command]
2. [Action that triggers the change]
3. [What you should observe]
4. [Optional: how to confirm the old broken behavior is gone]

Tested on: [OS, display server, GPU/driver if relevant]

## Visual / UI changes

None — no HTML, CSS, or DOM-writing JS was changed.

<!-- For UI changes, replace the line above with:
- [x] Screenshot of the change in the running app attached below (before and after if modifying existing UI).
- [x] Style match: the change uses the project's existing visual language (existing CSS variables, button/card classes, etc.).
- [x] No new component patterns — extended an existing widget rather than adding a parallel one.

### Screenshots / clips

[Attach by dragging and dropping into the GitHub PR text box]
-->

---

## Filing Notes

> **INTERNAL — do not paste this section upstream.**

1. **Upstream issue required?** Yes — file upstream issue first, then add its number to "Linked Issue" above.
2. **Target branch:** `dev` (not `main`).
3. **Screenshots needed?** [List any screenshots still to be captured, or "None"]
4. **Dependencies:** [List any PRs that must merge first, or "None"]
5. **Fork tracker:** Issue #N on your fork's issue tracker.
