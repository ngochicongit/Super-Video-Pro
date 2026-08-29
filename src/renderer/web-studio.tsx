import { useCallback, useEffect, useState } from "react";
const views = [
  "Projects",
  "Create Project",
  "Article",
  "Facts",
  "Script",
  "Storyboard",
  "Scene Editor",
  "Preview",
  "QA",
  "Settings",
  "Services",
] as const;
type View = (typeof views)[number];
type Job = {
  job_id: string;
  project_id: string;
  operation: string;
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  current_stage: string;
  message: string;
  error?: string | null;
};
type ServiceStatus = {
  name: string;
  status: string;
  detail: string;
  required: boolean;
};
export type Scene = {
  id: string;
  type: string;
  narration: string;
  fact_refs: string[];
  duration_seconds: number;
  visual: {
    type: string;
    prompt?: string | null;
    template: string;
    provenance: Record<string, unknown>;
    data: Record<string, unknown>;
  };
  [key: string]: unknown;
};
export type Storyboard = {
  video: Record<string, unknown>;
  scenes: Scene[];
  [key: string]: unknown;
};
const base = import.meta.env.VITE_NEWSVID_API_URL ?? "http://127.0.0.1:8787";
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, init);
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data: unknown = isJson
    ? await response.json().catch(() => ({ detail: response.statusText }))
    : await response.text();
  if (!response.ok) {
    const detail =
      typeof data === "object" && data && "detail" in data
        ? String(data.detail)
        : response.statusText;
    throw new Error(detail);
  }
  return data as T;
}
export function patchStoryboardScene(
  storyboard: Storyboard,
  sceneId: string,
  patch: Partial<Scene>,
  visual?: Partial<Scene["visual"]>,
): Storyboard {
  return {
    ...storyboard,
    scenes: storyboard.scenes.map((scene) =>
      scene.id === sceneId
        ? {
            ...scene,
            ...patch,
            visual: visual ? { ...scene.visual, ...visual } : scene.visual,
          }
        : scene,
    ),
  };
}
export function WebStudio() {
  const [view, setView] = useState<View>("Projects"),
    [projects, setProjects] = useState<any[]>([]),
    [project, setProject] = useState<any>(),
    [data, setData] = useState<Record<string, any>>({}),
    [storyboard, setStoryboard] = useState<Storyboard>(),
    [sceneId, setSceneId] = useState(""),
    [job, setJob] = useState<Job>(),
    [error, setError] = useState(""),
    [projectName, setProjectName] = useState(""),
    [articleSource, setArticleSource] = useState("");
  const loadProjects = useCallback(
    () =>
      request<any[]>("/projects")
        .then(setProjects)
        .catch((reason) => setError(String(reason))),
    [],
  );
  const loadProject = useCallback(async (id: string) => {
    const names = [
        "source",
        "article",
        "images",
        "facts",
        "script",
        "storyboard",
        "qa",
      ],
      entries = await Promise.all(
        names.map(async (name) => {
          try {
            return [name, await request(`/projects/${id}/resources/${name}`)];
          } catch {
            return [name, null];
          }
        }),
      ),
      metadata = await request(`/projects/${id}`),
      outputs = await request(`/projects/${id}/outputs`),
      jobs = await request(`/projects/${id}/jobs`),
      next: any = Object.fromEntries(entries);
    next.outputs = outputs;
    next.jobs = jobs;
    next.project = metadata;
    setData(next);
    setStoryboard(next.storyboard);
    setSceneId((current) =>
      next.storyboard?.scenes?.some((scene: Scene) => scene.id === current)
        ? current
        : next.storyboard?.scenes?.[0]?.id || "",
    );
  }, []);
  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);
  useEffect(() => {
    if (project) void loadProject(project.id);
  }, [project, loadProject]);
  useEffect(() => {
    if (!job || ["completed", "failed"].includes(job.status)) return;
    let cancelled = false;
    const timer = setInterval(
      () =>
        request<Job>(`/jobs/${job.job_id}`)
          .then((next) => {
            if (!cancelled) {
              setJob(next);
              if (next.status === "completed")
                void loadProject(next.project_id);
            }
          })
          .catch((reason) => !cancelled && setError(String(reason))),
      500,
    );
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [job, loadProject]);
  async function create() {
    const name = projectName.trim();
    if (!name) return;
    try {
      const made = await request<any>("/projects", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name }),
      });
      setProjects((current) => [made, ...current]);
      setProject(made);
      setView("Article");
      setProjectName("");
      if (articleSource.trim()) {
        setJob(
          await request<Job>(`/projects/${made.id}/ingest`, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ source: articleSource.trim() }),
          }),
        );
        setArticleSource("");
      }
    } catch (reason) {
      setError(String(reason));
    }
  }
  async function action(operation: string) {
    if (!project) return;
    setError("");
    try {
      if (["facts", "script"].includes(operation)) {
        const services = await request<ServiceStatus[]>("/services/status");
        setData((current) => ({ ...current, services }));
        const ollama = services.find((service) => service.name === "Ollama");
        if (!ollama || ollama.status !== "OK") {
          throw new Error(
            ollama?.detail ??
              "Không thể kiểm tra Ollama. Hãy mở tab Services và thử lại.",
          );
        }
      }
      setJob(
        await request<Job>(`/projects/${project.id}/${operation}`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(
            ["scene", "tts", "visual"].includes(operation)
              ? { scene_id: sceneId }
              : {},
          ),
        }),
      );
    } catch (reason) {
      setError(String(reason));
    }
  }
  function patchScene(
    patch: Partial<Scene>,
    visual?: Partial<Scene["visual"]>,
  ) {
    if (storyboard)
      setStoryboard(patchStoryboardScene(storyboard, sceneId, patch, visual));
  }
  async function saveScene() {
    if (!project || !storyboard) return;
    try {
      const saved = await request<Storyboard>(
        `/projects/${project.id}/storyboard`,
        {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(storyboard),
        },
      );
      setStoryboard(saved);
      setData((current) => ({ ...current, storyboard: saved }));
    } catch (reason) {
      setError(String(reason));
    }
  }
  const scene = storyboard?.scenes.find((item) => item.id === sceneId),
    busy = job && ["queued", "running"].includes(job.status);
  return (
    <section className="web-studio">
      <nav aria-label="Studio views">
        {views.map((item) => (
          <button
            key={item}
            className={view === item ? "active" : ""}
            onClick={() => setView(item)}
          >
            {item}
          </button>
        ))}
      </nav>
      <div className="studio-content">
        <h2>{view}</h2>
        {error && <p className="inline-error">{error}</p>}
        {job && (
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(job.progress * 100)}
          >
            <b>
              {job.operation}: {job.status}
            </b>{" "}
            · {job.current_stage} · {Math.round(job.progress * 100)}% ·{" "}
            {job.error ?? job.message}
          </div>
        )}
        {view === "Projects" && (
          <div>
            {projects.map((item) => (
              <button
                key={item.id}
                className={project?.id === item.id ? "active" : ""}
                onClick={() => setProject(item)}
              >
                {item.name}
              </button>
            ))}
            {project && (
              <>
                <h3>Project</h3>
                <pre>{JSON.stringify(data.project ?? project, null, 2)}</pre>
                <h3>Tác vụ gần đây</h3>
                <pre>{JSON.stringify(data.jobs ?? [], null, 2)}</pre>
              </>
            )}
          </div>
        )}
        {view === "Create Project" && (
          <div className="studio-actions">
            <input
              aria-label="Tên project"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              placeholder="Tên project"
            />
            <input
              aria-label="URL bài viết"
              value={articleSource}
              onChange={(event) => setArticleSource(event.target.value)}
              placeholder="https://..."
            />
            <button disabled={!projectName.trim() || busy} onClick={create}>
              Tạo project và nhập bài viết
            </button>
          </div>
        )}
        {view === "Article" && (
          <div className="studio-resource-grid">
            <section>
              <h3>Nguồn</h3>
              <pre>{JSON.stringify(data.source ?? "Chưa nhập nguồn", null, 2)}</pre>
            </section>
            <section>
              <h3>Nội dung</h3>
              <pre>{data.article ?? "Chưa tạo article"}</pre>
            </section>
            <section>
              <h3>Hình ảnh</h3>
              <pre>{JSON.stringify(data.images ?? "Chưa trích xuất hình ảnh", null, 2)}</pre>
            </section>
          </div>
        )}
        {view === "Facts" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("facts")}
            >
              Generate Facts
            </button>
            <pre>{JSON.stringify(data.facts ?? "Chưa tạo facts", null, 2)}</pre>
          </>
        )}
        {view === "Script" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("script")}
            >
              Generate Script
            </button>
            <pre>
              {JSON.stringify(data.script ?? "Chưa tạo script", null, 2)}
            </pre>
          </>
        )}
        {view === "Storyboard" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("storyboard")}
            >
              Generate Storyboard
            </button>
            <pre>
              {JSON.stringify(storyboard ?? "Chưa tạo storyboard", null, 2)}
            </pre>
          </>
        )}
        {view === "Scene Editor" && storyboard && (
          <div className="studio-actions">
            <select
              aria-label="Scene"
              value={sceneId}
              onChange={(event) => setSceneId(event.target.value)}
            >
              {storyboard.scenes.map((item) => (
                <option key={item.id}>{item.id}</option>
              ))}
            </select>
            {scene && (
              <>
                <input
                  aria-label="Scene type"
                  value={scene.type}
                  onChange={(event) => patchScene({ type: event.target.value })}
                />
                <textarea
                  aria-label="Narration"
                  value={scene.narration}
                  onChange={(event) =>
                    patchScene({ narration: event.target.value })
                  }
                />
                <input
                  aria-label="Fact references"
                  value={scene.fact_refs.join(", ")}
                  onChange={(event) =>
                    patchScene({
                      fact_refs: event.target.value
                        .split(",")
                        .map((value) => value.trim())
                        .filter(Boolean),
                    })
                  }
                />
                <input
                  aria-label="Duration"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={scene.duration_seconds}
                  onChange={(event) =>
                    patchScene({ duration_seconds: Number(event.target.value) })
                  }
                />
                <input
                  aria-label="Visual type"
                  value={scene.visual.type}
                  onChange={(event) =>
                    patchScene({}, { type: event.target.value })
                  }
                />
                <input
                  aria-label="Visual prompt"
                  value={scene.visual.prompt ?? ""}
                  onChange={(event) =>
                    patchScene({}, { prompt: event.target.value || null })
                  }
                />
                <input
                  aria-label="Template"
                  value={scene.visual.template}
                  onChange={(event) =>
                    patchScene({}, { template: event.target.value })
                  }
                />
                <button disabled={busy} onClick={() => void saveScene()}>
                  Lưu scene
                </button>
                {[
                  ["tts", "Regenerate TTS"],
                  ["visual", "Regenerate Visual"],
                  ["scene", "Render Scene"],
                ].map(([op, label]) => (
                  <button
                    key={op}
                    disabled={busy}
                    onClick={() => void action(op)}
                  >
                    {label}
                  </button>
                ))}
              </>
            )}
          </div>
        )}
        {view === "Preview" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("preview")}
            >
              Render Preview
            </button>
            {data.outputs?.preview?.exists && !data.outputs.preview.stale ? (
              <video
                controls
                src={`${base}${data.outputs.preview.media_url}?v=${encodeURIComponent(data.outputs.preview.modified_at)}`}
              />
            ) : (
              <p>
                {data.outputs?.preview?.stale
                  ? "Preview cần render lại sau chỉnh sửa"
                  : "Chưa có preview"}
              </p>
            )}
            <button
              disabled={!project || busy}
              onClick={() => void action("render")}
            >
              Final Render
            </button>
            {data.outputs?.final?.exists && !data.outputs.final.stale && (
              <video
                controls
                src={`${base}${data.outputs.final.media_url}?v=${encodeURIComponent(data.outputs.final.modified_at)}`}
              />
            )}
            {data.outputs?.final?.stale && <p>Video cuối cần render lại</p>}
          </>
        )}
        {view === "QA" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("validate")}
            >
              Run QA
            </button>
            <pre>{JSON.stringify(data.qa ?? "QA chưa chạy", null, 2)}</pre>
          </>
        )}
        {view === "Services" && (
          <>
            <button
              onClick={() =>
                request("/services/status").then((value) =>
                  setData((current) => ({ ...current, services: value })),
                )
              }
            >
              Refresh services
            </button>
            {Array.isArray(data.services) ? (
              <div className="studio-resource-grid">
                {(data.services as ServiceStatus[]).map((service) => (
                  <section key={service.name}>
                    <h3>{service.name}</h3>
                    <b>{service.status}</b>
                    <p>{service.detail}</p>
                  </section>
                ))}
              </div>
            ) : (
              <p>Chưa kiểm tra dịch vụ</p>
            )}
          </>
        )}
      </div>
    </section>
  );
}
