from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

import torch
import whisperx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile


MODEL_NAME = os.environ.get("NEWSVID_WHISPERX_MODEL", "small")
DEVICE = os.environ.get("NEWSVID_WHISPERX_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("NEWSVID_WHISPERX_COMPUTE_TYPE", "int8")
BATCH_SIZE = int(os.environ.get("NEWSVID_WHISPERX_BATCH_SIZE", "4"))

app = FastAPI(title="Super Video WhisperX", version="1")
_model = None
_aligners: dict[str, tuple[object, dict]] = {}
_lock = threading.Lock()


def _load_model():
    global _model
    with _lock:
        if _model is None:
            _model = whisperx.load_model(
                MODEL_NAME, DEVICE, compute_type=COMPUTE_TYPE,
                language=None if MODEL_NAME.endswith(".en") else "vi",
            )
    return _model


def _word_payload(result: dict) -> list[dict]:
    words = result.get("word_segments") or []
    if not words:
        for segment in result.get("segments", []):
            words.extend(segment.get("words") or [])
    return [
        {"word": str(item.get("word", "")).strip(),
         "start": float(item["start"]), "end": float(item["end"])}
        for item in words
        if item.get("word") and item.get("start") is not None and item.get("end") is not None
    ]


@app.get("/health")
def health() -> dict:
    return {
        "status": "ready", "service": "whisperx", "model": MODEL_NAME,
        "device": DEVICE, "compute_type": COMPUTE_TYPE,
        "cuda_available": bool(torch.cuda.is_available()),
    }


@app.get("/v1/models")
def models() -> dict:
    return {"data": [{"id": MODEL_NAME, "object": "model", "owned_by": "local"}]}


@app.post("/v1/audio/alignments")
def align_audio(
    file: UploadFile = File(...), model: str = Form(MODEL_NAME),
    language: str = Form("vi"), text: str = Form(""),
    response_format: str = Form("verbose_json"),
    timestamp_granularities: str = Form("word"),
) -> dict:
    del text, response_format, timestamp_granularities
    if model != MODEL_NAME:
        raise HTTPException(400, f"Model {model!r} is not loaded; available model is {MODEL_NAME!r}")
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="newsvid-whisperx-", suffix=suffix, delete=False) as stream:
            temp_path = Path(stream.name)
            while chunk := file.file.read(1024 * 1024):
                stream.write(chunk)
        audio = whisperx.load_audio(str(temp_path))
        result = _load_model().transcribe(audio, batch_size=BATCH_SIZE, language=language)
        detected_language = str(result.get("language") or language)
        try:
            with _lock:
                if detected_language not in _aligners:
                    _aligners[detected_language] = whisperx.load_align_model(
                        language_code=detected_language, device=DEVICE
                    )
                align_model, metadata = _aligners[detected_language]
            result = whisperx.align(
                result["segments"], align_model, metadata, audio, DEVICE,
                return_char_alignments=False,
            )
        except Exception:
            # WhisperX ASR timestamps remain real audio-derived timestamps when a
            # language-specific forced-alignment model is unavailable.
            pass
        words = _word_payload(result)
        if not words:
            raise HTTPException(422, "WhisperX produced no word timestamps")
        return {"text": " ".join(item["word"] for item in words),
                "language": detected_language, "words": words}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"WhisperX alignment failed: {exc}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
