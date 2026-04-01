# Plan

## Goal

Implement a city-scoped, short-lived trust profile strategy that works with rotating proxy IPs and integrates cleanly with the current grouped runner.

## Phase 1: State and Profile Ownership

### Outcome

Introduce reusable profile metadata and route browser creation through it.

### Changes

- add a profile state persistence layer
- define profile keying by `city_name`
- add TTL support
- pass `city_name` and `rsw_id` into `create_webdriver()`
- split profile handling into:
  - ephemeral per-run profile
  - reusable city profile

### Files

- `profile_state_db.py` new
- `ad_clicker.py`
- `webdriver.py`
- `config_reader.py`
- `config.json`

## Phase 2: Cleanup Policy Refactor

### Outcome

Stop unconditional full cleanup and make cleanup policy-driven.

### Changes

- replace the current hard reset path with cleanup policies
- keep full cleanup for ephemeral runs
- add selective cleanup for reusable city profiles
- make reusable profile retention TTL-aware
- extend cleanup logic to remove expired/recycled city profiles safely

### Files

- `search_controller.py`
- `ad_clicker.py`
- `browser_cleanup.py`
- `config_reader.py`
- `config.json`

## Phase 3: IP-Aware Hygiene

### Outcome

Handle rotating IPs without blindly trusting stale state.

### Changes

- compare current proxy IP with last profile IP before reuse
- on between-run IP change:
  - preserve lightweight consent/locale state
  - clear sensitive cookies and ephemeral storage
- on mid-session IP change:
  - keep current abort behavior
  - increase risk score
  - mark the profile for recycle if threshold is exceeded

### Files

- `profile_state_db.py`
- `webdriver.py`
- `search_controller.py`

## Phase 4: Seed Cookie Bootstrap

### Outcome

Warm up cold profiles with a minimal consent/locale seed.

### Changes

- add a narrow seed-cookie loader
- apply seed only for cold or reset city profiles
- keep the current consent-click fallback
- avoid using full `cookies.txt` for the new path

### Files

- `utils.py`
- `search_controller.py`
- `config_reader.py`
- `config.json`

## Phase 5: Risk Scoring and Recycling

### Outcome

Automatically recycle profiles that become suspicious or stale.

### Changes

- track profile risk signals
- increment risk on:
  - mid-session IP change
  - repeated captcha
  - post-captcha block
  - repeated no-click suspicious pattern if desired
- recycle profile when score exceeds threshold

### Files

- `profile_state_db.py`
- `search_controller.py`
- `ad_clicker.py`
- `browser_cleanup.py`

## Phase 6: Validation

### Outcome

Validate that the new model improves trust without destabilizing runtime behavior.

### Validation Steps

- py_compile for touched modules
- single-city `--once` validation
- grouped run validation with concurrency
- verify no profile deletion race
- verify reusable profile survives normal end-of-run
- verify profile recycles on TTL
- verify behavior on between-run IP change
- compare captcha rate before and after

## Implementation Order

1. Add profile metadata store.
2. Pass grouped city context into browser creation.
3. Introduce reusable city profile resolution with TTL.
4. Refactor cleanup from hard reset to policy.
5. Add between-run IP hygiene.
6. Add minimal seed-cookie bootstrap.
7. Add risk score and recycle logic.
8. Run validations and tune defaults.

## Rollout Notes

- keep feature-flagged config defaults during rollout
- preserve a fast revert path to fully-ephemeral mode
- avoid changing multiple trust variables at once without measuring impact

