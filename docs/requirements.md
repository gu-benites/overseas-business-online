# Requirements

## Objective

Improve browser trustworthiness for Google search runs on the x86_64 VPS by replacing the current fully-ephemeral cookie/profile model with a short-lived, city-scoped session strategy that remains coherent under automatic proxy IP rotation.

This work must reduce avoidable captcha pressure without introducing profile corruption, cleanup races, or cross-city state leakage.

## Context

The current flow is documented in [fluxo-atual-e-mapeamento.md](./fluxo-atual-e-mapeamento.md).

Current limitations:

- each run creates a fresh Chrome profile
- each run clears cookies, cache, localStorage, and sessionStorage at the end
- no reusable profile metadata exists
- no distinction exists between IP change during a run and IP change between runs
- cookie handling is all-or-nothing: either `cookies.txt` or nothing

## Functional Requirements

### 1. Profile Reuse Model

- The system must support a reusable browser profile keyed by `city_name`.
- The reusable profile must have a configurable TTL in minutes.
- The system must preserve isolation between cities.
- The system must keep the current per-run ephemeral model available as a fallback mode.

### 2. Profile Metadata

- The system must persist metadata for reusable profiles.
- Metadata must include at least:
  - `profile_key`
  - `city_name`
  - `rsw_id`
  - `profile_dir`
  - `created_at`
  - `last_used_at`
  - `last_proxy_ip`
  - `last_proxy_session_id`
  - `risk_score`
  - `last_seeded_at`
- Metadata updates must be safe under concurrent grouped runs.

### 3. IP-Rotation-Aware Behavior

- If the proxy exit IP changes during a run, the run must continue to abort as it does today.
- If the exit IP changed between runs using the same city profile, the system must perform selective hygiene instead of blindly reusing all prior state.
- The system must distinguish:
  - `mid-session IP change`
  - `between-run IP change`

### 4. Cookie and Storage Strategy

- The system must stop doing unconditional full cleanup for reusable profiles.
- The system must support at least these cleanup policies:
  - `ephemeral`
  - `city_profile_soft_cleanup`
  - `city_profile_ip_changed_cleanup`
  - `city_profile_recycle`
- The reusable profile path must preserve lightweight trust state when safe.
- The system must continue to support full cleanup for ephemeral runs.

### 5. Seed Cookie Strategy

- The system must support a minimal seed-cookie mechanism for cold city profiles.
- Seed cookies must be limited to lightweight consent/locale/preference data.
- The system must not depend on full `cookies.txt` replay for the new strategy.
- The click-based consent handler must remain as a fallback when seed cookies are absent or invalid.

### 6. Locale, Timezone, and Fingerprint Coherence

- Locale, `Accept-Language`, geolocation, and timezone must still be applied from the current proxy IP on every run.
- Reused profile state must not override current-run locale/timezone alignment.
- The new strategy must remain compatible with the current headless-first mode and isolated chromedriver-per-run mode.

### 7. Cleanup and Retention

- Cleanup must support persistent short-lived profiles without deleting healthy in-use city profiles.
- Cleanup must remove expired, orphaned, or recycled city profiles.
- Cleanup must remain concurrency-safe.

### 8. Configuration Surface

- The strategy must be controllable from configuration.
- New config should cover at least:
  - enable/disable reusable profiles
  - TTL
  - profile key mode
  - seed-cookie enablement
  - preserve consent cookies
  - preserve locale cookies
  - cleanup behavior on between-run IP change
  - recycle threshold / risk score threshold

## Non-Goals

- No long-lived full-day browser identity tied to a rotating proxy IP
- No full import/export of heavy Google session cookies across many hours
- No profile reuse shared across different cities
- No regression to the old cleanup race behavior

## Constraints

- Proxy IP rotation is normal and expected.
- Multiple grouped runs may execute concurrently.
- The solution must work with the current grouped runner and current click logging.
- The solution must not break existing `--once` runs.

## Acceptance Criteria

- City-scoped profiles are reused within TTL and recycled after TTL.
- A run with between-run IP change reuses the city profile only after selective hygiene.
- A run with mid-session IP change still aborts and marks the profile as risky.
- End-of-run cleanup no longer destroys reusable profiles by default.
- Consent handling works with:
  - seeded cold profile
  - unseeded cold profile
  - reused warm profile
- Concurrent grouped runs do not race and delete each other's reusable profiles.
- The new behavior is configurable and can be disabled cleanly.

## Success Metrics

- lower captcha rate per city
- lower captcha rate on first query of a cold run
- fewer repeated consent dialogs within the same city profile TTL
- no increase in profile corruption or cleanup-race incidents

