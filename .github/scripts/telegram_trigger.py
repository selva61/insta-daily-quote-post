"""Poll Telegram for a /post command and dispatch the daily-post workflow.

Run on a schedule (see telegram-trigger.yml). Tracks the last processed
Telegram update_id in state/telegram_offset.json (committed by the workflow)
so restarts don't reprocess old messages or miss ones sent between runs.
"""
import json
import os
import sys

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
OFFSET_FILE = "state/telegram_offset.json"
WORKFLOW_FILE = "daily-post.yml"


def call(token, method, **params):
    resp = requests.post(TELEGRAM_API.format(token=token, method=method), json=params, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error on {method}: {body}")
    return body["result"]


def load_offset():
    try:
        with open(OFFSET_FILE) as f:
            return json.load(f).get("offset")
    except (OSError, json.JSONDecodeError):
        return None


def save_offset(offset):
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
    with open(OFFSET_FILE, "w") as f:
        json.dump({"offset": offset}, f)
        f.write("\n")


def dispatch_workflow(repo, gh_token, dry_run):
    resp = requests.post(
        f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches",
        headers={
            "Authorization": f"Bearer {gh_token}",
            "Accept": "application/vnd.github+json",
        },
        json={"ref": "main", "inputs": {"dry_run": "true" if dry_run else "false"}},
        timeout=20,
    )
    resp.raise_for_status()


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    gh_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not all([token, chat_id, gh_token, repo]):
        print("::error::TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GITHUB_TOKEN and GITHUB_REPOSITORY must be set", file=sys.stderr)
        sys.exit(1)
    chat_id = int(chat_id)

    offset = load_offset()
    updates = call(token, "getUpdates", offset=offset, timeout=0, allowed_updates=["message"])
    if not updates:
        print("No new Telegram messages.")
        return

    triggered = False
    for update in updates:
        offset = update["update_id"] + 1
        message = update.get("message")
        if not message or message.get("chat", {}).get("id") != chat_id:
            continue
        text = (message.get("text") or "").strip().lower()
        if not text.startswith("/post"):
            continue

        dry_run = "dry" in text
        print(f"Received {text!r} — dispatching daily-post.yml (dry_run={dry_run}).")
        try:
            dispatch_workflow(repo, gh_token, dry_run)
            call(token, "sendMessage", chat_id=chat_id,
                 text=f"🚀 Triggered today's post{' (dry run)' if dry_run else ''}.")
            triggered = True
        except requests.RequestException as exc:
            print(f"::error::Failed to dispatch workflow: {exc}", file=sys.stderr)
            call(token, "sendMessage", chat_id=chat_id, text=f"⚠️ Failed to trigger workflow: {exc}")

    save_offset(offset)
    if triggered:
        print("Dispatched daily-post.yml.")


if __name__ == "__main__":
    main()
