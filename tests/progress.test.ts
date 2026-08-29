import {describe,expect,it} from "vitest";
import {parseFfmpegProgressLine,parseFfmpegTime} from "../src/main/ffmpeg-progress";
import {aggregateTaskProgress} from "../src/renderer/task-progress";

describe("task progress",()=>{
  it("averages active tasks and clamps invalid bounds",()=>{
    expect(aggregateTaskProgress([{progress:.25},{progress:.75}])).toBe(.5);
    expect(aggregateTaskProgress([{progress:-1},{progress:2}])).toBe(.5);
    expect(aggregateTaskProgress([])).toBe(0);
  });
  it("parses ffmpeg timestamps",()=>{
    expect(parseFfmpegTime("00:01:30.500000")).toBe(90.5);
    expect(parseFfmpegProgressLine("out_time_us=2500000")).toBe(2.5);
    expect(parseFfmpegProgressLine("out_time=00:00:03.250000")).toBe(3.25);
    expect(parseFfmpegProgressLine("out_time_us=N/A")).toBeNull();
    expect(parseFfmpegProgressLine("out_time_ms=invalid")).toBeNull();
    expect(parseFfmpegProgressLine("progress=continue")).toBeNull();
  });
});
