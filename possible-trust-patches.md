# Possible Trust Patches

This file tracks browser-trust and captcha-pressure patches for the x86_64 VPS branch.

Status legend:
- `[x]` implemented in this branch/worktree
- `[ ]` not implemented yet

## Already Implemented

- [x] Fix proxy-locale resolution so `country_to_locale.json` array values resolve to a single locale string instead of a stringified list.
- [x] Apply proxy locale consistently to Google start URL, browser language, and `Accept-Language`.
- [x] Apply proxy geolocation and timezone overrides through CDP.
- [x] Pin `undetected_chromedriver` startup to the installed Chrome major version on x86_64.
- [x] Attach SSH-launched runs to the persistent Xvfb display with `DISPLAY=:10` and `XAUTHORITY` fallback.
- [x] Make runtime cleanup concurrency-safe so one browser startup cannot delete another task's profile/plugin directories.
- [x] Tighten the Google cookie-dialog handler so it stops clicking arbitrary buttons unrelated to consent.
- [x] Recover from early local browser-session loss before clicks instead of failing the whole run immediately.
- [x] Add WhatsApp CTA detection so landing pages can interact with visible `wa.me` / WhatsApp-style links.
- [x] Rotate notebook-style window sizes instead of hardcoding every fallback to `1366x768`.
- [x] Restrict Linux user-agent selection to desktop Linux identities only. Android/mobile user agents are no longer used on Linux unless a real mobile-emulation path is added later.
- [x] Normalize selected Chrome/CriOS user-agent versions to the installed Chrome major version so the advertised version no longer drifts far behind the real browser.
- [x] Cap rotating window sizes to the real X display dimensions so viewport size does not exceed `screen.width` / `screen.height`.
- [x] Stop forcing CDP `platform=Linux` in the UA override payload for every session.
- [x] Prefer explicit realistic window sizing over `maximize_window()` on this Chrome 146 + Xvfb stack, since maximize is failing and was producing inconsistent fallbacks.

## High-Value Remaining Patches

- [ ] Add a real mobile-emulation mode before re-enabling Android or iPhone user agents.
- [ ] Expand the Xvfb screen to a larger coherent desktop size, such as `1920x1080`, if we want larger desktop fingerprints without impossible screen/viewport combinations.
- [ ] Send coherent `userAgentMetadata` / `Sec-CH-UA*` hints instead of relying on default or disabled client-hint behavior.
- [ ] Refresh `user_agents.txt` into a tighter, current desktop Linux pool so the branch stops sampling very old Chrome families.
- [ ] Audit the Chrome flag set against the old ARM/main behavior and remove any flags that unnecessarily increase fingerprint entropy.
- [ ] Compare browser-fingerprint outputs between the old ARM main branch and this x86 branch on leak-check sites, then patch deltas one by one.
- [ ] Tune proxy session reuse and provider settings if captcha pressure remains high after browser-identity fixes.
- [ ] Evaluate whether `identity_mode = native_linux` should become the default on x86_64 if the native Chrome fingerprint outperforms the curated UA pool.
- [ ] Re-check WebGL, canvas, and font surfaces on this VPS after the UA/window fixes, because x86_64 Chrome 146 may still differ materially from the old ARM stack.

## Current Working Theory

The biggest captcha driver on this VPS was the browser presenting a mixed identity:

- mobile Android user agent
- desktop Linux browser/runtime behavior
- no touch support
- desktop-sized or impossible viewport values
- Chrome version claims that did not match the installed browser

The implemented patches above remove the most obvious mixed-identity signals. If captcha volume is still materially higher than the ARM baseline after this, the next most likely causes are client hints, Chrome flag differences, or proxy reputation rather than locale alone.
