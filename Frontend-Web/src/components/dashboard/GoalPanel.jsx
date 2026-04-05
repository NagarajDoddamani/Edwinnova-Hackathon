import { useState } from "react";

function money(value) {
  const amount = Number(value || 0);
  return `Rs. ${new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(Number.isFinite(amount) ? amount : 0)}`;
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-IN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function GoalRow({ goal }) {
  const progress = Number(goal.progress || 0);

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-900">{goal.title}</p>
          <p className="mt-1 text-xs text-slate-500">
            {money(goal.saved_amount)} saved of {money(goal.target_amount)}
          </p>
        </div>
        <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">
          {Math.round(progress)}%
        </span>
      </div>

      <div className="mt-3 h-2 rounded-full bg-slate-200">
        <div
          className="h-2 rounded-full bg-slate-900 transition-all"
          style={{ width: `${Math.min(Math.max(progress, 0), 100)}%` }}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span>{goal.target_date ? `Target: ${formatDate(goal.target_date)}` : "No target date"}</span>
        <span>Remaining {money(goal.remaining_amount)}</span>
      </div>
    </div>
  );
}

export default function GoalPanel({ goals, onCreateGoal }) {
  const [form, setForm] = useState({
    title: "",
    target_amount: "",
    saved_amount: "",
    target_date: "",
    monthly_target: "",
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const update = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.target_amount) return;

    setSaving(true);
    setMessage("");

    try {
      await onCreateGoal({
        title: form.title.trim(),
        target_amount: Number(form.target_amount),
        saved_amount: Number(form.saved_amount || 0),
        target_date: form.target_date || null,
        monthly_target: Number(form.monthly_target || 0),
      });
      setForm({
        title: "",
        target_amount: "",
        saved_amount: "",
        target_date: "",
        monthly_target: "",
      });
      setMessage("Goal saved.");
    } catch (err) {
      setMessage(err?.response?.data?.detail || "Unable to save goal.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">
            Goals
          </p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">
            Upcoming saving goal
          </h2>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          {goals.length} active
        </span>
      </div>

      <form onSubmit={handleSubmit} className="mt-5 grid gap-3 sm:grid-cols-2">
        <input
          value={form.title}
          onChange={(e) => update("title", e.target.value)}
          placeholder="Goal name"
          className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-slate-400"
        />
        <input
          value={form.target_amount}
          onChange={(e) => update("target_amount", e.target.value)}
          type="number"
          min="0"
          placeholder="Target amount"
          className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-slate-400"
        />
        <input
          value={form.saved_amount}
          onChange={(e) => update("saved_amount", e.target.value)}
          type="number"
          min="0"
          placeholder="Already saved"
          className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-slate-400"
        />
        <input
          value={form.monthly_target}
          onChange={(e) => update("monthly_target", e.target.value)}
          type="number"
          min="0"
          placeholder="Monthly save"
          className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-slate-400"
        />
        <input
          value={form.target_date}
          onChange={(e) => update("target_date", e.target.value)}
          type="date"
          className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-slate-400 sm:col-span-2"
        />

        <div className="sm:col-span-2 flex items-center justify-between gap-3">
          <p className="text-sm text-slate-500">Set the goal now and track progress here.</p>
          <button
            type="submit"
            disabled={saving}
            className="rounded-full bg-slate-900 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {saving ? "Saving..." : "Save goal"}
          </button>
        </div>
      </form>

      {message ? (
        <p className="mt-3 text-sm text-slate-600">{message}</p>
      ) : null}

      <div className="mt-6 space-y-3">
        {goals.length ? (
          goals.map((goal) => <GoalRow key={goal.goal_id || goal.title} goal={goal} />)
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-500">
            No savings goals yet.
          </div>
        )}
      </div>
    </section>
  );
}
