import { useCallback, useEffect, useState } from "react";
import vi from "./locales/vi.json";
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
  id: string;
  display_name: string;
  state: string;
  root_cause?: string | null;
  detected?: string | null;
  manual_fix: string;
  required: boolean;
};
type EnvironmentReport = {task:string;status:string;results:ServiceStatus[]};
type ModelSettings = {ollama_model:string;tts_provider:"piper"|"f5tts";tts_voice:string;whisperx_model:string;comfyui_checkpoint:string};
type ModelOptions = {ollama_models:string[];tts_providers:string[];tts_voices:string[];whisperx_models:string[];comfyui_checkpoints:string[];availability:Record<string,boolean>};
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
function operationLabel(operation: string): string {
  return (vi.operations as Record<string, string>)[operation] ?? operation;
}
function stageLabel(stage: string): string {
  const key = stage.split(":").at(-1) ?? stage;
  return (vi.stages as Record<string, string>)[key] ?? stage;
}
export function WebStudio() {
  const [view, setView] = useState<View>("Projects"),
    [projects, setProjects] = useState<any[]>([]),
    [project, setProject] = useState<any>(),
    [data, setData] = useState<Record<string, any>>({}),
    [storyboard, setStoryboard] = useState<Storyboard>(),
    [sceneId, setSceneId] = useState(""),
    [job, setJob] = useState<Job>(),
    [pendingOperation, setPendingOperation] = useState<string>(),
    [environmentTask, setEnvironmentTask] = useState("render"),
    [modelSettings, setModelSettings] = useState<ModelSettings>(),
    [modelOptions, setModelOptions] = useState<ModelOptions>(),
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
    void request<ModelSettings>("/settings/models").then(setModelSettings).catch((reason) => setError(String(reason)));
    void request<ModelOptions>("/settings/model-options").then(setModelOptions).catch((reason) => setError(String(reason)));
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
              if (next.status === "completed") {
                if (next.project_id === "system") {
                  void request<ServiceStatus[]>("/services/status").then(
                    async (services) => {
                      setData((current) => ({ ...current, services }));
                      if (pendingOperation && project) {
                        const operation = pendingOperation;
                        setPendingOperation(undefined);
                        setJob(
                          await request<Job>(
                            `/projects/${project.id}/${operation}`,
                            {
                              method: "POST",
                              headers: { "content-type": "application/json" },
                              body: JSON.stringify({}),
                            },
                          ),
                        );
                      }
                    },
                  ).catch((reason) => setError(String(reason)));
                } else void loadProject(next.project_id);
              }
            }
          })
          .catch((reason) => !cancelled && setError(String(reason))),
      500,
    );
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [job, loadProject, pendingOperation, project]);
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
        const ollama = services.find((service) => service.id === "ollama");
        if (!ollama || ollama.state !== "READY") {
          setPendingOperation(operation);
          setView("Services");
          setJob(
            await request<Job>("/services/ollama/setup", {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({}),
            }),
          );
          return;
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
  async function setupOllama() {
    setError("");
    try {
      setJob(
        await request<Job>("/services/ollama/setup", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({}),
        }),
      );
    } catch (reason) {
      setError(String(reason));
    }
  }
  async function saveModelSettings() {
    if (!modelSettings) return;
    setError("");
    try {
      setModelSettings(await request<ModelSettings>("/settings/models", {
        method: "PUT", headers: {"content-type":"application/json"},
        body: JSON.stringify(modelSettings),
      }));
    } catch (reason) { setError(String(reason)); }
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
      <nav aria-label={vi.aria.studioViews}>
        {views.map((item) => (
          <button
            key={item}
            className={view === item ? "active" : ""}
            onClick={() => setView(item)}
          >
            {vi.views[item]}
          </button>
        ))}
      </nav>
      <div className="studio-content">
        <h2>{vi.views[view]}</h2>
        {error && <p className="inline-error">{error}</p>}
        {job && (
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(job.progress * 100)}
          >
            <b>
              {operationLabel(job.operation)}: {vi.status[job.status]}
            </b>{" "}
            · {stageLabel(job.current_stage)} · {Math.round(job.progress * 100)}% ·{" "}
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
                <h3>{vi.sections.project}</h3>
                <pre>{JSON.stringify(data.project ?? project, null, 2)}</pre>
                <h3>{vi.sections.recentJobs}</h3>
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
              <h3>{vi.sections.source}</h3>
              <pre>{JSON.stringify(data.source ?? vi.messages.noSource, null, 2)}</pre>
            </section>
            <section>
              <h3>{vi.sections.content}</h3>
              <pre>{data.article ?? vi.messages.noArticle}</pre>
            </section>
            <section>
              <h3>{vi.sections.images}</h3>
              <pre>{JSON.stringify(data.images ?? vi.messages.noImages, null, 2)}</pre>
            </section>
          </div>
        )}
        {view === "Facts" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("facts")}
            >
              {vi.actions.generateFacts}
            </button>
            <pre>{JSON.stringify(data.facts ?? vi.messages.noFacts, null, 2)}</pre>
          </>
        )}
        {view === "Script" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("script")}
            >
              {vi.actions.generateScript}
            </button>
            <pre>
              {JSON.stringify(data.script ?? vi.messages.noScript, null, 2)}
            </pre>
          </>
        )}
        {view === "Storyboard" && (
          <>
            <button
              disabled={!project || busy}
              onClick={() => void action("storyboard")}
            >
              {vi.actions.generateStoryboard}
            </button>
            <pre>
              {JSON.stringify(storyboard ?? vi.messages.noStoryboard, null, 2)}
            </pre>
          </>
        )}
        {view === "Scene Editor" && storyboard && (
          <div className="studio-actions">
            <select
              aria-label={vi.fields.scene}
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
                  aria-label={vi.fields.sceneType}
                  value={scene.type}
                  onChange={(event) => patchScene({ type: event.target.value })}
                />
                <textarea
                  aria-label={vi.fields.narration}
                  value={scene.narration}
                  onChange={(event) =>
                    patchScene({ narration: event.target.value })
                  }
                />
                <input
                  aria-label={vi.fields.factRefs}
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
                  aria-label={vi.fields.duration}
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={scene.duration_seconds}
                  onChange={(event) =>
                    patchScene({ duration_seconds: Number(event.target.value) })
                  }
                />
                <input
                  aria-label={vi.fields.visualType}
                  value={scene.visual.type}
                  onChange={(event) =>
                    patchScene({}, { type: event.target.value })
                  }
                />
                <input
                  aria-label={vi.fields.visualPrompt}
                  value={scene.visual.prompt ?? ""}
                  onChange={(event) =>
                    patchScene({}, { prompt: event.target.value || null })
                  }
                />
                <input
                  aria-label={vi.fields.template}
                  value={scene.visual.template}
                  onChange={(event) =>
                    patchScene({}, { template: event.target.value })
                  }
                />
                <button disabled={busy} onClick={() => void saveScene()}>
                  {vi.actions.saveScene}
                </button>
                {[
                  ["tts", vi.actions.regenerateTts],
                  ["visual", vi.actions.regenerateVisual],
                  ["scene", vi.actions.renderScene],
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
        {view === "Settings" && modelSettings && (
          <div className="model-settings-grid">
            <section><h3>{vi.modelSettings.language}</h3><label>{vi.modelSettings.llm}<select value={modelSettings.ollama_model} onChange={(event)=>setModelSettings({...modelSettings,ollama_model:event.target.value})}>{(modelOptions?.ollama_models??[modelSettings.ollama_model]).map(value=><option key={value}>{value}</option>)}</select></label><small>{modelOptions?.availability.ollama?vi.modelSettings.detected:vi.modelSettings.offline}</small></section>
            <section><h3>{vi.modelSettings.voice}</h3><label>{vi.modelSettings.provider}<select value={modelSettings.tts_provider} onChange={(event)=>setModelSettings({...modelSettings,tts_provider:event.target.value as "piper"|"f5tts"})}><option value="piper">Piper cục bộ</option><option value="f5tts">F5-TTS service</option></select></label><label>{vi.modelSettings.voiceModel}<select value={modelSettings.tts_voice} onChange={(event)=>setModelSettings({...modelSettings,tts_voice:event.target.value})}>{(modelOptions?.tts_voices??[modelSettings.tts_voice]).map(value=><option key={value}>{value}</option>)}</select></label></section>
            <section><h3>{vi.modelSettings.captions}</h3><label>{vi.modelSettings.whisperx}<select value={modelSettings.whisperx_model} onChange={(event)=>setModelSettings({...modelSettings,whisperx_model:event.target.value})}>{(modelOptions?.whisperx_models??[modelSettings.whisperx_model]).map(value=><option key={value}>{value}</option>)}</select></label><small>{modelOptions?.availability.whisperx?vi.modelSettings.detected:vi.modelSettings.offline}</small></section>
            <section><h3>{vi.modelSettings.images}</h3><label>{vi.modelSettings.checkpoint}<select value={modelSettings.comfyui_checkpoint} onChange={(event)=>setModelSettings({...modelSettings,comfyui_checkpoint:event.target.value})}>{(modelOptions?.comfyui_checkpoints??[modelSettings.comfyui_checkpoint]).map(value=><option key={value}>{value}</option>)}</select></label><small>{modelOptions?.availability.comfyui?vi.modelSettings.detected:vi.modelSettings.offline}</small></section>
            <button className="primary-workflow" disabled={busy} onClick={()=>void saveModelSettings()}>{vi.actions.saveModels}</button>
          </div>
        )}
        {view === "Preview" && (
          <>
            <section className="workflow-launcher">
              <span>QUY TRÌNH TỰ ĐỘNG</span><h3>Tạo video mà không cần đi từng tab</h3>
              <p>Hệ thống tự dùng lại stage hợp lệ và chỉ chạy phần còn thiếu hoặc đã thay đổi.</p>
              <div>
                <button className="primary-workflow" disabled={!project||busy} onClick={()=>void action("render")}>{vi.actions.createCompleteVideo}</button>
                <button disabled={!project||busy} onClick={()=>void action("quick-preview")}>{vi.actions.quickPreview}</button>
                <button disabled={!project||busy} onClick={()=>void action("preview")}>{vi.actions.captionedPreview}</button>
              </div>
              <small>Preview nhanh không cần WhisperX. Preview hoàn chỉnh và video cuối có phụ đề nên cần WhisperX.</small>
            </section>
            {data.outputs?.quick_preview?.exists && !data.outputs.quick_preview.stale && (
              <section className="preview-result"><h3>Preview nhanh</h3><video controls src={`${base}${data.outputs.quick_preview.media_url}?v=${encodeURIComponent(data.outputs.quick_preview.modified_at)}`} /></section>
            )}
            {data.outputs?.preview?.exists && !data.outputs.preview.stale ? (
              <section className="preview-result"><h3>Preview có phụ đề</h3><video controls src={`${base}${data.outputs.preview.media_url}?v=${encodeURIComponent(data.outputs.preview.modified_at)}`} /></section>
            ) : (
              <p>
                {data.outputs?.preview?.stale
                  ? vi.messages.previewStale
                  : vi.messages.noPreview}
              </p>
            )}
            {data.outputs?.final?.exists && !data.outputs.final.stale && (
              <section className="preview-result"><h3>Video hoàn chỉnh</h3><video controls src={`${base}${data.outputs.final.media_url}?v=${encodeURIComponent(data.outputs.final.modified_at)}`} /></section>
            )}
            {data.outputs?.final?.stale && <p>{vi.messages.finalStale}</p>}
          </>
        )}
        {view === "QA" && (
          <section className="qa-panel">
            <div><h3>{vi.qa.title}</h3><p>{vi.qa.description}</p></div>
            <button
              disabled={!project || busy}
              onClick={() => void action("validate")}
            >
              {vi.actions.runQa}
            </button>
            {data.qa ? <><div className={`qa-summary ${data.qa.status}`}>{data.qa.status === "pass" ? vi.qa.ready : vi.qa.needsAttention}</div><div className="qa-checks">{data.qa.checks.map((check:any)=><article key={check.name} data-status={check.status}><span>{check.status === "pass" ? "✓" : check.status === "not_run" ? "○" : "!"}</span><div><strong>{(vi.qa.checks as Record<string,string>)[check.name]??check.name}</strong>{check.detail&&<small>{check.detail}</small>}</div></article>)}</div>{data.qa.checks.some((check:any)=>check.name==="final_render"&&check.status==="not_run")&&<button className="primary-workflow" disabled={busy} onClick={()=>void action("render")}>{vi.actions.createCompleteVideo}</button>}</> : <p>{vi.messages.qaPending}</p>}
          </section>
        )}
        {view === "Services" && (
          <>
            <label className="environment-task">Tác vụ
              <select value={environmentTask} onChange={(event) => setEnvironmentTask(event.target.value)}>
                {['facts','script','visual','tts','alignment','scene','preview','render','build','test','ui-verify'].map((task) => <option key={task}>{task}</option>)}
              </select>
            </label>
            <button
              onClick={() =>
                request<EnvironmentReport>(`/environment/dependencies?task=${environmentTask}`).then((value) =>
                  setData((current) => ({ ...current, environment: value, services: value.results })),
                )
              }
            >
              {vi.actions.refreshServices}
            </button>
            <button disabled={busy} onClick={() => request<EnvironmentReport>(`/environment/dependencies?task=${environmentTask}&fix=true`).then((value) => setData((current) => ({ ...current, environment: value, services: value.results })))}>
              {vi.actions.fixDependencies}
            </button>
            <button disabled={busy} onClick={() => void setupOllama()}>
              {vi.actions.setupOllama}
            </button>
            {data.environment && <p className="environment-summary">Trạng thái {data.environment.task}: <b>{data.environment.status}</b></p>}
            {Array.isArray(data.services) ? (
              <div className="studio-resource-grid">
                {(data.services as ServiceStatus[]).map((service) => (
                  <section key={service.id} className={`dependency-card state-${service.state.toLowerCase()}`}>
                    <h3>{service.display_name}</h3>
                    <b>{service.state}</b>
                    <p>{service.detected ?? service.root_cause ?? service.manual_fix}</p>
                  </section>
                ))}
              </div>
            ) : (
              <p>{vi.messages.servicesUnchecked}</p>
            )}
          </>
        )}
      </div>
    </section>
  );
}
