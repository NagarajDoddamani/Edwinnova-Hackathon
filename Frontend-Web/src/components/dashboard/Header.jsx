import { Bell, TrendingUp, User, LogOut } from "lucide-react";

export default function Header({
  onProfile,
  onLogout,
  onNotify,
  notificationStatus,
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/80 backdrop-blur">
      <div className="container mx-auto flex items-center justify-between gap-3 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 via-blue-700 to-cyan-500 shadow-lg shadow-blue-500/20">
            <TrendingUp className="text-white" size={18} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-slate-500">
              FinArmor
            </p>
            <span className="text-lg font-semibold text-slate-900">Dashboard</span>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          {onNotify ? (
            <button
              onClick={onNotify}
              className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <Bell size={16} />
              {notificationStatus === "granted" ? "Alerts on" : "Enable alerts"}
            </button>
          ) : null}

          <button
            onClick={onProfile}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            <User size={16} />
            Profile
          </button>

          <button
            onClick={onLogout}
            className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
