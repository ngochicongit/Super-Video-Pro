from __future__ import annotations

import os
import hashlib
import tempfile
from collections.abc import Callable
from pathlib import Path

from newsvid_brain import TTSError

TRUSTED_VOICE_SHA256 = {
    "vi_VN-vais1000-medium": (
        "ec7c89e2c85f4d1edc24b6120c18aaf1bda614f06b511567eb9c7c0de15e2dab",
        "fafb9da1354ed4b77c31af228ed41fb41cd825c14cffa105454b25e6ae751ee0",
    )
}

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def validate_piper_voice(model_path: Path, voice: str) -> bool:
    config_path = model_path.with_suffix(model_path.suffix + ".json")
    if not model_path.is_file() or model_path.stat().st_size < 1_000_000 or not config_path.is_file(): return False
    expected = TRUSTED_VOICE_SHA256.get(voice)
    return expected is None or (_sha256(model_path), _sha256(config_path)) == expected


def ensure_piper_voice(model_path: Path, voice: str, *,
                       downloader: Callable[[str, Path], None] | None = None) -> None:
    config_path = model_path.with_suffix(model_path.suffix + ".json")
    if validate_piper_voice(model_path, voice):
        return
    if downloader is None:
        try:
            from piper.download_voices import download_voice
        except ImportError as exc:
            raise TTSError(
                "Piper chưa được cài. Cài dependency piper-tts rồi thử lại."
            ) from exc
        downloader = download_voice
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".piper-", dir=model_path.parent) as temporary:
        staging = Path(temporary)
        try:
            downloader(voice, staging)
        except Exception as exc:
            raise TTSError(f"Không thể tải giọng Piper '{voice}': {exc}") from exc
        staged_model = staging / model_path.name
        staged_config = staging / config_path.name
        if not staged_model.is_file() or staged_model.stat().st_size == 0 or not staged_config.is_file():
            raise TTSError(f"Bộ giọng Piper '{voice}' tải về không đầy đủ")
        expected = TRUSTED_VOICE_SHA256.get(voice)
        if expected and (_sha256(staged_model), _sha256(staged_config)) != expected:
            raise TTSError(f"Checksum bộ giọng Piper '{voice}' không hợp lệ")
        os.replace(staged_model, model_path)
        os.replace(staged_config, config_path)
