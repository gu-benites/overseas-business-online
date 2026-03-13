import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


ROOT = Path.cwd()
load_dotenv(ROOT / ".env")
CONFIG_PATH = ROOT / "config.json"
LOG_DIR = ROOT / ".streamlit_logs"
SMOKE_TEST_SCREENSHOT_DIR = ROOT / ".streamlit_uploads" / "smoke_test_screenshots"


REQUIRED_FIELDS = {
    "paths": {"query_file", "proxy_file", "user_agents", "filtered_domains"},
    "webdriver": {
        "proxy",
        "auth",
        "incognito",
        "country_domain",
        "language_from_proxy",
        "ss_on_exception",
        "window_size",
        "shift_windows",
        "use_seleniumbase",
    },
    "behavior": {
        "query",
        "ad_page_min_wait",
        "ad_page_max_wait",
        "nonad_page_min_wait",
        "nonad_page_max_wait",
        "max_scroll_limit",
        "check_shopping_ads",
        "excludes",
        "random_mouse",
        "custom_cookies",
        "click_order",
        "browser_count",
        "multiprocess_style",
        "loop_wait_time",
        "wait_factor",
        "running_interval_start",
        "running_interval_end",
        "2captcha_apikey",
        "hooks_enabled",
        "telegram_enabled",
        "send_to_android",
        "request_boost",
    },
}


def load_config() -> dict[str, Any] | None:
    if not CONFIG_PATH.exists():
        return None

    try:
        with open(CONFIG_PATH, encoding="utf-8") as config_file:
            return json.load(config_file)
    except json.JSONDecodeError:
        return None


def validate_config(config: dict[str, Any]) -> list[str]:
    missing: list[str] = []

    for section, required_keys in REQUIRED_FIELDS.items():
        if section not in config:
            missing.append(section)
            continue

        section_value = config[section]
        if not isinstance(section_value, dict):
            missing.append(f"{section} (invalid type)")
            continue

        for key in required_keys:
            if key not in section_value:
                missing.append(f"{section}.{key}")

    return missing


def save_config(config: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=4)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def start_process(script: str, extra_args: list[str] | None = None, process_key: str | None = None) -> None:
    key = process_key or Path(script).stem
    jobs = st.session_state.setdefault("jobs", {})
    existing_job = jobs.get(key)

    if existing_job:
        process = existing_job["proc"]
        if process.poll() is None:
            st.warning(f"{key} is already running.")
            return
        _stop_job(existing_job)
        jobs.pop(key, None)

    LOG_DIR.mkdir(exist_ok=True)
    args = [sys.executable, str(ROOT / script)]
    if extra_args:
        args.extend(extra_args)

    if os.name == "posix" and not os.environ.get("DISPLAY"):
        xvfb_run = shutil.which("xvfb-run")
        if xvfb_run:
            args = [xvfb_run, "-a", *args]

    log_path = LOG_DIR / f"{key}.log"
    try:
        log_file = open(log_path, "a", encoding="utf-8")
        process = subprocess.Popen(
            args, cwd=str(ROOT), stdout=log_file, stderr=subprocess.STDOUT
        )
    except OSError as exc:
        st.error(f"Failed to start {script}: {exc}")
        return

    jobs[key] = {
        "proc": process,
        "log": log_path,
        "args": args,
        "log_file": log_file,
    }


def _stop_job(job: dict[str, Any]) -> None:
    proc = job["proc"]
    if proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            pass

    try:
        job["log_file"].close()
    except Exception:
        pass


def stop_process(process_key: str) -> None:
    jobs = st.session_state.setdefault("jobs", {})
    job = jobs.get(process_key)
    if not job:
        st.warning(f"No running job found for {process_key}.")
        return

    _stop_job(job)
    jobs.pop(process_key, None)


def read_recent_lines(log_file: Path, limit: int = 30) -> str:
    if not log_file.exists():
        return ""

    try:
        lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return ""

    return "\n".join(lines[-limit:])


def get_smoke_test_screenshots(limit: int = 10) -> list[Path]:
    if not SMOKE_TEST_SCREENSHOT_DIR.exists():
        return []

    screenshots = sorted(
        SMOKE_TEST_SCREENSHOT_DIR.glob("*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return screenshots[:limit]


def to_int(raw: Any, fallback: int) -> int:
    if isinstance(raw, int):
        return raw
    try:
        return int(raw)
    except (TypeError, ValueError):
        return fallback


def to_float(raw: Any, fallback: float) -> float:
    if isinstance(raw, float | int):
        return float(raw)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return fallback


def to_text(raw: Any) -> str:
    if raw is None:
        return ""
    return str(raw)


def _build_keyword_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "language": {"type": "string"},
            "market": {"type": "string"},
            "seed_query": {"type": "string"},
            "keywords": {
                "type": "array",
                "minItems": 10,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "term": {"type": "string"},
                        "est_search_volume": {"type": "integer"},
                        "est_cpc": {"type": "number"},
                        "currency": {"type": "string"},
                        "intent": {"type": "string"},
                        "confidence": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": [
                        "term",
                        "est_search_volume",
                        "est_cpc",
                        "currency",
                        "intent",
                        "confidence",
                        "rationale",
                    ],
                },
            },
        },
        "required": ["language", "market", "seed_query", "keywords"],
    }


def _extract_json_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    try:
        raw = response.model_dump()
    except Exception:
        raw = {}

    output = raw.get("output", [])
    for item in output:
        content = item.get("content", [])
        for part in content:
            if part.get("type") == "output_text":
                text_value = part.get("text", "")
                if text_value.strip():
                    return text_value
    return ""


def generate_keywords_with_openai(seed_query: str, model: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
    if OpenAI is None:
        raise RuntimeError("OpenAI SDK is not installed. Add `openai` to requirements.")

    client = OpenAI(api_key=api_key)
    system_prompt = (
        "You are a paid-search keyword strategist for Brazil focused on desentupidora services. "
        "Generate terms in Portuguese (pt-BR) only. "
        "Infer a city from the seed query. "
        "The first keyword must be exactly: 'desentupidora <cidade>' (with inferred city). "
        "The second keyword must be exactly: 'desentupidora em <cidade>' (with inferred city). "
        "Keywords 3-10 must remain focused on the same inferred city (never switch to other cities), "
        "while varying naturally and prioritizing the best estimated volume/CPC opportunities relevant to desentupidora services. "
        "Do not use external tools; provide realistic estimates and concise rationale."
    )
    user_prompt = (
        f"Seed query: {seed_query}\n"
        "Return exactly 10 keyword objects in ranked order. "
        "Constraint: keywords[0].term = 'desentupidora <cidade>' and keywords[1].term = 'desentupidora em <cidade>', "
        "replacing <cidade> with the inferred city from the seed query. "
        "For keywords[2]..keywords[9], use free high-volume/high-CPC variations but keep the same inferred city and do not introduce other cities. "
        "Do not output '<cidade>' literally. "
        "Market: Brazil. Language: pt-BR. Currency: BRL."
    )

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "keyword_generation_result",
                "strict": True,
                "schema": _build_keyword_schema(),
            }
        },
    )

    json_text = _extract_json_text(response)
    if not json_text:
        raise RuntimeError("OpenAI response did not include structured JSON output text.")

    payload = json.loads(json_text)
    keywords = payload.get("keywords", [])
    if len(keywords) != 10:
        raise RuntimeError("Structured output did not return exactly 10 keywords.")
    return payload


st.set_page_config(page_title="Google Ad Clicker Dashboard", layout="wide")


if "jobs" not in st.session_state:
    st.session_state["jobs"] = {}


config = load_config()

st.title("Google Ad Clicker Dashboard")
st.caption("Desktop GUI parity: config editor and script launcher in the browser.")

if not config:
    st.error("config.json not found or invalid JSON.")
    st.stop()

missing_fields = validate_config(config)
if missing_fields:
    st.error("config.json is missing required fields: " + ", ".join(missing_fields))
    st.stop()


paths = config["paths"]
webdriver = config["webdriver"]
behavior = config["behavior"]

with st.expander("Settings", expanded=True):
    with st.form("settings_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            query_file = st.text_input("Query file", value=to_text(paths.get("query_file")))
        with c2:
            proxy_file = st.text_input("Proxy file", value=to_text(paths.get("proxy_file")))
        with c3:
            user_agents = st.text_input("User agents", value=to_text(paths.get("user_agents")))
        with c4:
            filtered_domains = st.text_input("Filtered domains", value=to_text(paths.get("filtered_domains")))

        st.divider()

        d1, d2, d3 = st.columns(3)
        with d1:
            webdriver_proxy = st.text_input("Proxy", value=to_text(webdriver.get("proxy")))
            webdriver_auth = st.checkbox("Proxy Auth", value=_to_bool(webdriver.get("auth")))
            webdriver_incognito = st.checkbox("Incognito", value=_to_bool(webdriver.get("incognito")))
            webdriver_country_domain = st.checkbox(
                "Country Domain", value=_to_bool(webdriver.get("country_domain"))
            )

        with d2:
            webdriver_window_size = st.text_input("Window size", value=to_text(webdriver.get("window_size")))
            webdriver_language_from_proxy = st.checkbox(
                "Language From Proxy", value=_to_bool(webdriver.get("language_from_proxy"))
            )
            webdriver_ss_on_exception = st.checkbox(
                "SS on Exception", value=_to_bool(webdriver.get("ss_on_exception"))
            )

        with d3:
            webdriver_shift_windows = st.checkbox("Shift windows", value=_to_bool(webdriver.get("shift_windows")))
            webdriver_use_seleniumbase = st.checkbox(
                "Use SeleniumBase with UC Mode", value=_to_bool(webdriver.get("use_seleniumbase"))
            )

        st.divider()

        ai_seed_query = st.text_input("AI Seed Query (pt-BR)", value=to_text(behavior.get("query")), key="ai_seed_query")
        ad_page_min_wait = st.number_input(
            "Ad page min wait", min_value=0, value=to_int(behavior.get("ad_page_min_wait"), 10)
        )
        ad_page_max_wait = st.number_input(
            "Ad page max wait", min_value=0, value=to_int(behavior.get("ad_page_max_wait"), 15)
        )
        nonad_page_min_wait = st.number_input(
            "Non-ad page min wait", min_value=0, value=to_int(behavior.get("nonad_page_min_wait"), 15)
        )
        nonad_page_max_wait = st.number_input(
            "Non-ad page max wait", min_value=0, value=to_int(behavior.get("nonad_page_max_wait"), 20)
        )
        max_scroll_limit = st.number_input(
            "Max scroll limit", min_value=0, value=to_int(behavior.get("max_scroll_limit"), 0)
        )
        click_order = st.number_input("Click order", min_value=1, max_value=5, value=to_int(behavior.get("click_order"), 5))
        browser_count = st.number_input(
            "Browser count", min_value=0, value=to_int(behavior.get("browser_count"), 2)
        )
        multiprocess_style = st.number_input(
            "Multiprocess style", min_value=1, max_value=2, value=to_int(behavior.get("multiprocess_style"), 1)
        )
        loop_wait_time = st.number_input(
            "Loop wait time", min_value=0, value=to_int(behavior.get("loop_wait_time"), 60)
        )
        wait_factor = st.number_input(
            "Wait factor",
            min_value=0.1,
            max_value=5.0,
            step=0.1,
            value=float(to_float(behavior.get("wait_factor"), 1.0)),
        )

        behavior_check_shopping_ads = st.checkbox(
            "Check shopping ads", value=_to_bool(behavior.get("check_shopping_ads"))
        )
        behavior_random_mouse = st.checkbox("Random mouse", value=_to_bool(behavior.get("random_mouse")))
        behavior_custom_cookies = st.checkbox("Custom cookies", value=_to_bool(behavior.get("custom_cookies")))
        behavior_hooks_enabled = st.checkbox("Hooks enabled", value=_to_bool(behavior.get("hooks_enabled")))
        behavior_telegram_enabled = st.checkbox("Telegram enabled", value=_to_bool(behavior.get("telegram_enabled")))
        behavior_send_to_android = st.checkbox("Send to Android", value=_to_bool(behavior.get("send_to_android")))
        behavior_request_boost = st.checkbox("Request boost", value=_to_bool(behavior.get("request_boost")))

        excludes = st.text_input("Excludes", value=to_text(behavior.get("excludes")), key="excludes_field")
        twocaptcha_apikey = st.text_input("2captcha API Key", value=to_text(behavior.get("2captcha_apikey")))
        running_interval_start = st.text_input(
            "Running interval start", value=to_text(behavior.get("running_interval_start"))
        )
        running_interval_end = st.text_input(
            "Running interval end", value=to_text(behavior.get("running_interval_end"))
        )

        if st.form_submit_button("SAVE CONFIGURATION"):
            config["paths"] = {
                "query_file": query_file,
                "proxy_file": proxy_file,
                "user_agents": user_agents,
                "filtered_domains": filtered_domains,
            }
            config["webdriver"] = {
                "proxy": webdriver_proxy,
                "auth": webdriver_auth,
                "incognito": webdriver_incognito,
                "country_domain": webdriver_country_domain,
                "language_from_proxy": webdriver_language_from_proxy,
                "ss_on_exception": webdriver_ss_on_exception,
                "window_size": webdriver_window_size,
                "shift_windows": webdriver_shift_windows,
                "use_seleniumbase": webdriver_use_seleniumbase,
            }
            config["behavior"] = {
                "query": "",
                "ad_page_min_wait": ad_page_min_wait,
                "ad_page_max_wait": ad_page_max_wait,
                "nonad_page_min_wait": nonad_page_min_wait,
                "nonad_page_max_wait": nonad_page_max_wait,
                "max_scroll_limit": max_scroll_limit,
                "check_shopping_ads": behavior_check_shopping_ads,
                "excludes": excludes,
                "random_mouse": behavior_random_mouse,
                "custom_cookies": behavior_custom_cookies,
                "click_order": click_order,
                "browser_count": browser_count,
                "multiprocess_style": multiprocess_style,
                "loop_wait_time": loop_wait_time,
                "wait_factor": to_float(wait_factor, 1.0),
                "running_interval_start": running_interval_start,
                "running_interval_end": running_interval_end,
                "2captcha_apikey": twocaptcha_apikey,
                "hooks_enabled": behavior_hooks_enabled,
                "telegram_enabled": behavior_telegram_enabled,
                "send_to_android": behavior_send_to_android,
                "request_boost": behavior_request_boost,
            }
            save_config(config)
            st.success("Saved config.json")

st.subheader("AI Keyword Generator")
selected_model = st.selectbox(
    "OpenAI model",
    options=["gpt-5", "gpt-5-mini", "gpt-5-nano"],
    index=1,
    key="ai_model",
)

if st.button("Generate AI Terms", key="generate_ai_terms"):
    current_seed = to_text(st.session_state.get("ai_seed_query", "")).strip()
    current_query_file = to_text(query_file).strip()
    if not current_seed:
        st.error("AI Seed Query is required.")
    elif not current_query_file:
        st.error("Query file path is required.")
    else:
        try:
            generated = generate_keywords_with_openai(current_seed, selected_model)
            st.session_state["generated_keywords_payload"] = generated
            st.success("Generated 10 keyword suggestions.")
        except Exception as exc:
            st.error(f"Failed to generate AI terms: {exc}")

generated_payload = st.session_state.get("generated_keywords_payload")
if generated_payload:
    st.caption("Preview generated structured output")
    st.dataframe(generated_payload.get("keywords", []), use_container_width=True)
    if st.button("Confirm and overwrite query_file", key="confirm_ai_terms_overwrite"):
        current_query_file = to_text(query_file).strip()
        target_path = Path(current_query_file)
        keywords = generated_payload.get("keywords", [])
        terms = [to_text(item.get("term", "")).strip() for item in keywords if to_text(item.get("term", "")).strip()]
        if len(terms) != 10:
            st.error("Expected exactly 10 valid terms before writing to query_file.")
        elif not current_query_file:
            st.error("Query file path is required.")
        else:
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text("\n".join(terms) + "\n", encoding="utf-8")
                st.success(f"query_file overwritten with 10 terms: {target_path}")
            except Exception as exc:
                st.error(f"Failed to write query_file: {exc}")

st.subheader("Actions")
smoke_test_query = st.text_input(
    "Smoke test query",
    value="desentupidora porto alegre zn",
    help="Optional. Runs a safe Google search smoke test and saves a screenshot when filled.",
)
action_1, action_2, action_3, action_4, action_5 = st.columns(5)
with action_1:
    if st.button("RUN ad_clicker.py"):
        start_process("ad_clicker.py")

with action_2:
    if st.button("RUN run_ad_clicker.py"):
        start_process("run_ad_clicker.py")

with action_3:
    if st.button("RUN run_in_loop.py"):
        start_process("run_in_loop.py")

with action_4:
    if st.button("GENERATE CLICK REPORT"):
        start_process("ad_clicker.py", ["--report_clicks", "--excel"], process_key="report_clicks")

with action_5:
    if st.button("RUN smoke test"):
        smoke_args = ["--smoke_test"]
        current_smoke_query = smoke_test_query.strip()
        if current_smoke_query:
            smoke_args.extend(["--query", current_smoke_query])
        start_process("ad_clicker.py", smoke_args, process_key="smoke_test")


st.subheader("Smoke Test Screenshots")
screenshots = get_smoke_test_screenshots()
if screenshots and "selected_smoke_screenshot" not in st.session_state:
    st.session_state["selected_smoke_screenshot"] = str(screenshots[0])

if screenshots:
    list_col, preview_col = st.columns([1, 2])
    with list_col:
        for screenshot in screenshots:
            if st.button(screenshot.name, key=f"open_{screenshot.name}"):
                st.session_state["selected_smoke_screenshot"] = str(screenshot)
    with preview_col:
        selected_screenshot = Path(st.session_state["selected_smoke_screenshot"])
        if selected_screenshot.exists():
            st.image(str(selected_screenshot), caption=selected_screenshot.name, width="stretch")
else:
    st.info("No smoke test screenshots yet. Run a smoke test query to generate one.")


st.subheader("Running jobs")
tracked_processes = [
    ("ad_clicker.py", "ad_clicker.py"),
    ("run_ad_clicker.py", "run_ad_clicker.py"),
    ("run_in_loop.py", "run_in_loop.py"),
    ("ad_clicker.py", "generate click report"),
    ("ad_clicker.py", "smoke test"),
]

for script, label in tracked_processes:
    if label == "generate click report":
        key = "report_clicks"
    elif label == "smoke test":
        key = "smoke_test"
    else:
        key = Path(script).stem
    with st.container():
        job = st.session_state["jobs"].get(key)
        if job and job["proc"].poll() is not None:
            _stop_job(job)
            st.session_state["jobs"].pop(key, None)
            job = None
        if job and job["proc"].poll() is None:
            st.success(f"{label}: running (pid={job['proc'].pid})")
        else:
            st.info(f"{label}: not running")

        if st.button(f"Stop {label}", key=f"stop_{key}"):
            stop_process(key)

        if job:
            with st.expander(f"{label} log", expanded=False):
                st.code(read_recent_lines(job["log"]) or "No output yet")

st.caption("Tip: open http://localhost:8501 while running `streamlit run streamlit_gui.py`")
