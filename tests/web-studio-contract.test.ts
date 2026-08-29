import { describe, expect, it } from "vitest";
import {
  patchStoryboardScene,
  type Storyboard,
} from "../src/renderer/web-studio";

function scene(id: string) {
  return {
    id,
    script_segment_id: id.replace("scene", "segment"),
    type: "stat-hero",
    narration: `Narration ${id}`,
    fact_refs: ["fact_001"],
    duration_seconds: 2,
    visual: {
      type: "stat-hero",
      prompt: null,
      template: "frame-stat",
      provenance: { source_type: "graphic" },
      data: { value: "75%", label: "Kept metadata" },
    },
  };
}

describe("Web Studio storyboard contract", () => {
  it("patches the selected scene and preserves all untouched metadata and scenes", () => {
    const original: Storyboard = {
      schema_version: 1,
      video: { width: 1080, height: 1920, fps: 30 },
      scenes: [scene("scene_001"), scene("scene_002"), scene("scene_003")],
    };
    const updated = patchStoryboardScene(
      original,
      "scene_002",
      { narration: "Updated narration" },
      { prompt: "Updated prompt" },
    );
    expect(updated.scenes[1].narration).toBe("Updated narration");
    expect(updated.scenes[1].visual.prompt).toBe("Updated prompt");
    expect(updated.scenes[1].visual.data).toEqual({
      value: "75%",
      label: "Kept metadata",
    });
    expect(updated.scenes[1].script_segment_id).toBe("segment_002");
    expect(updated.scenes[0]).toBe(original.scenes[0]);
    expect(updated.scenes[2]).toBe(original.scenes[2]);
  });
});
