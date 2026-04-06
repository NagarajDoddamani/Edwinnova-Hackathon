import { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_PALETTE = ["#06b6d4", "#2563eb", "#8b5cf6", "#10b981"];

function safeNumber(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num : 0;
}

function formatMoney(value) {
  const amount = Math.max(Math.round(safeNumber(value)), 0);
  return `Rs. ${new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: 0,
  }).format(amount)}`;
}

function useInViewOnce() {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || visible) return undefined;

    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return undefined;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "120px" }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [visible]);

  return [ref, visible];
}

export default function ChartCard({
  title,
  description,
  labels = [],
  values = [],
  colors = DEFAULT_PALETTE,
  followUpLabel = "Ask follow-up",
  onAskFollowUp,
}) {
  const [ref, visible] = useInViewOnce();
  const numericValues = useMemo(
    () => labels.map((_, index) => safeNumber(values[index])),
    [labels, values]
  );
  const total = numericValues.reduce((sum, value) => sum + value, 0);

  if (total <= 0) return null;

  const maxValue = Math.max(...numericValues, 1);

  return (
    <section
      ref={ref}
      className="chart-pop-in rounded-2xl border border-slate-200 bg-gradient-to-br from-white via-white to-slate-50 p-4 shadow-sm shadow-slate-200/50 dark:border-slate-800 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950 dark:shadow-black/20"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">
            Chart
          </p>
          <h4 className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h4>
          {description ? (
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{description}</p>
          ) : null}
        </div>

        <span className="rounded-full bg-slate-900 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-white dark:bg-cyan-400 dark:text-slate-950">
          AI view
        </span>
      </div>

      <div className="mt-4 overflow-x-auto">
        <div className="min-w-[320px] space-y-3 pr-1">
          {!visible ? (
            Array.from({ length: Math.min(labels.length || 3, 4) }).map((_, index) => (
              <div key={index} className="space-y-2 animate-pulse">
                <div className="flex items-center justify-between gap-3">
                  <div className="h-3 w-28 rounded-full bg-slate-200 dark:bg-slate-800" />
                  <div className="h-3 w-16 rounded-full bg-slate-200 dark:bg-slate-800" />
                </div>
                <div className="h-3 rounded-full bg-slate-200 dark:bg-slate-800" />
              </div>
            ))
          ) : (
            labels.map((label, index) => {
              const value = numericValues[index];
              const percent = maxValue > 0 ? Math.max((value / maxValue) * 100, 6) : 0;
              const color = colors[index] || DEFAULT_PALETTE[index % DEFAULT_PALETTE.length];

              return (
                <div key={label} className="space-y-2">
                  <div className="flex items-center justify-between gap-3 text-sm text-slate-600 dark:text-slate-300">
                    <span className="truncate">{label}</span>
                    <span className="shrink-0 font-medium text-slate-900 dark:text-slate-100">
                      {formatMoney(value)}
                    </span>
                  </div>

                  <div className="h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${percent}%`,
                        background: `linear-gradient(90deg, ${color}, #2563eb)`,
                      }}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={onAskFollowUp}
          className="inline-flex items-center rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs font-semibold text-cyan-700 transition hover:bg-cyan-100 dark:border-cyan-900/40 dark:bg-cyan-950/30 dark:text-cyan-200 dark:hover:bg-cyan-950/50"
        >
          {followUpLabel}
        </button>
        <p className="text-xs text-slate-500 dark:text-slate-400">Swipe horizontally if the chart needs more room.</p>
      </div>
    </section>
  );
}
