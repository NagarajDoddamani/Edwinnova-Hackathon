export default function StatCard({ icon, title, value, onClick }) {
  const Wrapper = onClick ? "button" : "div";

  return (
    <Wrapper
      onClick={onClick}
      className="group rounded-3xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex size-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-700 transition group-hover:bg-slate-900 group-hover:text-white">
          {icon}
        </div>
        <span className="text-2xl font-semibold tracking-tight text-slate-900">
          {value}
        </span>
      </div>
      <p className="mt-4 text-sm font-medium text-slate-500">{title}</p>
    </Wrapper>
  );
}
