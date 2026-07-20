#!/usr/bin/env python3
"""
Whisper transcription fallback service for the YouTube digest -> mydefilife
article pipeline. Called by n8n only when a video has no official YouTube
captions (the HTML-scrape approach in the n8n workflow can't find any).

POST /transcript  {"videoUrl": "https://youtube.com/watch?v=..."}
  -> downloads audio only via yt-dlp, transcribes with faster-whisper (base model, CPU),
     returns {"transcript": "...", "hasTranscript": true/false, "method": "whisper"}

GET /health -> {"status": "ok"}

Auth: shared secret via X-API-Key header (set WHISPER_API_KEY env var).
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path

from flask import Flask, request, jsonify
from faster_whisper import WhisperModel

app = Flask(__name__)

API_KEY = os.environ.get("WHISPER_API_KEY", "")
MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")
YT_DLP_BIN = os.environ.get("YT_DLP_BIN", str(Path(__file__).parent / "venv" / "bin" / "yt-dlp"))
COOKIES_FILE = os.environ.get("YT_COOKIES_FILE", str(Path(__file__).parent / "cookies.txt"))

print(f"Loading faster-whisper model: {MODEL_SIZE} (CPU, int8)...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("Model loaded.")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_SIZE})


@app.route("/transcript", methods=["POST"])
def transcript():
    if API_KEY:
        if request.headers.get("X-API-Key") != API_KEY:
            return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    video_url = data.get("videoUrl", "").strip()
    if not video_url:
        return jsonify({"error": "videoUrl is required"}), 400

    workdir = tempfile.mkdtemp(prefix="whisper_")
    try:
        audio_path = os.path.join(workdir, "audio.%(ext)s")
        cmd = [
            YT_DLP_BIN,
            "-x", "--audio-format", "mp3", "--audio-quality", "5",
            "-o", audio_path,
            "--no-playlist",
            "--js-runtimes", "node",  # Deno is yt-dlp's default JS runtime for the n-challenge solver; not installed here, Node is
        ]
        if os.path.exists(COOKIES_FILE):
            cmd += ["--cookies", COOKIES_FILE]
        cmd.append(video_url)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return jsonify({
                "transcript": "",
                "hasTranscript": False,
                "method": "whisper",
                "error": f"yt-dlp failed: {result.stderr[-500:]}",
            })

        mp3_files = list(Path(workdir).glob("audio.mp3"))
        if not mp3_files:
            return jsonify({
                "transcript": "",
                "hasTranscript": False,
                "method": "whisper",
                "error": "yt-dlp produced no audio file",
            })

        segments, info = model.transcribe(str(mp3_files[0]), beam_size=5, language="en")
        text = " ".join(seg.text.strip() for seg in segments).strip()

        return jsonify({
            "transcript": text[:12000] if text else "",
            "hasTranscript": len(text) > 0,
            "method": "whisper",
            "detectedLanguage": info.language,
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            "transcript": "", "hasTranscript": False, "method": "whisper",
            "error": "yt-dlp audio download timed out (>5min)",
        })
    except Exception as e:
        return jsonify({
            "transcript": "", "hasTranscript": False, "method": "whisper",
            "error": str(e),
        })
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3600))
    app.run(host="0.0.0.0", port=port)
