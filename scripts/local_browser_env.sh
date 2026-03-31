#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_ROOT="$ROOT_DIR/.local-system/root"

export PYTHONPATH="$LOCAL_ROOT/usr/lib/python3.13:$LOCAL_ROOT/usr/lib/python3.13/lib-dynload${PYTHONPATH:+:$PYTHONPATH}"
export LD_LIBRARY_PATH="$LOCAL_ROOT/usr/lib/aarch64-linux-gnu:$LOCAL_ROOT/lib/aarch64-linux-gnu:$LOCAL_ROOT/usr/lib/chromium${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TCL_LIBRARY="$LOCAL_ROOT/usr/share/tcltk/tcl8.6"
export TK_LIBRARY="$LOCAL_ROOT/usr/share/tcltk/tk8.6"
export CHROME_BINARY="$LOCAL_ROOT/usr/lib/chromium/chromium"
export PATH="$LOCAL_ROOT/usr/bin:$PATH"

if [[ -z "${DISPLAY:-}" && -S /tmp/.X11-unix/X10 ]]; then
    export DISPLAY=:10
fi

if [[ "${DISPLAY:-}" == ":10" && -z "${XAUTHORITY:-}" && -f "$HOME/.Xauthority-xvfb-10" ]]; then
    export XAUTHORITY="$HOME/.Xauthority-xvfb-10"
fi
