import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  Bell,
  MessageSquare,
  Send,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";

import { api } from "../services/api";
import { logout, isAuthenticated } from "../services/auth";

import Header from "../components/dashboard/Header";
import StatCard from "../components/dashboard/StatCard";
import AnalysisCard from "../components/dashboard/AnalysisCard";
import QueryList from "../components/dashboard/QueryList";
import BehaviorCard from "../components/dashboard/BehaviorCard";
import GoalPanel from "../components/dashboard/GoalPanel";

function canNotify() {
  return typeof Notification !== "undefined";
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [behavior, setBehavior] = useState(null);
  const [goals, setGoals] = useState([]);
  const [queries, setQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [behaviorLoading, setBehaviorLoading] = useState(true);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [aiAnswer, setAiAnswer] = useState(null);
  const [notificationStatus, setNotificationStatus] = useState(() =>
    canNotify() ? Notification.permission : "unsupported"
  );
  const [notificationMessage, setNotificationMessage] = useState("");

  const pushNotification = (title, body) => {
    if (!canNotify() || Notification.permission !== "granted") return;
    new Notification(title, { body });
  };

  const syncBehaviorOnly = async () => {
    try {
      const res = await api.get("/ai/dashboard");
      setBehavior(res.data?.insight || null);
    } catch (err) {
      console.error(err);
      setBehavior(null);
    } finally {
      setBehaviorLoading(false);
    }
  };

  const refreshAfterChange = async () => {
    const [a, q, g] = await Promise.all([
      api.get("/finance/analysis"),
      api.get("/query/history"),
      api.get("/goals"),
    ]);

    setAnalysis(a.data);
    setQueries(q.data || []);
    setGoals(g.data || []);
    setBehaviorLoading(true);
    await syncBehaviorOnly();
  };

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login");
      return;
    }

    let cancelled = false;

    const boot = async () => {
      try {
        const [u, a, q, g] = await Promise.all([
          api.get("/user/me"),
          api.get("/finance/analysis"),
          api.get("/query/history"),
          api.get("/goals"),
        ]);

        if (cancelled) return;

        setUser(u.data);
        setAnalysis(a.data);
        setQueries(q.data || []);
        setGoals(g.data || []);

        const pct = parseInt(a.data?.profile_completion || "0", 10);
        if (pct <= 20 && !u.data?.name) {
          navigate("/complete-profile");
        }

        setBehaviorLoading(true);
        try {
          const res = await api.get("/ai/dashboard");
          if (!cancelled) {
            setBehavior(res.data?.insight || null);
          }
        } catch (err) {
          console.error(err);
          if (!cancelled) {
            setBehavior(null);
          }
        } finally {
          if (!cancelled) {
            setBehaviorLoading(false);
          }
        }
      } catch (err) {
        console.error(err);
        logout();
        navigate("/login");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    boot();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  useEffect(() => {
    if (!user || !canNotify() || Notification.permission !== "granted") return;

    const key = "finarmor-dashboard-welcome";
    if (sessionStorage.getItem(key)) return;

    pushNotification(
      `Welcome back, ${user.name || user.email}`,
      analysis?.recommendation || "Your dashboard is ready."
    );
    sessionStorage.setItem(key, "1");
  }, [user, analysis]);

  const handleEnableNotifications = async () => {
    if (!canNotify()) {
      setNotificationMessage("This browser does not support notifications.");
      return;
    }

    const permission = await Notification.requestPermission();
    setNotificationStatus(permission);

    if (permission === "granted") {
      pushNotification("FinArmor alerts enabled", "You will see dashboard updates here.");
      setNotificationMessage("Notifications enabled.");
    } else if (permission === "denied") {
      setNotificationMessage("Notifications are blocked in this browser.");
    }
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    const prompt = question.trim();
    if (!prompt || asking) return;

    setAsking(true);
    setAiAnswer(null);

    try {
      const res = await api.post("/query/ask", { question: prompt });
      setAiAnswer(res.data?.answer || res.data?.response?.summary || "No answer returned.");
      setQuestion("");
      const [q, b] = await Promise.all([api.get("/query/history"), api.get("/ai/dashboard")]);
      setQueries(q.data || []);
      setBehavior(b.data?.insight || null);
    } catch (err) {
      console.error(err);
      setAiAnswer("Sorry, something went wrong. Please try again.");
    } finally {
      setAsking(false);
    }
  };

  const handleCreateGoal = async (goal) => {
    await api.post("/goals", goal);
    await refreshAfterChange();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-slate-500 text-lg">Loading your dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#f8fafc,_#eef2ff_35%,_#e2e8f0_100%)] text-slate-900">
      <Header
        onProfile={() => navigate("/personal-details")}
        onLogout={() => {
          logout();
          navigate("/login");
        }}
        onNotify={handleEnableNotifications}
        notificationStatus={notificationStatus}
      />

      <div className="container mx-auto px-4 py-6 lg:py-8">
        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-2xl shadow-slate-900/10">
          <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-cyan-200">
                <Sparkles size={14} />
                Financial control center
              </div>

              <h1 className="mt-4 text-4xl font-semibold tracking-tight">
                Welcome, {user?.name || user?.email}
              </h1>

              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                A live snapshot of your score, behavior, goals, and recent questions.
              </p>

              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => navigate("/query")}
                  className="inline-flex items-center gap-2 rounded-full bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
                >
                  <Send size={16} />
                  Open AI query
                </button>

                <button
                  type="button"
                  onClick={handleEnableNotifications}
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  <Bell size={16} />
                  {notificationStatus === "granted" ? "Alerts enabled" : "Enable alerts"}
                </button>
              </div>

              {notificationMessage ? (
                <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200">
                  {notificationMessage}
                </div>
              ) : null}
            </div>

            <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs uppercase tracking-[0.32em] text-slate-400">
                  Dashboard pulse
                </p>
                <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-semibold text-emerald-300">
                  {analysis?.grade || "F"}
                </span>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <MiniStat label="Health" value={`${analysis?.total_score || 0}/100`} />
                <MiniStat label="Goals" value={String(analysis?.goals || 0)} />
                <MiniStat label="Behavior" value={behavior?.behavior?.label || "Loading"} />
                <MiniStat label="Queries" value={String(queries.length)} />
              </div>

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                  Current focus
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-200">
                  {analysis?.financial_goals || behavior?.goal_focus?.title || "Set one savings goal to start tracking progress."}
                </p>
              </div>
            </div>
          </div>

        </section>

        <div className="mt-6 grid gap-6 md:grid-cols-4">
          <StatCard
            icon={<TrendingUp size={20} />}
            title="Health Score"
            value={`${analysis?.total_score || 0}/100`}
          />
          <StatCard
            icon={<BookOpen size={20} />}
            title="Grade"
            value={analysis?.grade || "F"}
          />
          <StatCard
            icon={<MessageSquare size={20} />}
            title="Total Queries"
            value={queries.length}
          />
          <StatCard
            icon={<Target size={20} />}
            title="Profile Complete"
            value={analysis?.profile_completion || "0%"}
            onClick={() => navigate("/complete-profile")}
          />
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            <AnalysisCard analysis={analysis} />
            <QueryList queries={queries.slice(0, 4)} />
          </div>

          <div className="space-y-6">
            <BehaviorCard insight={behavior} loading={behaviorLoading} />
            <GoalPanel goals={goals} onCreateGoal={handleCreateGoal} />
          </div>
        </div>
      </div>
    </div>
  );
}
