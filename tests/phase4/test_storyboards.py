from __future__ import annotations

import json
from pathlib import Path

from newsvid.checkpoint import CheckpointStore
from newsvid.persistence import atomic_write_model, load_model
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid.storyboards import StoryboardCoordinator
from newsvid_brain import (Fact, FactSet, FactSource, NewsScript, NewsStyle,
                           RoutingContext, SceneType, ScriptSegment, SegmentType,
                           SourceType, Storyboard, VisualRouter, SchemaValidationError)
from newsvid_ingest.models import ArticleImage, ImageManifest

ARTICLE_URL = "https://news.example.vn/ai"
IMAGE_URL = "https://news.example.vn/media/launch.jpg"


def facts() -> FactSet:
    return FactSet(
        source=FactSource(url=ARTICLE_URL, publisher="news.example.vn", title="Bản tin AI"),
        facts=[
            Fact(id="fact_001", claim="Ông An công bố trung tâm AI tại Hà Nội.",
                 evidence="Ông An công bố trung tâm AI tại Hà Nội.", importance=.9, confidence=.98),
            Fact(id="fact_002", claim="Trung tâm đào tạo 1.000 kỹ sư.",
                 evidence="Trung tâm đào tạo 1.000 kỹ sư.", importance=.8, confidence=.96),
            Fact(id="fact_003", claim="Dự án phát triển một chiến lược trí tuệ nhân tạo.",
                 evidence="Dự án phát triển một chiến lược trí tuệ nhân tạo.", importance=.7, confidence=.9),
        ],
    )


def segment(text: str, *, kind: SegmentType = SegmentType.BODY,
            refs: list[str] | None = None, index: int = 2) -> ScriptSegment:
    return ScriptSegment(id=f"segment_{index:03d}", type=kind, narration=text,
                         fact_refs=refs or ["fact_001"], estimated_duration_seconds=20)


def context(image: bool = True) -> RoutingContext:
    return RoutingContext(article_image_url=IMAGE_URL if image else None, article_url=ARTICLE_URL)


def test_router_hook_and_outro_use_kinetic_and_outro_templates() -> None:
    router = VisualRouter()
    hook = router.route(segment("Tin mới đáng chú ý.", kind=SegmentType.HOOK, index=1), facts(), context())
    outro = router.route(segment("Đây là những thông tin chính.", kind=SegmentType.OUTRO, index=3), facts(), context())
    assert (hook.type, hook.template, hook.provenance.source_type) == (
        SceneType.KINETIC_TEXT, "frame-kinetic-type", SourceType.GRAPHIC)
    assert (outro.type, outro.template) == (SceneType.OUTRO, "frame-logo-outro")


def test_real_person_or_event_uses_source_imagery_and_never_ai() -> None:
    router = VisualRouter()
    with_image = router.route(segment("Ông An công bố dự án mới."), facts(), context())
    without_image = router.route(segment("Ông An công bố dự án mới."), facts(), context(False))
    assert with_image.type is SceneType.ARTICLE_IMAGE
    assert with_image.provenance.source_type is SourceType.ARTICLE
    assert str(with_image.provenance.source_url) == IMAGE_URL
    assert without_image.type is SceneType.SCREENSHOT
    assert without_image.provenance.source_type is SourceType.SCREENSHOT


def test_numbers_route_to_stat_chart_or_comparison() -> None:
    router = VisualRouter()
    fact_set = facts()
    stat = router.route(segment("Kế hoạch đào tạo 1.000 kỹ sư.", refs=["fact_002"]), fact_set, context())
    chart = router.route(segment("Các mốc đạt 100, 200 và 300 hồ sơ.", refs=["fact_002"]), fact_set, context())
    comparison = router.route(segment("Tỷ lệ tăng từ 10% lên 20% so với năm trước.", refs=["fact_002"]), fact_set, context())
    assert stat.type is SceneType.STAT_HERO
    assert chart.type is SceneType.CHART
    assert comparison.type is SceneType.COMPARISON


def test_chronology_location_software_quote_list_and_abstract_routes() -> None:
    router = VisualRouter()
    fact_set = facts()
    cases = [
        ("Đầu tiên dự án nghiên cứu, sau đó triển khai.", SceneType.TIMELINE),
        ("Hoạt động diễn ra tại Hà Nội.", SceneType.MAP),
        ("Nền tảng trực tuyến có giao diện mới.", SceneType.SCREENSHOT),
        ('Đại diện cho biết “dữ liệu được bảo vệ”.', SceneType.QUOTE),
        ("Các tính năng bao gồm tìm kiếm và phân tích.", SceneType.FEATURE_LIST),
        ("Chiến lược trí tuệ nhân tạo mở ra một khái niệm mới.", SceneType.AI_ILLUSTRATION),
    ]
    for text, expected in cases:
        routed = router.route(segment(text, refs=["fact_003"]), fact_set, context())
        assert routed.type is expected, text
    generated = router.route(segment(cases[-1][0], refs=["fact_003"]), fact_set, context())
    assert generated.provenance.source_type is SourceType.GENERATED
    assert generated.provenance.generator == "comfyui"


def test_scene_type_schema_covers_master_plan_minimum() -> None:
    expected = {"hook", "headline", "article-image", "kinetic-text", "stat-hero", "chart",
                "comparison", "feature-list", "timeline", "quote", "screenshot",
                "AI-illustration", "map", "outro"}
    assert {item.value for item in SceneType} == expected


def project_with_inputs(tmp_path: Path) -> tuple[ProjectManager, str]:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("Storyboard test")
    directory = manager.project_dir(project.id)
    fact_set = facts()
    script = NewsScript(
        style=NewsStyle.TECH_NEWS, target_duration_seconds=60,
        estimated_duration_seconds=60, title="Bản tin AI",
        segments=[
            segment("Trung tâm AI vừa có thông tin mới.", kind=SegmentType.HOOK, index=1),
            segment("Ông An công bố trung tâm AI tại Hà Nội.", index=2),
            segment("Đây là những dữ kiện chính của bản tin.", kind=SegmentType.OUTRO,
                    refs=["fact_003"], index=3),
        ],
    )
    images = ImageManifest(source_url=ARTICLE_URL, images=[
        ArticleImage(source_url=IMAGE_URL, alt="Lễ công bố", is_hero=True)
    ])
    atomic_write_model(directory / "facts.json", fact_set)
    atomic_write_model(directory / "script.json", script)
    atomic_write_model(directory / "images.json", images)
    CheckpointStore(directory / "checkpoint.json").update(
        PipelineStage.SCRIPT, StageStatus.COMPLETED, fingerprint="sha256:script"
    )
    return manager, project.id


def test_storyboard_is_valid_editable_source_of_truth_and_preserves_refs(tmp_path: Path) -> None:
    manager, project_id = project_with_inputs(tmp_path)
    coordinator = StoryboardCoordinator(manager)
    storyboard = coordinator.build(project_id)
    directory = manager.project_dir(project_id)
    saved = load_model(directory / "storyboard.json", Storyboard)
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    script = load_model(directory / "script.json", NewsScript)
    assert saved.video.model_dump() == {"width": 1080, "height": 1920, "fps": 30,
                                       "target_duration": 60, "style": "tech-news"}
    assert [scene.fact_refs for scene in saved.scenes] == [s.fact_refs for s in script.segments]
    assert [scene.id for scene in saved.scenes] == ["scene_001", "scene_002", "scene_003"]
    assert saved.scenes[0].type is SceneType.HOOK
    assert saved.scenes[0].visual.type is SceneType.KINETIC_TEXT
    assert saved.scenes[1].visual.provenance.source_type is SourceType.ARTICLE
    editable = json.loads((directory / "storyboard.json").read_text(encoding="utf-8"))
    editable["scenes"][1]["visual"]["template"] = "user-selected-template"
    assert Storyboard.model_validate(editable).scenes[1].visual.template == "user-selected-template"
    assert checkpoint.stages[PipelineStage.STORYBOARD].status is StageStatus.COMPLETED
    assert not (directory / "audio").joinpath("narration.wav").exists()
    assert coordinator.build(project_id).model_dump() == storyboard.model_dump()


def test_storyboard_rejects_script_reference_missing_from_facts(tmp_path: Path) -> None:
    manager, project_id = project_with_inputs(tmp_path)
    directory = manager.project_dir(project_id)
    script = load_model(directory / "script.json", NewsScript)
    script.segments[1].fact_refs = ["fact_999"]
    atomic_write_model(directory / "script.json", script)
    try:
        StoryboardCoordinator(manager).build(project_id)
        raise AssertionError("unresolved fact reference was accepted")
    except SchemaValidationError as exc:
        assert "fact_999" in str(exc)
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.STORYBOARD].status is StageStatus.FAILED
    assert not (directory / "storyboard.json").exists()
