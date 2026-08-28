from newsvid.autonomous_editor import BoundedAutonomousEditor

def test_bounded_loop_stops_after_three_and_keeps_scene_scope():
    calls = []
    def inspect(): return {"ok": False}
    def identify(_): return ["scene_002"]
    def edit(issues): calls.append(issues); return ["scene_002"]
    def qa(): return {"status": "fail"}
    history = BoundedAutonomousEditor().run(inspect, identify, edit, lambda: "ok", lambda: None, qa)
    assert len(history) == 3 and all(h.changed_scenes == ("scene_002",) for h in history)
    assert len(calls) == 3

def test_loop_stops_when_qa_passes():
    n = [0]
    def identify(_): n[0] += 1; return ["scene_001"]
    history = BoundedAutonomousEditor().run(lambda: None, identify, lambda _: ["scene_001"], lambda: "ok", lambda: None, lambda: {"status": "pass"})
    assert len(history) == 1
