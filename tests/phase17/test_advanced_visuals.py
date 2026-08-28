from newsvid.advanced_visuals import available_workflows, advanced_visuals_enabled

def test_advanced_workflows_are_optional_and_disabled_by_default():
    items = available_workflows()
    assert {i.name for i in items} == {"wan", "ltx", "animatediff"}
    assert not advanced_visuals_enabled()
    assert all(not i.enabled for i in items)

def test_explicit_workflow_flag_does_not_change_core_default_contract():
    assert advanced_visuals_enabled({"wan": True})
    assert not advanced_visuals_enabled({"unknown": True})
