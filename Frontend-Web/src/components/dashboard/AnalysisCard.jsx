function money(value) {
  const amount = Number(value || 0);
  return `Rs. ${new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(Number.isFinite(amount) ? amount : 0)}`;
}

export default function AnalysisCard({ analysis }) {
  if (!analysis) return null;

  const score = Number(analysis.total_score || 0);
  const grade = analysis.grade || "F";
  const breakdown = analysis.score_breakdown || {};
  const recommendations = analysis.recommendations?.length
    ? analysis.recommendations
    : analysis.recommendation
    ? [analysis.recommendation]
    : [];

  const ringColor =
    score >= 80 ? "#16a34a" : score >= 60 ? "#2563eb" : score >= 40 ? "#d97706" : "#dc2626";
  const gradeColor =
    grade === "A+" || grade === "A"
      ? "text-emerald-600"
      : grade === "B"
      ? "text-blue-600"
      : grade === "C"
      ? "text-amber-600"
      : grade === "D"
      ? "text-orange-500"
      : "text-rose-600";

  const circumference = 2 * Math.PI * 40;
  const strokeDash = (Math.max(score, 0) / 100) * circumference;

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">
            Analysis
          </p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">
            Financial Health Score
          </h2>
        </div>

        <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          {analysis.profile_completion || "0%"} profile
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[220px_minmax(0,1fr)]">
        <div className="flex items-center justify-center">
          <div className="relative flex items-center justify-center">
            <svg width="120" height="120" className="-rotate-90">
              <circle cx="60" cy="60" r="40" fill="none" stroke="#e5e7eb" strokeWidth="12" />
              <circle
                cx="60"
                cy="60"
                r="40"
                fill="none"
                stroke={ringColor}
                strokeWidth="12"
                strokeDasharray={`${strokeDash} ${circumference}`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute text-center">
              <p className="text-3xl font-semibold" style={{ color: ringColor }}>
                {score}
              </p>
              <p className="text-xs text-slate-400">/100</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <p className="text-sm text-slate-500">Overall Grade</p>
              <p className={`text-5xl font-semibold ${gradeColor}`}>{grade}</p>
            </div>

            <div className="min-w-[180px] rounded-2xl bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">
                Recommendation
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-700">
                {analysis.recommendation || "Keep reviewing the plan monthly."}
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ScoreBar label="Profile" score={breakdown.profile_score} max={25} />
            <ScoreBar label="Context" score={breakdown.context_score} max={25} />
            <ScoreBar label="Behavior" score={breakdown.behavior_score} max={25} />
            <ScoreBar label="Goals" score={breakdown.goal_score} max={25} />
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Income" value={money(analysis.income)} />
        <Metric label="Expenses" value={money(analysis.expenses)} />
        <Metric label="Savings" value={money(analysis.savings)} />
        <Metric label="Debt / EMI" value={money((analysis.debt || 0) + (analysis.emi || 0))} />
      </div>

      {analysis.financial_goals ? (
        <div className="mt-5 rounded-2xl border border-cyan-100 bg-cyan-50 p-4">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-600">Current goal</p>
          <p className="mt-2 font-semibold text-cyan-950">{analysis.financial_goals}</p>
        </div>
      ) : null}

      {recommendations.length ? (
        <div className="mt-6">
          <p className="text-sm font-semibold text-slate-900">Recommendations</p>
          <ul className="mt-3 space-y-2">
            {recommendations.map((item) => (
              <li key={item} className="flex gap-2 text-sm leading-6 text-slate-600">
                <span className="mt-2 size-1.5 rounded-full bg-slate-900" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function ScoreBar({ label, score, max }) {
  const pct = Math.round(((score || 0) / max) * 100);
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{label}</p>
        <p className="text-xs font-semibold text-slate-700">
          {score || 0}/{max}
        </p>
      </div>
      <div className="h-2 rounded-full bg-slate-200">
        <div
          className="h-2 rounded-full bg-slate-900 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}
