# Anime Subtitle Backend

Offline FastAPI backend for converting Japanese anime/video files into English `.srt` subtitles and hard-subbed MP4 output.

## Features

- FFmpeg audio extraction to mono 16 kHz WAV.
- Japanese transcription with `faster-whisper`.
- Subtitle segment cleanup, merge/split refinement, timing padding, reading-speed checks, and overlap prevention.
- Local open-source Japanese-to-English translation with Hugging Face `transformers`.
- SRT generation with readable wrapping.
- FFmpeg hard-sub rendering with bottom-centered anime-style subtitles.
- SQLite-backed async job tracking.
- CLI for local testing.

## Setup

System FFmpeg is preferred if available on `PATH`. If it is not installed, the app falls back to the `imageio-ffmpeg` binary from `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For a 16 GB laptop, keep the defaults:

```powershell
$env:WHISPER_MODEL_SIZE="small"
$env:WHISPER_DEVICE="auto"
$env:WHISPER_COMPUTE_TYPE="auto"
$env:TRANSLATION_MODEL="Helsinki-NLP/opus-mt-ja-en"
$env:TRANSLATION_DEVICE="cpu"
```

On a CUDA GPU machine, you can use:

```powershell
$env:WHISPER_MODEL_SIZE="medium"
$env:WHISPER_DEVICE="cuda"
$env:WHISPER_COMPUTE_TYPE="float16"
```

## Run API

```powershell
uvicorn app.main:app --reload
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

## Run Desktop App

```powershell
python desktop_app.py
```

The desktop app starts the local FastAPI backend and opens a native window for uploading one video, tracking progress, previewing the completed MP4, and downloading the `.srt`.

The UI lets you choose the Whisper transcription model per video (`tiny` through `large-v3`) and the Japanese-to-English translation model before starting a job.

## API

- `GET /health`
- `POST /jobs` with form field `file`
- `POST /jobs/batch` with form field `files`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/subtitle`
- `GET /jobs/{job_id}/video`

## CLI Demo

Put a sample video at `examples/input/sample.mp4`, then run:

```powershell
python cli.py process examples/input/sample.mp4 --output-dir outputs/demo
```

Expected outputs are created under a generated job folder:

- `sample.en.srt`
- `sample.hardsub.mp4`

## Translation Models

Default:

- `Helsinki-NLP/opus-mt-ja-en`: small, Apache-2.0, good local default.

Alternatives:

- `staka/fugumt-ja-en`: Japanese-English Marian model, CC-BY-SA-4.0.
- `facebook/nllb-200-distilled-600M`: stronger multilingual model, heavier, CC-BY-NC-4.0.

## Notes

The 2-5 minute target for 10-15 minute videos requires a CUDA GPU. CPU processing is supported but slower, especially during transcription.
