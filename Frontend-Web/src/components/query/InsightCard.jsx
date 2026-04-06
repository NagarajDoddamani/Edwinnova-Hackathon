const TONE_STYLES = {
  blue: "border-cyan-100 bg-cyan-50 text-cyan-900",
  violet: "border-violet-100 bg-violet-50 text-violet-900",
  rose: "border-rose-100 bg-rose-50 text-rose-900",
  slate: "border-slate-200 bg-slate-50 text-slate-900",
};

export default function InsightCard({
  eyebrow,
  title,
  text,
  tone = "blue",
  className = "",
}) {
  const toneClass = TONE_STYLES[tone] || TONE_STYLES.slate;

  return (
    <section className={`rounded-2xl border p-4 ${toneClass} ${className}`}>
      {eyebrow ? (
        <p className="text-[11px] uppercase tracking-[0.3em] opacity-70">
          {eyebrow}
        </p>
      ) : null}
      {title ? <h4 className="mt-2 text-sm font-semibold">{title}</h4> : null}
      {text ? <p className="mt-2 text-sm leading-6 opacity-90">{text}</p> : null}
    </section>
  );
}
