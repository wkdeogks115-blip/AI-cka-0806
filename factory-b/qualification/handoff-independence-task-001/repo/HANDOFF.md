# Implementation Handoff

## Goal
Implement `normalize_slug` in `src/text_utils.py` so the supplied tests pass.

## Requirements
- Lowercase ASCII letters.
- Convert one or more whitespace characters to one hyphen.
- Remove punctuation other than hyphens.
- Collapse repeated hyphens.
- Strip leading/trailing hyphens.

## Non-goals
- Unicode transliteration.
- External packages.
- Public release or deployment.

## Constraints
- Edit only `src/text_utils.py` unless a test-only correction is demonstrably required.
- Use Python standard library only.
- Do not rely on prior chat or hidden context.

## Relevant Files
- `src/text_utils.py`
- `tests/test_text_utils.py`
- `AGENTS.md`

## Acceptance Criteria
- All existing tests pass.
- Behavior matches the requirements above.
- No unrelated file changes.

## Required Tests
- `python -m pytest -q`

## Evidence Required
- Test command and result.
- Changed-file list.
- Short implementation summary.

## Release Target
LOCAL
