# RSE-Agent Peer Review Audit

## Run Summary
- Passed: `False`
- Iterations: `1` / `1`
- Runner: `none`
- Error: `compliance:blocking:["separation_of_concerns"]`

## Validation Output
### stdout
```text
[reviewer] blocking execution due to checklist failures
```
### stderr
```text

```

## Carver Checklist (Deterministic)
- Score: `0.5`
- Blocking: `True`

- `no_hardcoded_paths`: **PASS** — no absolute path string literals detected
- `version_control_hygiene`: **PASS** — header mentions version/commit
- `separation_of_concerns`: **FAIL** — cannot parse code to analyze I/O separation: invalid character '’' (U+2019) (<unknown>, line 3)
- `license_check`: **FAIL** — no LICENSE/COPYING file found at repo root

## Artifacts
- `candidate.py`: refactored code
- `test_candidate.py`: generated tests
