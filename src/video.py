"""Composite the still quote card into a Reel: a slow Ken Burns zoom over
config.REEL_DURATION_SECONDS, with the picked track underneath (faded in
and out), encoded to Instagram's Reels requirements.
"""

import subprocess
import sys

import config

FPS = 25
CRF = 23
MAX_VIDEO_BITRATE = "3M"
BUFSIZE = "6M"
AUDIO_BITRATE = "96k"
FADE_IN = 0.5
FADE_OUT = 0.7
MAX_SIZE_MB = 8


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{' '.join(cmd)}\n\n{result.stderr[-2000:]}")
    return result


def build_reel(still_image_path, audio_path, out_path, duration=None):
    duration = duration or config.REEL_DURATION_SECONDS
    fade_out_start = duration - FADE_OUT

    # Ken Burns: upscale the still frame, then zoompan a slow continuous
    # zoom centered on the frame, cut to `duration`. d=1 keeps zoompan's
    # internal zoom/x/y state advancing per output frame against the
    # single looped input frame (the standard ffmpeg static-image zoom
    # idiom) rather than resetting every input frame.
    video_filter = (
        "scale=w=8*iw:h=8*ih,"
        "zoompan=z='min(zoom+0.0008,1.15)':d=1:"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"s={config.CARD_WIDTH}x{config.CARD_HEIGHT}:fps={FPS},"
        "format=yuv420p"
    )
    audio_filter = f"afade=t=in:st=0:d={FADE_IN},afade=t=out:st={fade_out_start}:d={FADE_OUT}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(still_image_path),
        "-i", str(audio_path),
        "-filter:v", video_filter,
        "-filter:a", audio_filter,
        "-t", str(duration),
        "-c:v", "libx264", "-crf", str(CRF),
        "-maxrate", MAX_VIDEO_BITRATE, "-bufsize", BUFSIZE,
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-movflags", "+faststart",
        "-shortest",
        str(out_path),
    ]
    _run(cmd)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    assert size_mb < MAX_SIZE_MB, f"Reel exceeds Instagram's {MAX_SIZE_MB}MB limit ({size_mb:.1f}MB)"
    return out_path


def extract_thumbnail(video_path, out_jpg_path, at_seconds=1.0):
    """Grab a single frame for the job-summary preview."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(at_seconds), "-i", str(video_path),
        "-vframes", "1", "-q:v", "3",
        str(out_jpg_path),
    ]
    _run(cmd)
    return out_jpg_path
