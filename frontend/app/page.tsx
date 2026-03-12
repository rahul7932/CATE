"use client";

import { useState } from "react";

type Context = {
  patient_id: string;
  provider_id: string;
  encounter_id: string;
};

export default function Home() {
  const [ctx, setCtx] = useState<Context>({
    patient_id: "MRN001",
    provider_id: "NPI123",
    encounter_id: "enc-001",
  });
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState(false);

  const api = (path: string, opts?: RequestInit) =>
    fetch(`/api${path}`, {
      ...opts,
      headers: { "Content-Type": "application/json", ...opts?.headers },
    });

  const run = async (
    action: string,
    fn: () => Promise<Response>
  ) => {
    setLoading(action);
    setResult(null);
    setError(false);
    try {
      const r = await fn();
      const data = await r.json();
      setResult(JSON.stringify(data, null, 2));
      setError(!r.ok);
    } catch (e) {
      setResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setError(true);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="mx-auto min-h-screen max-w-2xl px-6 py-12">
      <header className="mb-12 animate-fade-in">
        <h1 className="font-display text-3xl font-semibold tracking-tight text-white">
          CATE Sandbox
        </h1>
        <p className="mt-2 text-slate-400">
          Clinical AI Telemetry — simulate EHR workflows with provenance logging
        </p>
      </header>

      <section className="card animate-slide-up p-6">
        <h2 className="mb-4 font-medium text-slate-300">Context</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-sm text-slate-500">
              Patient ID
            </label>
            <input
              type="text"
              value={ctx.patient_id}
              onChange={(e) => setCtx((c) => ({ ...c, patient_id: e.target.value }))}
              className="input-field"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-slate-500">
              Provider ID
            </label>
            <input
              type="text"
              value={ctx.provider_id}
              onChange={(e) => setCtx((c) => ({ ...c, provider_id: e.target.value }))}
              className="input-field"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-slate-500">
              Encounter ID
            </label>
            <input
              type="text"
              value={ctx.encounter_id}
              onChange={(e) => setCtx((c) => ({ ...c, encounter_id: e.target.value }))}
              className="input-field"
            />
          </div>
        </div>
      </section>

      <section className="mt-6 animate-slide-up" style={{ animationDelay: "0.1s" }}>
        <h2 className="mb-4 font-medium text-slate-300">Actions</h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() =>
              run("predict", () =>
                api("/predict", {
                  method: "POST",
                  body: JSON.stringify(ctx),
                })
              )
            }
            disabled={!!loading}
            className="btn-primary disabled:opacity-50"
          >
            {loading === "predict" ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
            ) : (
              "Run Sepsis Prediction"
            )}
          </button>
          <button
            onClick={() =>
              run("summarize", () =>
                api("/summarize", {
                  method: "POST",
                  body: JSON.stringify(ctx),
                })
              )
            }
            disabled={!!loading}
            className="btn-primary disabled:opacity-50"
          >
            {loading === "summarize" ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
            ) : (
              "Summarize Notes"
            )}
          </button>
          <button
            onClick={() =>
              run("trace", () =>
                api(`/trace?${new URLSearchParams(ctx)}`)
              )
            }
            disabled={!!loading}
            className="btn-secondary disabled:opacity-50"
          >
            {loading === "trace" ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-transparent" />
            ) : (
              "View Trace"
            )}
          </button>
        </div>
      </section>

      {result && (
        <section
          className="card mt-6 animate-slide-up overflow-hidden p-4"
          style={{ animationDelay: "0.05s" }}
        >
          <pre
            className={`overflow-x-auto font-mono text-sm ${
              error ? "text-red-400" : "text-slate-300"
            }`}
          >
            {result}
          </pre>
        </section>
      )}
    </div>
  );
}
