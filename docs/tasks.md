# Tasks

## Phase 1: Profile State

- Create `profile_state_db.py`.
- Define schema for reusable profile metadata.
- Add helpers to create, read, update, expire, and recycle profile records.
- Decide and implement profile key format based on `city_name`.
- Add config fields for reusable profile behavior.
- Pass `city_name` and `rsw_id` from `ad_clicker.py` into `create_webdriver()`.
- Update `create_webdriver()` to resolve a reusable city profile instead of always reserving a fresh profile dir.

## Phase 2: Cleanup Policy

- Refactor `search_controller._delete_cache_and_cookies()` into policy-aware cleanup.
- Add cleanup policy selection based on run mode and profile state.
- Update `ad_clicker.py` finalization so reusable profiles are not always deleted.
- Extend `browser_cleanup.py` to recognize reusable profile directories.
- Add TTL cleanup for expired city profiles.
- Preserve current concurrency-safe reservation behavior.

## Phase 3: IP-Aware Hygiene

- Record `last_proxy_ip` and `last_proxy_session_id` in profile metadata.
- On browser startup, compare current proxy IP to stored profile IP.
- Implement `between-run IP changed` hygiene path.
- Preserve current `mid-session IP change` abort path.
- Mark risky profiles when mid-session IP change occurs.

## Phase 4: Seed Cookies

- Add a minimal seed-cookie loader separate from `add_cookies()`.
- Define the allowed seed-cookie scope:
  - consent
  - locale
  - lightweight preferences
- Apply seed only for cold or freshly recycled city profiles.
- Keep consent-click fallback enabled.

## Phase 5: Risk and Recycling

- Define profile risk signals.
- Add `risk_score` persistence.
- Increment score on:
  - mid-session IP change
  - repeated captcha
  - post-captcha Google block
- Recycle profile when risk exceeds threshold.
- Add logs explaining why a profile was recycled.

## Phase 6: Validation

- Validate `py_compile` for all touched modules.
- Run `--once` for a city with a cold profile.
- Run `--once` again within TTL for the same city and verify reuse.
- Validate behavior after between-run IP change.
- Validate behavior after forced TTL expiry.
- Run grouped validation with concurrency.
- Compare captcha rate with baseline.
- Verify no cleanup races and no cross-city profile reuse.

## Deliverables

- reusable city-scoped profile state store
- policy-driven cleanup
- IP-aware hygiene on profile reuse
- seed-cookie bootstrap
- risk-based recycle logic
- config knobs for rollout and rollback
- validation notes and measured impact

## Deferred Items

- sophisticated per-cookie allowlist tuning based on observed Google cookie names
- richer telemetry dashboard for profile trust score
- automatic experimentation framework for TTL and hygiene tuning
