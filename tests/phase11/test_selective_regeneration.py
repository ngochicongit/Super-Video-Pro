from newsvid.selective_regeneration import ChangeKind, plan_invalidation


def test_narration_invalidates_only_scene_and_downstream() -> None:
    plan = plan_invalidation(ChangeKind.NARRATION, ["scene_002", "scene_002"])
    assert plan.scenes == ("scene_002",)
    assert (plan.regenerate_tts, plan.regenerate_alignment, plan.regenerate_captions, plan.reassemble) == (True, True, True, True)


def test_visual_and_template_changes_keep_audio_cache() -> None:
    for kind in (ChangeKind.VISUAL, ChangeKind.TEMPLATE):
        plan = plan_invalidation(kind, ("scene_001", "scene_003"))
        assert plan.scenes == ("scene_001", "scene_003")
        assert not plan.regenerate_tts and not plan.regenerate_alignment and not plan.regenerate_captions
        assert plan.reassemble


def test_transition_only_reassembles_without_scene_regeneration() -> None:
    plan = plan_invalidation("transition")
    assert plan == plan_invalidation(ChangeKind.TRANSITION)
    assert plan.scenes == () and plan.reassemble
