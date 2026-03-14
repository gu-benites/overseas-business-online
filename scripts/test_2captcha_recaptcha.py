#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time

import requests


CREATE_TASK_URL = "https://api.2captcha.com/createTask"
GET_TASK_RESULT_URL = "https://api.2captcha.com/getTaskResult"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Smoke test 2captcha with a standalone reCAPTCHA target."
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("TWOCAPTCHA_API_KEY", "").strip(),
        help="2captcha API key. Can also be provided via TWOCAPTCHA_API_KEY env var.",
    )
    parser.add_argument(
        "--site-url",
        default="https://www.google.com/recaptcha/api2/demo",
        help="Page URL containing the reCAPTCHA widget.",
    )
    parser.add_argument(
        "--site-key",
        default="6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
        help="reCAPTCHA sitekey from the target page.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Max seconds to wait for a solved token.",
    )
    parser.add_argument(
        "--poll",
        type=int,
        default=5,
        help="Polling interval in seconds.",
    )
    return parser.parse_args()


def fail(msg, code=1):
    print(msg)
    sys.exit(code)


def main():
    args = parse_args()
    if not args.api_key:
        fail("Missing API key. Pass --api-key or TWOCAPTCHA_API_KEY.")

    create_payload = {
        "clientKey": args.api_key,
        "task": {
            "type": "RecaptchaV2TaskProxyless",
            "websiteURL": args.site_url,
            "websiteKey": args.site_key,
        },
    }

    print("[1/3] createTask request")
    print(
        json.dumps(
            {
                "websiteURL": args.site_url,
                "websiteKey": args.site_key,
                "taskType": "RecaptchaV2TaskProxyless",
            },
            indent=2,
        )
    )

    try:
        create_resp = requests.post(CREATE_TASK_URL, json=create_payload, timeout=30)
        create_data = create_resp.json()
    except Exception as exp:
        fail(f"createTask call failed: {exp}")

    print("[2/3] createTask response")
    print(json.dumps(create_data, indent=2))
    if create_data.get("errorId") != 0:
        fail("createTask returned error.")

    task_id = create_data.get("taskId")
    if not task_id:
        fail("No taskId in createTask response.")

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        time.sleep(args.poll)
        try:
            result_resp = requests.post(
                GET_TASK_RESULT_URL,
                json={"clientKey": args.api_key, "taskId": task_id},
                timeout=30,
            )
            result_data = result_resp.json()
        except Exception as exp:
            fail(f"getTaskResult call failed: {exp}")

        status = result_data.get("status")
        print(f"[poll] status={status} payload={json.dumps(result_data)}")

        if result_data.get("errorId") not in (None, 0):
            fail("getTaskResult returned error.")
        if status == "ready":
            solution = result_data.get("solution", {})
            token = solution.get("gRecaptchaResponse") or solution.get("token")
            print("[3/3] solved")
            print(f"taskId={task_id}")
            print(f"token_prefix={token[:80] if token else '<empty>'}")
            print(f"cost={result_data.get('cost')}")
            return

    fail(f"Timed out waiting for solve. taskId={task_id}", code=2)


if __name__ == "__main__":
    main()
