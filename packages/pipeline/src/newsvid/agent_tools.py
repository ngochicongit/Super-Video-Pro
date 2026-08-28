from __future__ import annotations
import json, shutil, subprocess
from typing import Any
from .persistence import atomic_write_text
from .project import ProjectManager

def discover_agents() -> dict[str, dict[str, Any]]:
    return {n: {"available": bool(shutil.which(b)), "binary": b} for n, b in (("codex", "codex"), ("cursor-agent", "cursor-agent"))}

class AgentTools:
    def __init__(self, projects: ProjectManager) -> None: self.projects = projects
    def _read(self, rel: str, project_id: str) -> dict[str, Any]: return json.loads((self.projects.project_dir(project_id) / rel).read_text(encoding="utf-8"))
    def fetch_article(self, project_id: str): return self._read("source.json", project_id)
    def generate_script(self, project_id: str): return self._read("script.json", project_id)
    def generate_tts(self, project_id: str): return self._read("audio/tts_manifest.json", project_id)
    def generate_visual(self, project_id: str):
        p = self.projects.project_dir(project_id) / "images/generated_manifest.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"assets": []}
    def inspect_video(self, project_id: str):
        p = self.projects.project_dir(project_id) / "output/final.mp4"
        return json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(p)], capture_output=True, text=True, check=True).stdout)
    def validate_project(self, project_id: str):
        from .qa import QACoordinator
        from .final_assembler import FinalAssembler
        return QACoordinator(self.projects, FinalAssembler()).run(project_id)
    def render_scene(self, project_id: str, scene_id: str):
        return {"project_id": project_id, "scene_id": scene_id, "action": "render_scene", "deterministic": True}
    def render_video(self, project_id: str):
        return {"project_id": project_id, "action": "render_video", "deterministic": True}
    def edit_storyboard(self, project_id: str, scene_id: str, patch: dict[str, Any]):
        p = self.projects.project_dir(project_id) / "storyboard.json"; d = json.loads(p.read_text(encoding="utf-8"))
        for s in d["scenes"]:
            if s["id"] == scene_id: s.update(patch); atomic_write_text(p, json.dumps(d, ensure_ascii=True, indent=2)); return s
        raise KeyError(scene_id)
