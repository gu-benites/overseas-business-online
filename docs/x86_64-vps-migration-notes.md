# x86_64 VPS Migration Notes

## Context

This repo was moved from an older Arch Linux ARM VPS to a newer Ubuntu x86_64 VPS.

Validation command used on the new VPS:

```bash
cd /home/gustavo/overseas-business-online
./.venv/bin/python run_grouped_ad_clicker.py --once --group-city 'Pedreira'
```

Final result on this VPS:
- command completed successfully
- proxy/geolocation worked
- Google search flow loaded
- run finished with `Ads Found = 0`, so there was no click on that specific query/run

## Main VPS Changes

The new VPS was missing the basic runtime pieces that existed on the old one.

Installed on the VPS:

```bash
sudo apt-get install -y python3.12-venv python3-pip
sudo apt-get install -y /tmp/google-chrome-stable_current_amd64.deb
```

Why this was needed:
- `.venv` could not be created because `ensurepip` was missing
- there was no usable Chrome/Chromium binary on the server

## Main Repo Changes

### 1. Removed old hardcoded `/home/otavio` paths

File:
- `run_grouped_ad_clicker.py`

Changed to derive paths from:
- current repo root
- current user home directory

This fixed failures like:
- inability to create grouped runner log files
- stale detection markers pointing to the previous VPS layout

### 2. Fixed authenticated Xvfb usage on this server

Files:
- `webdriver.py`
- `streamlit_gui.py`
- `scripts/local_browser_env.sh`

Changed behavior:
- when `DISPLAY=:10` is used, the code now also exports `XAUTHORITY=$HOME/.Xauthority-xvfb-10` if available

Why this was needed:
- this VPS uses an authenticated persistent Xvfb display
- `DISPLAY=:10` alone was not enough

### 3. Fixed false display detection

File:
- `webdriver.py`

Change:
- added the missing `subprocess` import used by `_has_usable_display()`

Why this mattered:
- without that import, display detection silently failed
- the app incorrectly fell back to headless mode every time

### 4. Matched `undetected_chromedriver` to the installed Chrome version

File:
- `webdriver.py`

Change:
- detect the installed Chrome major version with `get_browser_major_version()`
- pass that version into `undetected_chromedriver` via `version_main=...`

Why this was needed:
- UC had cached a ChromeDriver for version `147`
- installed Chrome on this VPS was version `146`
- that mismatch caused `session not created` errors

### 5. Made window setup resilient under Xvfb

File:
- `webdriver.py`

Change:
- if `maximize_window()` fails, fall back to `1366x768`

Why this was needed:
- Chrome was starting correctly, but `maximize_window()` failed on this Xvfb session

## What Broke First On This VPS

In order, the main blockers were:

1. missing `.venv`
2. missing `python3.12-venv`
3. missing Chrome/Chromium
4. hardcoded old VPS paths
5. missing X authority for display `:10`
6. UC driver/browser version mismatch
7. `maximize_window()` failure under Xvfb

## Validation Notes

After the fixes:
- Chrome launched correctly
- proxy extension loaded correctly
- proxy IP lookup worked
- geolocation and timezone were applied
- screenshots were saved
- Google results were parsed
- the grouped runner completed normally on the new VPS

## Remaining Observation

The successful validation run did not find clickable ads for the tested `Pedreira` query. That is a data/result issue for that run, not a VPS bootstrap failure.
