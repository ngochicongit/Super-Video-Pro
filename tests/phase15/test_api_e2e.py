from __future__ import annotations

import hashlib
import shutil
import time
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from newsvid.api import create_app
from newsvid_brain import WordTiming

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "article_vi.html"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


class DeterministicLLM:
    cache_key = "deterministic-api-e2e-v1"

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        if "facts" in schema.get("properties", {}):
            return {"facts": [{
                "claim": "Trung tâm AI mới được công bố tại Thành phố Hồ Chí Minh.",
                "evidence": "được công bố tại Thành phố Hồ Chí Minh",
                "importance": .95,
                "confidence": .99,
            }]}
        sentence = "Trung tâm AI mới được công bố tại Thành phố Hồ Chí Minh phục vụ giáo dục và y tế"
        narration = f"{sentence} và hỗ trợ nghiên cứu tiếng Việt an toàn."
        return {"title": "Trung tâm AI mới", "segments": [
            {"type": "hook", "narration": narration, "fact_refs": ["fact_001"]},
            {"type": "body", "narration": narration, "fact_refs": ["fact_001"]},
            {"type": "outro", "narration": narration, "fact_refs": ["fact_001"]},
        ]}


class DeterministicTTS:
    name = "deterministic-wav"
    cache_key = "deterministic-wav-v1"

    def synthesize(self, text: str, output_path: Path, *, voice: str) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
            stream.writeframes(b"\x00\x00" * 12800)
        return output_path


class DeterministicAlignment:
    name = "deterministic-align"
    cache_key = "deterministic-align-v1"

    def align(self, audio_path: Path, text: str, *, language: str = "vi") -> list[WordTiming]:
        words = text.split(); step = .75 / max(1, len(words))
        return [WordTiming(word=word, start=index * step, end=(index + 1) * step)
                for index, word in enumerate(words)]


class OfflineVisual:
    cache_key = "offline-graphics-only-v1"

    def health_check(self) -> bool: return False


def wait(client: TestClient, response) -> dict:
    assert response.status_code == 200, response.text
    job = response.json()
    for _ in range(600):
        job = client.get(f"/jobs/{job['job_id']}").json()
        if job["status"] in {"completed", "failed"}: break
        time.sleep(.02)
    assert job["status"] == "completed", job
    assert job["progress"] == 1 and job["current_stage"].endswith(":complete")
    return job


@pytest.mark.acceptance
def test_real_api_url_to_final_mp4_workflow(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg"); ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe or not EDGE.is_file():
        pytest.skip("FFmpeg/FFprobe/Edge unavailable")
    client = TestClient(create_app(tmp_path / "projects", overrides={
        "llm": DeterministicLLM(), "tts": DeterministicTTS(),
        "alignment": DeterministicAlignment(), "visual": OfflineVisual(),
    }))
    project = client.post("/projects", json={"name": "API E2E"}).json(); project_id = project["id"]
    wait(client, client.post(f"/projects/{project_id}/ingest", json={"source": str(FIXTURE)}))
    wait(client, client.post(f"/projects/{project_id}/facts", json={}))
    wait(client, client.post(f"/projects/{project_id}/script", json={"duration": 30, "style": "tech-news"}))
    wait(client, client.post(f"/projects/{project_id}/storyboard", json={}))

    board = client.get(f"/projects/{project_id}/storyboard").json()
    types = ("hook", "stat-hero", "outro")
    for scene, scene_type in zip(board["scenes"], types):
        scene["type"] = scene_type
        scene["visual"] = {"type": scene_type, "template": f"e2e-{scene_type}",
                           "provenance": {"source_type": "graphic"}, "data": {}}
    assert client.put(f"/projects/{project_id}/storyboard", json=board).status_code == 200
    for scene in board["scenes"]:
        wait(client, client.post(f"/projects/{project_id}/tts", json={"scene_id": scene["id"]}))
        wait(client, client.post(f"/projects/{project_id}/visual", json={"scene_id": scene["id"]}))
        wait(client, client.post(f"/projects/{project_id}/scene", json={"scene_id": scene["id"]}))
    wait(client, client.post(f"/projects/{project_id}/preview", json={}))

    reloaded = client.get(f"/projects/{project_id}/storyboard").json()
    reloaded["scenes"][1]["visual"]["template"] = "e2e-stat-hero-edited"
    assert client.put(f"/projects/{project_id}/storyboard", json=reloaded).status_code == 200
    wait(client, client.post(f"/projects/{project_id}/scene", json={"scene_id": reloaded["scenes"][1]["id"]}))
    wait(client, client.post(f"/projects/{project_id}/preview", json={}))
    wait(client, client.post(f"/projects/{project_id}/validate", json={}))
    wait(client, client.post(f"/projects/{project_id}/render", json={}))

    outputs = client.get(f"/projects/{project_id}/outputs").json()
    assert outputs["preview"]["exists"] and not outputs["preview"]["stale"]
    assert outputs["final"]["exists"] and not outputs["final"]["stale"]
    final_path = tmp_path / "projects" / project_id / "output" / "final.mp4"
    assert final_path.stat().st_size > 10_000
    import json, subprocess
    probe = json.loads(subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format",
                                      "-of", "json", str(final_path)], check=True,
                                     capture_output=True, text=True).stdout)
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in probe["streams"] if stream["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"], video["r_frame_rate"]) == ("h264", 1080, 1920, "30/1")
    assert audio["codec_name"] == "aac" and float(probe["format"]["duration"]) > 0
    assert hashlib.sha256(client.get(outputs["final"]["media_url"]).content).hexdigest() == hashlib.sha256(final_path.read_bytes()).hexdigest()
