from io import StringIO

import httpx

import newsvid.ollama_setup as ollama_module
from newsvid.ollama_setup import OllamaSetupCoordinator


class Process:
    def __init__(self, output="", code=0):
        self.stdout = StringIO(output)
        self.code = code

    def wait(self):
        return self.code


def response(status, payload):
    request = httpx.Request("GET", "http://127.0.0.1:11434/api/tags")
    return httpx.Response(status, request=request, json=payload)


def test_setup_installs_starts_pulls_and_reports_cli_percentage(monkeypatch):
    discoveries = iter([None, r"C:\Program Files\Ollama\ollama.exe"])
    monkeypatch.setattr(ollama_module, "find_ollama", lambda: next(discoveries))
    monkeypatch.setattr(ollama_module.shutil, "which", lambda name: r"C:\Windows\winget.exe")
    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        if "install" in command:
            return Process("Downloading 25%\rInstalling 100%\n")
        if "serve" in command:
            return Process()
        return Process("pulling manifest 10%\rpulling layers 73%\rsuccess 100%\n")

    online = iter([
        response(503, {}),
        response(503, {}),
        response(200, {"models": []}),
        response(200, {"models": [{"name": "qwen2.5:3b"}]}),
    ])
    updates = []
    coordinator = OllamaSetupCoordinator(
        "http://127.0.0.1:11434", runner=runner,
        http_get=lambda *args, **kwargs: next(online), sleeper=lambda _: None,
    )
    result = coordinator.setup("qwen2.5:3b", lambda *value: updates.append(value))

    assert result["status"] == "ready"
    assert any("install" in call for call in calls)
    assert any(call[-1] == "serve" for call in calls)
    assert any(call[-2:] == ["pull", "qwen2.5:3b"] for call in calls)
    assert any(stage == "ollama:downloading" and progress > .75
               for progress, stage, _ in updates)
