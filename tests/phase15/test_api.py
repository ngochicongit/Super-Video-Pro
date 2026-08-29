from newsvid.api import create_app
from fastapi.testclient import TestClient
from newsvid.persistence import atomic_write_model
from newsvid.project import ProjectManager
from newsvid_brain import Fact, FactSet, FactSource, NewsScript, NewsStyle, ScriptSegment, SegmentType
from newsvid.storyboards import StoryboardCoordinator
from newsvid_ingest.models import ArticleImage, ImageManifest
from newsvid.checkpoint import CheckpointStore
from newsvid.schemas import PipelineStage, StageStatus
import time


class FakeOllamaSetup:
    def setup(self, model, progress):
        progress(.12, "ollama:installing", "Đang cài Ollama")
        progress(.64, "ollama:downloading", "Đang tải model 42%")
        progress(.97, "ollama:verifying", "Đang xác minh model")
        return {"status": "ready", "model": model, "base_url": "http://127.0.0.1:11434"}


class FailingOllamaSetup:
    def setup(self, model, progress):
        raise RuntimeError("setup failed")

class OfflineComfyUI:
    cache_key = "offline-comfyui"
    def health_check(self): raise AssertionError("ComfyUI must not be checked for graphic scenes")

class RejectingPreflight:
    def require(self, *args, **kwargs): raise AssertionError("visual preflight must be conditional")


def wait_for_job(client, job_id):
    for _ in range(100):
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(.01)
    raise AssertionError("job did not finish")

def test_projects_and_service_api(tmp_path):
    client = TestClient(create_app(tmp_path))
    made = client.post("/projects", json={"name": "API demo"})
    assert made.status_code == 201
    project_id = made.json()["id"]
    assert client.get("/projects").status_code == 200
    assert client.get(f"/projects/{project_id}").status_code == 200
    job = client.post(f"/projects/{project_id}/validate").json()
    assert job["status"] == "queued"
    assert job["current_stage"] == "queued"
    assert client.get(f"/jobs/{job['job_id']}").status_code == 200

def test_model_provider_settings_are_validated_and_persisted(tmp_path):
    client=TestClient(create_app(tmp_path))
    initial=client.get("/settings/models").json();assert initial["tts_provider"]=="piper"
    updated={**initial,"ollama_model":"qwen2.5:3b","tts_provider":"f5tts","tts_voice":"female-vi","whisperx_model":"medium","comfyui_checkpoint":"news.safetensors"}
    assert client.put("/settings/models",json=updated).json()==updated
    assert client.put("/settings/models",json={"tts_provider":"unknown"}).status_code==422
    assert "female-vi" in (tmp_path/".service-settings.json").read_text(encoding="utf-8")
    assert TestClient(create_app(tmp_path)).get("/settings/models").json()==updated


def test_ollama_setup_is_a_real_progress_job_and_persists_selected_model(tmp_path):
    client = TestClient(create_app(tmp_path, {"ollama_setup": FakeOllamaSetup()}))
    response = client.post("/services/ollama/setup", json={"model": "qwen2.5:3b"})
    assert response.status_code == 200
    completed = wait_for_job(client, response.json()["job_id"])
    assert completed["status"] == "completed"
    assert completed["current_stage"] == "ollama-setup:complete"
    assert completed["result"]["model"] == "qwen2.5:3b"
    assert (tmp_path / ".service-settings.json").read_text(encoding="utf-8").find("qwen2.5:3b") >= 0


def test_failed_job_has_terminal_stage_instead_of_execute_stage(tmp_path):
    client = TestClient(create_app(tmp_path, {"ollama_setup": FailingOllamaSetup()}))
    response = client.post("/services/ollama/setup", json={"model": "qwen2.5:3b"})
    assert response.json()["status"] == "queued"
    failed = wait_for_job(client, response.json()["job_id"])
    assert failed["status"] == "failed"
    assert failed["current_stage"] == "ollama-setup:failed"
    assert failed["message"] == "Thực hiện thất bại"

def test_storyboard_save_validates_refs_and_preserves_full_scene(tmp_path):
    manager=ProjectManager(tmp_path); project=manager.create("Studio save"); root=manager.project_dir(project.id)
    facts=FactSet(source=FactSource(url="https://example.test/a",publisher="example.test",title="Tin"),facts=[Fact(id="fact_001",claim="Thông tin đã xác nhận.",evidence="Thông tin đã xác nhận.",importance=.8,confidence=.9)])
    script=NewsScript(style=NewsStyle.TECH_NEWS,target_duration_seconds=30,estimated_duration_seconds=30,title="Tin",segments=[ScriptSegment(id=f"segment_{index:03d}",type=kind,narration="Thông tin đã xác nhận.",fact_refs=["fact_001"],estimated_duration_seconds=10) for index,kind in ((1,SegmentType.HOOK),(2,SegmentType.BODY),(3,SegmentType.OUTRO))])
    images=ImageManifest(source_url="https://example.test/a",images=[ArticleImage(source_url="https://example.test/i.png",alt="Ảnh",is_hero=True)])
    for name,value in (("facts.json",facts),("script.json",script),("images.json",images)): atomic_write_model(root/name,value)
    board=StoryboardCoordinator(manager).build(project.id); (root/"output"/"preview.mp4").write_bytes(b"old-preview"); CheckpointStore(root/"checkpoint.json").update(PipelineStage.PREVIEW,StageStatus.COMPLETED)
    payload=board.model_dump(mode="json"); payload["scenes"][0]["narration"]="Nội dung đã sửa."; payload["scenes"][0]["visual"]["template"]="template-da-sua"; original_data=payload["scenes"][0]["visual"]["data"]
    client=TestClient(create_app(tmp_path)); saved=client.put(f"/projects/{project.id}/storyboard",json=payload)
    assert saved.status_code==200 and saved.json()["scenes"][0]["narration"]=="Nội dung đã sửa."
    assert saved.json()["scenes"][0]["visual"]["template"]=="template-da-sua"
    assert saved.json()["scenes"][0]["visual"]["data"]==original_data
    checkpoint=CheckpointStore(root/"checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.TTS].status is StageStatus.PENDING
    assert checkpoint.stages[PipelineStage.ALIGNMENT].status is StageStatus.PENDING
    assert checkpoint.stages[PipelineStage.VISUALS].status is StageStatus.PENDING
    assert checkpoint.stages[PipelineStage.PREVIEW].status is StageStatus.PENDING
    assert client.get(f"/projects/{project.id}/outputs").json()["preview"]["stale"] is True
    payload["scenes"][0]["fact_refs"]=["fact_999"]
    assert client.put(f"/projects/{project.id}/storyboard",json=payload).status_code==422
    assert client.get(f"/projects/{project.id}/resources/storyboard").status_code==200
    assert client.get(f"/projects/{project.id}/resources/../../project.json").status_code==404

def test_output_metadata_and_media_are_project_scoped_and_allowlisted(tmp_path):
    manager=ProjectManager(tmp_path); project=manager.create("Output media"); root=manager.project_dir(project.id)
    output=root/"output"; output.mkdir(exist_ok=True); (output/"preview.mp4").write_bytes(b"verified-preview")
    client=TestClient(create_app(tmp_path)); metadata=client.get(f"/projects/{project.id}/outputs")
    assert metadata.status_code==200
    assert metadata.json()["preview"]["exists"] is True
    assert metadata.json()["preview"]["size"]==len(b"verified-preview")
    assert metadata.json()["final"]["exists"] is False
    media=client.get(f"/projects/{project.id}/media/preview.mp4")
    assert media.status_code==200 and media.headers["content-type"].startswith("video/mp4")
    assert media.content==b"verified-preview"
    partial=client.get(f"/projects/{project.id}/media/preview.mp4",headers={"range":"bytes=0-3"})
    assert partial.status_code==206 and partial.content==b"veri"
    assert client.get(f"/projects/{project.id}/media/checkpoint.json").status_code==404

def test_graphic_scene_visual_refresh_does_not_require_comfyui(tmp_path):
    manager=ProjectManager(tmp_path);project=manager.create("Graphic visual");root=manager.project_dir(project.id)
    facts=FactSet(source=FactSource(url="https://example.test/a",publisher="example.test",title="Tin"),facts=[Fact(id="fact_001",claim="Thông tin.",evidence="Thông tin.",importance=.8,confidence=.9)])
    script=NewsScript(style=NewsStyle.TECH_NEWS,target_duration_seconds=30,estimated_duration_seconds=30,title="Tin",segments=[ScriptSegment(id=f"segment_{i:03d}",type=t,narration="Thông tin.",fact_refs=["fact_001"],estimated_duration_seconds=10) for i,t in ((1,SegmentType.HOOK),(2,SegmentType.BODY),(3,SegmentType.OUTRO))])
    images=ImageManifest(source_url="https://example.test/a",images=[])
    for name,value in (("facts.json",facts),("script.json",script),("images.json",images)):atomic_write_model(root/name,value)
    board=StoryboardCoordinator(manager).build(project.id)
    client=TestClient(create_app(tmp_path,{"visual":OfflineComfyUI(),"preflight":RejectingPreflight()}))
    queued=client.post(f"/projects/{project.id}/visual",json={"scene_id":board.scenes[0].id}).json()
    completed=wait_for_job(client,queued["job_id"])
    assert completed["status"]=="completed", completed
    assert completed["result"]["assets"]==[]
