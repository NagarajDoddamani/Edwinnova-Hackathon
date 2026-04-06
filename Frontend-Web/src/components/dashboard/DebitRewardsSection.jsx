import { useEffect, useState } from "react";
import { ChevronRight, Wallet } from "lucide-react";

import { api } from "../../services/api";

export default function DebitRewardsSection() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    api
      .get("/cards/debit-rewards")
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return null;
  if (!data || !data.eligible) return null;

  const tips = Array.isArray(data.tips) ? data.tips : [];

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Wallet className="size-5 text-violet-600" />
        <h2 className="text-lg font-semibold text-slate-900">Maximize Your Rewards</h2>
      </div>

      <p className="mb-4 text-sm text-slate-500">
        You do not need a credit card to earn rewards. Here is what works for you:
      </p>

      <div className="space-y-3">
        {tips.map((tip, index) => (
          <article
            key={`${tip.title}-${index}`}
            className="flex items-start gap-3 rounded-2xl border border-slate-200 p-4 transition hover:bg-slate-50"
          >
            <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-violet-100 text-sm font-bold text-violet-700">
              {index + 1}
            </div>

            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-900">{tip.title}</p>
              <p className="mt-0.5 text-xs text-slate-500">{tip.description}</p>
              <p className="mt-1 text-xs font-medium text-violet-700">→ {tip.action}</p>
            </div>

            <ChevronRight className="mt-1 size-4 flex-shrink-0 text-slate-400" />
          </article>
        ))}
      </div>
    </section>
  );
}
