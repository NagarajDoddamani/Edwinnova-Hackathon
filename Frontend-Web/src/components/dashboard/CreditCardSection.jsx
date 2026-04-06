import { useEffect, useState } from "react";
import { CreditCard, Gift, TrendingUp } from "lucide-react";

import { api } from "../../services/api";

function formatMoney(value) {
  const amount = Number(value) || 0;
  return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export default function CreditCardSection() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    api
      .get("/cards/recommendations")
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

  const recommendations = Array.isArray(data.recommendations) ? data.recommendations : [];

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <CreditCard className="size-5 text-blue-600" />
        <h2 className="text-lg font-semibold text-slate-900">Maximize Your Card Rewards</h2>
      </div>

      {data.ai_insight ? (
        <div className="mb-5 rounded-2xl border border-blue-200 bg-blue-50 p-4">
          <div className="mb-1 flex items-center gap-2">
            <TrendingUp className="size-4 text-blue-600" />
            <span className="text-sm font-semibold text-blue-700">AI Insight</span>
          </div>
          <p className="text-sm text-blue-700">{data.ai_insight.insight}</p>
          {Number(data.ai_insight.missing_value || 0) > 0 ? (
            <p className="mt-1 font-bold text-blue-800">
              Potential savings: {formatMoney(data.ai_insight.missing_value)}/year
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-4">
        {recommendations.map((card, index) => (
          <article
            key={`${card.card_name}-${index}`}
            className={`rounded-2xl border p-4 transition ${
              index === 0 ? "border-blue-400 bg-blue-50/70" : "border-slate-200 bg-white"
            }`}
          >
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-slate-900">{card.card_name}</span>
                  <span className="text-xs text-slate-500">{card.bank}</span>
                  {index === 0 ? (
                    <span className="rounded-full bg-blue-600 px-2 py-0.5 text-xs font-semibold text-white">
                      Best Match
                    </span>
                  ) : null}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Hidden benefits you may not know
                </p>
              </div>

              <div className="text-right">
                <p className="text-sm font-bold text-emerald-600">
                  +{formatMoney(card.net_annual_benefit)}/yr
                </p>
                <p className="text-xs text-slate-500">
                  Fee: {formatMoney(card.annual_fee)}
                </p>
              </div>
            </div>

            <div className="mt-3">
              <ul className="space-y-1">
                {(card.hidden_benefits || []).slice(0, 2).map((benefit, benefitIndex) => (
                  <li key={benefitIndex} className="flex gap-2 text-xs text-slate-600">
                    <Gift className="mt-0.5 size-3.5 flex-shrink-0 text-blue-500" />
                    <span>{benefit}</span>
                  </li>
                ))}
              </ul>
            </div>
          </article>
        ))}
      </div>

      <p className="mt-4 text-xs text-slate-400">
        Reward values are estimated from your spending pattern.
      </p>
    </section>
  );
}
