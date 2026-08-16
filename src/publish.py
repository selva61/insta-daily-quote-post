#!/usr/bin/env python3
"""Publish a rendered Reel to Instagram via the Instagram API with
Instagram Login (host: graph.instagram.com — no Facebook Page needed).

Two-step flow: create a media container from a public video URL, poll
until it finishes processing, then publish it. Video (Reels) processing
takes noticeably longer than photo processing did.

Usage:
    python src/publish.py --validate
    python src/publish.py --video-url <public mp4 url> --caption-file out/2026-08-16.json
"""

import argparse
import json
import sys
import time

import requests

import config

BASE = f"https://graph.instagram.com/{config.IG_API_VERSION}"
POLL_ATTEMPTS = 40
POLL_DELAY_SECONDS = 8


def _require_credentials():
    missing = [name for name, val in [
        ("IG_USER_ID", config.IG_USER_ID),
        ("IG_ACCESS_TOKEN", config.IG_ACCESS_TOKEN),
    ] if not val]
    if missing:
        sys.exit(f"Missing required env vars: {', '.join(missing)}")


def validate():
    """Confirm the token is alive and points at the expected account."""
    _require_credentials()
    resp = requests.get(
        "https://graph.instagram.com/me",
        params={"fields": "user_id,username", "access_token": config.IG_ACCESS_TOKEN},
        timeout=20,
    )
    if resp.status_code != 200:
        sys.exit(f"Token validation failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    print(f"Token OK — authenticated as @{data.get('username')} (user_id={data.get('user_id')})")
    if str(data.get("user_id")) != str(config.IG_USER_ID):
        print(
            f"[warn] IG_USER_ID secret ({config.IG_USER_ID}) does not match the token's "
            f"user_id ({data.get('user_id')}) — double-check the secret.",
            file=sys.stderr,
        )
    return data


def create_container(video_url: str, caption: str) -> str:
    resp = requests.post(
        f"{BASE}/{config.IG_USER_ID}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": config.IG_ACCESS_TOKEN,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"Container creation failed ({resp.status_code}): {resp.text}")
    container_id = resp.json()["id"]
    print(f"Created container {container_id}")
    return container_id


def wait_until_ready(container_id: str):
    for attempt in range(1, POLL_ATTEMPTS + 1):
        resp = requests.get(
            f"{BASE}/{container_id}",
            params={
                "fields": "status_code,status",
                "access_token": config.IG_ACCESS_TOKEN,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            sys.exit(f"Status poll failed ({resp.status_code}): {resp.text}")
        body = resp.json()
        status = body.get("status_code")
        print(f"  poll {attempt}/{POLL_ATTEMPTS}: status_code={status} full={json.dumps(body)}")
        if status == "FINISHED":
            return
        if status == "ERROR":
            sys.exit(f"Container {container_id} failed processing: {json.dumps(body)}")
        time.sleep(POLL_DELAY_SECONDS)
    sys.exit(f"Container {container_id} never reached FINISHED after {POLL_ATTEMPTS} polls")


def publish_container(container_id: str) -> str:
    resp = requests.post(
        f"{BASE}/{config.IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": config.IG_ACCESS_TOKEN},
        timeout=30,
    )
    if resp.status_code != 200:
        sys.exit(f"Publish failed ({resp.status_code}): {resp.text}")
    media_id = resp.json()["id"]
    print(f"Published: media id {media_id}")
    return media_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true", help="only validate credentials, don't post")
    parser.add_argument("--video-url", type=str, help="publicly reachable MP4 URL")
    parser.add_argument("--caption-file", type=str, help="path to the .json sidecar written by generate.py")
    args = parser.parse_args()

    if args.validate:
        validate()
        return

    if not args.video_url or not args.caption_file:
        sys.exit("--video-url and --caption-file are required to publish")

    _require_credentials()

    with open(args.caption_file) as f:
        meta = json.load(f)
    caption = meta["caption"]

    container_id = create_container(args.video_url, caption)
    wait_until_ready(container_id)
    publish_container(container_id)


if __name__ == "__main__":
    main()
