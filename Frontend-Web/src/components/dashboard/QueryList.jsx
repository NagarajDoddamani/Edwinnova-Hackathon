import { Clock3, ChevronRight } from "lucide-react";

function formatDate(value) {
  if (!value) return "Recent";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recent";
  return date.toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
  });
}

function takeSnippet(text, size = 88) {
  const value = (text || "").trim();
  if (!value) return "Tap to view the answer.";
  return value.length <= size ? value : `${value.slice(0, size).trim()}...`;
}

export default function QueryList({ queries }) {
  if (!queries.length) return null;

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
            Activity
          </p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">
            Recent Queries
          </h2>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          {queries.length}
        </span>
      </div>

      <div className="mt-4 space-y-3">
        {queries.map((q, index) => (
          <div
            key={q.id || q._id || index}
            className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition hover:border-slate-300 hover:bg-white"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {q.question}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  {takeSnippet(q.answer || q.response?.summary)}
                </p>
              </div>
              <ChevronRight size={16} className="shrink-0 text-slate-400" />
            </div>

            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <Clock3 size={12} />
              <span>{formatDate(q.created_at || q.timestamp || q.updated_at)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
