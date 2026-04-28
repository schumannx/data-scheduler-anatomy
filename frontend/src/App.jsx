import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function toIsoLocal(datetimeLocal) {
  if (!datetimeLocal) return null;
  const d = new Date(datetimeLocal);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function toIsoDateEndOfDay(dateStr) {
  if (!dateStr) return null;
  const d = new Date(`${dateStr}T23:59:59`);
  return d.toISOString();
}

function toIsoDateStart(dateStr) {
  if (!dateStr) return null;
  const d = new Date(`${dateStr}T00:00:00`);
  return d.toISOString();
}

export default function App() {
  const [name, setName] = useState("");
  const [cron, setCron] = useState("*/5 * * * *");
  const [nextRun, setNextRun] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setStatus(null);
    const body = {
      name: name.trim(),
      cron: cron.trim(),
      next_run: toIsoLocal(nextRun),
      start_date: toIsoDateStart(startDate),
      end_date: toIsoDateEndOfDay(endDate),
    };
    if (!body.name || !body.cron || !body.next_run || !body.start_date || !body.end_date) {
      setStatus({ ok: false, text: "Fill all fields." });
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/schedules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail
          ? Array.isArray(data.detail)
            ? data.detail.map((d) => d.msg).join(" ")
            : String(data.detail)
          : res.statusText;
        setStatus({ ok: false, text: detail || "Request failed" });
        return;
      }
      setStatus({ ok: true, text: `Saved: ${data.name} (id ${data.id})` });
    } catch (err) {
      setStatus({ ok: false, text: err.message || "Network error" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1>Schedule job</h1>
      <p className="sub">Full stack data · stored in MongoDB · due runs pushed to Redis</p>
      <form onSubmit={onSubmit}>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. nightly title ingest"
          autoComplete="off"
        />

        <label htmlFor="cron">Cron</label>
        <input id="cron" value={cron} onChange={(e) => setCron(e.target.value)} placeholder="*/5 * * * *" />
        <p className="hint">5 fields: minute hour day month weekday</p>

        <label htmlFor="next_run">Next run</label>
        <input
          id="next_run"
          type="datetime-local"
          value={nextRun}
          onChange={(e) => setNextRun(e.target.value)}
        />

        <label htmlFor="start_date">Start date</label>
        <input id="start_date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />

        <label htmlFor="end_date">End date</label>
        <input id="end_date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />

        <button type="submit" disabled={loading}>
          {loading ? "Saving…" : "Save to MongoDB"}
        </button>
      </form>
      {status && (
        <div className={`msg ${status.ok ? "ok" : "err"}`} role="status">
          {status.text}
        </div>
      )}
    </>
  );
}
