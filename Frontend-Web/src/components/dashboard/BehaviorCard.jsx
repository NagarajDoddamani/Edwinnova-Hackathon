function money(value) {
  const amount = Number(value || 0);
  return `Rs. ${new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(Number.isFinite(amount) ? amount : 0)}`;
}

function Pill({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-900">{value}</p>
    </div>
  );
}

export default function BehaviorCard({ insight, loading }) {
  if (loading) {
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="h-4 w-40 animate-pulse rounded-full bg-slate-100" />
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
          <div className="h-20 animate-pulse rounded-2xl bg-slate-100" />
        </div>
        <div className="mt-4 h-24 animate-pulse rounded-2xl bg-slate-100" />
      </section>
    );
  }

  if (!insight) return null;

  const sentiment = insight.sentiment || {};
  const behavior = insight.behavior || {};
  const risk = insight.risk || {};
  const highlights = insight.highlights || [];
  const recommendations = insight.recommendations || [];
  const goalFocus = insight.goal_focus || {};

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">AI Insight</p>
          <h2 className="mt-2 text-xl font-semibold text-slate-900">
            Sentiment and Behavior
          </h2>
        </div>

        <div className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
          {risk.level || "Moderate"} risk
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <Pill label="Sentiment" value={`${sentiment.label || "Balanced"} ${sentiment.score ? `(${sentiment.score}/100)` : ""}`} />
        <Pill label="Behavior" value={`${behavior.label || "Stable"} ${behavior.score ? `(${behavior.score}/100)` : ""}`} />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Why</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {sentiment.reason || behavior.reason || "No insight available."}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Next action</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {insight.next_action || "Keep reviewing your plan monthly."}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Highlights</p>
          <ul className="mt-3 space-y-2">
            {highlights.length ? highlights.map((item) => (
              <li key={item} className="flex gap-2 text-sm leading-6 text-slate-600">
                <span className="mt-2 size-1.5 rounded-full bg-cyan-500" />
                <span>{item}</span>
              </li>
            )) : (
              <li className="text-sm text-slate-500">No highlights available.</li>
            )}
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Recommendations</p>
          <ul className="mt-3 space-y-2">
            {recommendations.length ? recommendations.map((item) => (
              <li key={item} className="flex gap-2 text-sm leading-6 text-slate-600">
                <span className="mt-2 size-1.5 rounded-full bg-slate-900" />
                <span>{item}</span>
              </li>
            )) : (
              <li className="text-sm text-slate-500">No recommendations yet.</li>
            )}
          </ul>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Pill label="Goal focus" value={goalFocus.title || "Emergency fund"} />
        <Pill label="Target" value={money(goalFocus.target_amount)} />
        <Pill label="Notification" value={insight.notification?.title || "FinArmor check-in"} />
      </div>
    </section>
  );
}
