"""Gate a GitHub Actions job on an Approve/Reject button press in Telegram.

Sends a message with an inline keyboard, then long-polls getUpdates for a
matching callback_query from the configured chat. Exits 0 on approve, 1 on
reject or timeout, so a job running this can gate a downstream `needs:`.
"""
import argparse
import json
import os
import sys
import time

import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def call(token, method, **params):
    resp = requests.post(TELEGRAM_API.format(token=token, method=method), json=params, timeout=35)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram API error on {method}: {body}")
    return body["result"]


def latest_update_offset(token):
    result = call(token, "getUpdates", limit=1, offset=-1)
    if not result:
        return None
    return result[0]["update_id"] + 1


def load_caption(path):
    try:
        with open(path) as f:
            data = json.load(f)
        caption = data.get("caption", "")
        return caption[:500] + ("…" if len(caption) > 500 else "")
    except (OSError, json.JSONDecodeError):
        return ""


def video_is_fetchable(url, attempts=6, delay=5):
    for _ in range(attempts):
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(delay)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--caption-file", required=True)
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--timeout-minutes", type=int, default=30)
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("::error::TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set", file=sys.stderr)
        sys.exit(1)
    chat_id = int(chat_id)

    caption = load_caption(args.caption_file)
    header = f"New Reel ready to publish — {args.date}\n\n{caption}"
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"approve:{args.run_id}"},
            {"text": "❌ Reject", "callback_data": f"reject:{args.run_id}"},
        ]]
    }

    offset = latest_update_offset(token)

    has_video = False
    if video_is_fetchable(args.video_url):
        try:
            sent = call(token, "sendVideo", chat_id=chat_id, video=args.video_url,
                        caption=f"{header}\n\nApprove to publish to Instagram?",
                        reply_markup=keyboard, supports_streaming=True)
            has_video = True
        except (RuntimeError, requests.RequestException) as exc:
            print(f"sendVideo failed, falling back to text: {exc}", file=sys.stderr)

    if not has_video:
        text = f"{header}\n\nPreview: {args.video_url}\n\nApprove to publish to Instagram?"
        sent = call(token, "sendMessage", chat_id=chat_id, text=text, reply_markup=keyboard)

    message_id = sent["message_id"]
    print(f"Sent approval request to Telegram chat {chat_id} (message {message_id}, video={has_video}).")

    deadline = time.monotonic() + args.timeout_minutes * 60
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        poll_timeout = max(1, min(25, int(remaining)))
        try:
            updates = call(token, "getUpdates", offset=offset, timeout=poll_timeout, allowed_updates=["callback_query"])
        except requests.RequestException as exc:
            print(f"Poll failed, retrying: {exc}", file=sys.stderr)
            time.sleep(3)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            cq = update.get("callback_query")
            if not cq:
                continue
            data = cq.get("data", "")
            from_id = cq.get("from", {}).get("id")
            if from_id != chat_id or ":" not in data:
                continue
            action, run_id = data.split(":", 1)
            if run_id != args.run_id or action not in ("approve", "reject"):
                continue

            responder = cq.get("from", {}).get("username") or cq.get("from", {}).get("first_name", "unknown")
            approved = action == "approve"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Approved ✅" if approved else "Rejected ❌")
            status_line = f"{'✅ Approved' if approved else '❌ Rejected'} by {responder}"
            if has_video:
                call(token, "editMessageCaption", chat_id=chat_id, message_id=message_id,
                     caption=f"{header}\n\n{status_line}")
            else:
                call(token, "editMessageText", chat_id=chat_id, message_id=message_id,
                     text=f"{text}\n\n{status_line}")

            summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary_path:
                with open(summary_path, "a") as f:
                    f.write(f"\nTelegram approval: **{'approved' if approved else 'rejected'}** by {responder}\n")

            sys.exit(0 if approved else 1)

    if has_video:
        call(token, "editMessageCaption", chat_id=chat_id, message_id=message_id,
             caption=f"{header}\n\n⏱️ Timed out waiting for a response.")
    else:
        call(token, "editMessageText", chat_id=chat_id, message_id=message_id,
             text=f"{text}\n\n⏱️ Timed out waiting for a response.")
    print("::error::Timed out waiting for Telegram approval.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
