# Status

## Current Goal

Implement the city-scoped reusable profile strategy for the x86_64 VPS branch, with:

- short-lived reusable profiles keyed by city
- IP-rotation-aware hygiene
- minimal seed-cookie bootstrap
- policy-driven cleanup
- risk-based recycle logic

## Progress

### Completed

- Added config surface for reusable profile behavior in `config.json` and `config_reader.py`.
- Added `profile_state_db.py` for reusable profile metadata persistence.
- Added reusable profile base path in `browser_cleanup.py`.
- Added Google seed-cookie helpers in `utils.py`.
- Updated `webdriver.py` to:
  - resolve reusable city profiles
  - fallback to ephemeral profile on active-use conflict
  - attach profile metadata to the driver
  - cleanup expired/recycled profiles before browser startup
- Updated `ad_clicker.py` to:
  - pass grouped city context into browser creation
  - release reusable profile reservations without deleting healthy reusable profiles
- Updated `search_controller.py` to:
  - apply startup bootstrap for reusable profiles
  - run between-run IP-change hygiene
  - seed cold profiles
  - switch end-of-run cleanup to policy-driven behavior
  - update profile risk state and recycle decision at shutdown

### In Progress

- broader live soak validation under grouped traffic
- tuning seed-cookie values from observed captcha outcomes
- extending the same reusable-profile behavior to SeleniumBase mode only if needed later

## Known Design Choices

- Reusable profiles are keyed by `city_name`.
- Reusable profile conflicts fall back to an ephemeral profile instead of sharing the same `user-data-dir`.
- Mid-session IP change still aborts the run and now raises profile recycle risk.
- Between-run IP change triggers selective Google-state hygiene instead of full profile deletion.

## Validation Checklist

- [x] `py_compile` passes on all touched modules
- [x] cold-profile bootstrap works
- [x] warm-profile reuse works within TTL
- [x] between-run IP-change hygiene works
- [x] expired/recycled profile cleanup works
- [ ] no cleanup-race regression appears under broader grouped load

## Validation Notes

- `py_compile` passed for:
  - `ad_clicker.py`
  - `webdriver.py`
  - `search_controller.py`
  - `utils.py`
  - `browser_cleanup.py`
  - `config_reader.py`
  - `profile_state_db.py`
- Cold reusable-profile validation with `Pedreira` confirmed:
  - persistent profile directory created at `.runtime/city_profiles/pedreira`
  - seed cookies applied successfully
  - profile metadata persisted to `profile_state.db`
- Warm reusable-profile validation with `Pedreira` confirmed:
  - same profile directory reused
  - `SEED_REQUIRED=False` on second run
  - `BETWEEN_RUN_IP_CHANGED=True` when proxy exit IP rotated
  - `city_profile_ip_changed_cleanup` executed and preserved only lightweight Google cookies
- TTL cleanup validation confirmed:
  - expired `pedreira` profile record and directory were removed cleanly
- Full grouped `--once` validation confirmed with `Bauru`:
  - run completed cleanly
  - no captcha
  - `ads_found=2`
  - `ads_clicked=2`
  - WhatsApp landing interaction executed on the first ad
  - click summary log recorded `position=1` and `position=2`
  - no leftover runner/Chrome/chromedriver processes remained after exit

## Residual Risks

- Seed-cookie values are intentionally lightweight and may still need tuning based on real Google behavior.
- Risk scoring is implemented, but threshold tuning may need real traffic observation before finalizing weights.
- The current validations were focused and isolated; grouped soak validation is still the next practical step.

## Notes

- SeleniumBase-specific profile reuse was not a priority path in this pass because current config uses `use_seleniumbase=false`.
- Seed-cookie values are intentionally minimal and may need tuning from live captcha observations.
