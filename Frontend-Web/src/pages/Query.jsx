import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Bot,
  ChevronRight,
  Clock3,
  Loader2,
  RefreshCcw,
  Send,
  User,
} from "lucide-react";
import { api } from "../services/api";
import { isAuthenticated } from "../services/auth";

const DEFAULT_COLORS = ["#14b8a6", "#ef4444", "#3b82f6", "#8b5cf6"];

function makeId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

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

function formatDateLabel(value) {
  if (!value) return "Recent";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recent";

  return date.toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
  });
}

function takeSnippet(text, size = 92) {
  const value = (text || "").trim();
  if (!value) return "Tap to open this answer.";
  return value.length <= size ? value : `${value.slice(0, size).trim()}...`;
}

function normalizeHistoryItem(item, index = 0) {
  const response =
    item?.response && typeof item.response === "object" ? item.response : null;
  const question = item?.question || response?.question || "Untitled question";
  const answer = item?.answer || response?.summary || "";
  const createdAt = item?.created_at || item?.timestamp || item?.updated_at || null;
  const fallbackId = createdAt ? `${createdAt}-${index}` : `${question}-${index}`;

  return {
    id: String(item?.id || item?._id || fallbackId),
    question,
    answer,
    response,
    source: item?.source || response?.source || "history",
    createdAt,
  };
}

function normalizeHistoryList(items) {
  if (!Array.isArray(items)) return [];
  return items.map(normalizeHistoryItem);
}

export default function Query() {
  const navigate = useNavigate();
  const composerRef = useRef(null);
  const bottomRef = useRef(null);

  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeHistoryId, setActiveHistoryId] = useState(null);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState("");

  const focusComposer = () => {
    window.requestAnimationFrame(() => {
      composerRef.current?.focus();
    });
  };

  const refreshHistory = async () => {
    try {
      const res = await api.get("/query/history");
      const nextHistory = normalizeHistoryList(res.data);
      setHistory(nextHistory);
      return nextHistory;
    } catch (err) {
      console.error(err);
      return history;
    }
  };

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate("/login");
      return;
    }

    let cancelled = false;

    const load = async () => {
      try {
        const [analysisRes, historyRes] = await Promise.all([
          api.get("/finance/analysis"),
          api.get("/query/history"),
        ]);

        if (cancelled) return;

        setAnalysis(analysisRes.data || null);
        setHistory(normalizeHistoryList(historyRes.data));
      } catch (err) {
        console.error(err);
        if (!cancelled) setError("Unable to load your finance data right now.");
      } finally {
        if (!cancelled) setBooting(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const openHistory = (item) => {
    setActiveHistoryId(item.id);
    setQuery(item.question || "");
    setError("");

    const assistantText = item.answer || item.response?.summary || "No response available.";
    setMessages([
      {
        id: `${item.id}-user`,
        role: "user",
        text: item.question || "Question",
      },
      {
        id: `${item.id}-assistant`,
        role: "assistant",
        text: assistantText,
        data: item.response || null,
        source: item.source || "history",
      },
    ]);

    focusComposer();
  };

  const startNewChat = () => {
    setMessages([]);
    setQuery("");
    setActiveHistoryId(null);
    setError("");
    focusComposer();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const prompt = query.trim();
    if (!prompt || loading) return;

    const userMessage = {
      id: makeId(),
      role: "user",
      text: prompt,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError("");
    setActiveHistoryId(null);

    try {
      const res = await api.post("/ai/query", {
        question: prompt,
      });

      const response =
        res.data?.response && typeof res.data.response === "object"
          ? res.data.response
          : null;
      const answer =
        response?.summary || res.data?.answer || "I could not generate a summary.";

      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          text: answer,
          data: response,
          source: res.data?.source || (response ? "gemini" : "fallback"),
        },
      ]);

      setQuery("");
      const nextHistory = await refreshHistory();
      if (nextHistory?.length) {
        setActiveHistoryId(nextHistory[0].id);
      }
    } catch (err) {
      console.error(err);
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        "AI failed to respond.";

      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          text: detail,
          error: true,
        },
      ]);
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen overflow-hidden bg-slate-950 text-slate-100">
      <div className="grid h-full overflow-hidden lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="h-full overflow-y-auto border-r border-white/10 bg-slate-950/95 px-4 py-5 backdrop-blur">
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => navigate("/dashboard")}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10"
            >
              <ArrowLeft size={15} />
              Dashboard
            </button>

            <button
              type="button"
              onClick={startNewChat}
              className="inline-flex items-center gap-2 rounded-full bg-cyan-400 px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              <RefreshCcw size={15} />
              New chat
            </button>
          </div>

          <div className="mt-6 rounded-3xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-400">
                Snapshot
              </p>
              <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-xs font-semibold text-emerald-300">
                {analysis?.profile_completion || "0%"}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <MiniStat label="Income" value={formatMoney(analysis?.income)} />
              <MiniStat label="Expenses" value={formatMoney(analysis?.expenses)} />
              <MiniStat label="Savings" value={formatMoney(analysis?.savings)} />
              <MiniStat label="Goals" value={String(analysis?.goals || 0)} />
            </div>
          </div>

          <div className="mt-6">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                Recent chats
              </p>
              <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-slate-300">
                {history.length}
              </span>
            </div>

            {booting ? (
              <div className="rounded-3xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
                Loading recent chats...
              </div>
            ) : (
              <RecentQueryList
                items={history}
                activeId={activeHistoryId}
                onSelect={openHistory}
              />
            )}
          </div>
        </aside>

        <main className="flex h-full min-h-0 flex-col overflow-hidden bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.95),_rgba(241,245,249,0.96)_35%,_rgba(226,232,240,0.98)_100%)] text-slate-900">
          <header className="border-b border-slate-200/80 bg-white/80 px-4 py-4 backdrop-blur">
            <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
                  Query
                </p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900">
                  FinArmor AI
                </h2>
              </div>

              <button
                type="button"
                onClick={startNewChat}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                <RefreshCcw size={15} />
                Clear
              </button>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto px-4 py-6">
            <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
              {error && messages.length === 0 ? (
                <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                  {error}
                </div>
              ) : null}

              {messages.length === 0 ? (
                <div className="rounded-3xl border border-slate-200 bg-white p-4 text-sm text-slate-500 shadow-sm">
                  Ask one finance question.
                </div>
              ) : (
                messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))
              )}

              {loading ? <TypingBubble /> : null}
              <div ref={bottomRef} />
            </div>
          </div>

          <footer className="border-t border-slate-200 bg-white/90 px-4 py-4 backdrop-blur">
            <form onSubmit={handleSubmit} className="mx-auto w-full max-w-5xl">
              <div className="rounded-3xl border border-slate-200 bg-slate-50 p-3 shadow-sm">
                <textarea
                  ref={composerRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                  placeholder="Ask about saving, investing, debt, or whether you can afford a purchase..."
                  rows={2}
                  className="w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-400"
                />

                <div className="mt-2 flex items-center justify-end gap-3 border-t border-slate-200 pt-3">
                  <button
                    type="submit"
                    disabled={loading || !query.trim()}
                    className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                    Send
                  </button>
                </div>
              </div>
            </form>
          </footer>
        </main>
      </div>
    </div>
  );
}

function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const isError = Boolean(message.error);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`w-full max-w-4xl rounded-3xl px-5 py-4 shadow-sm ${
          isUser
            ? "bg-slate-900 text-white"
            : isError
            ? "border border-rose-200 bg-rose-50 text-rose-900"
            : "border border-slate-200 bg-white text-slate-900"
        }`}
      >
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.3em]">
          {isUser ? <User size={13} /> : <Bot size={13} />}
          <span>{isUser ? "You" : "FinArmor AI"}</span>
        </div>

        <p
          className={`mt-3 whitespace-pre-line text-sm leading-6 ${
            isUser ? "text-white/90" : ""
          }`}
        >
          {message.text}
        </p>

        {!isUser && message.data ? (
          <div className="mt-4">
            <DecisionPanel data={message.data} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function DecisionPanel({ data }) {
  const split = data?.split || {};
  const chart = data?.chart || {};
  const recommendedAssets = Array.isArray(data?.recommended_assets)
    ? data.recommended_assets
    : [];
  const why = Array.isArray(data?.why) ? data.why : [];
  const warnings = Array.isArray(data?.warnings) ? data.warnings : [];
  const goalFocus =
    data?.goal_focus && typeof data.goal_focus === "object" ? data.goal_focus : null;
  const decision = data?.decision || data?.readiness?.label || "Needs Review";
  const intentLabel = formatIntentLabel(data?.intent);
  const readinessReason = data?.readiness?.reason || "";
  const riskReason = data?.risk?.reason || "";
  const nextStep = data?.next_step || "No next step available.";
  const labels =
    Array.isArray(chart.labels) && chart.labels.length
      ? chart.labels
      : ["Emergency Fund", "Debt / EMI", "Savings", "Investment"];
  const values =
    Array.isArray(chart.values) && chart.values.length
      ? chart.values
      : [split.emergency_fund, split.debt_emi, split.savings, split.investment];
  const colors =
    Array.isArray(chart.colors) && chart.colors.length
      ? chart.colors
      : DEFAULT_COLORS;

  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-2">
        <MiniCard
          label="Readiness"
          value={data?.readiness?.label || "Unknown"}
          tone="emerald"
        />

        <MiniCard
          label="Risk"
          value={data?.risk?.level || "Moderate"}
          tone="amber"
        />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <MiniCard label="Decision" value={decision} tone="cyan" />
        <MiniCard label="Intent" value={intentLabel} tone="emerald" />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <InfoPanel
          label="Readiness Reason"
          text={readinessReason || "No readiness reason available."}
        />
        <InfoPanel
          label="Risk Reason"
          text={riskReason || "No risk reason available."}
        />
      </div>

      {goalFocus ? (
        <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 text-violet-950">
          <p className="text-xs uppercase tracking-[0.3em] text-violet-700">
            Goal Focus
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-violet-600 px-3 py-1 text-xs font-semibold text-white">
              {goalFocus.title || "Active goal"}
            </span>
            <span className="text-sm text-violet-900/80">
              {goalFocus.reason || "Goal context available."}
            </span>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <MiniCard
              label="Target"
              value={formatMoney(goalFocus.target_amount)}
              tone="cyan"
            />
            <MiniCard
              label="Saved"
              value={formatMoney(goalFocus.saved_amount)}
              tone="emerald"
            />
            <MiniCard
              label="Remaining"
              value={formatMoney(goalFocus.remaining_amount)}
              tone="amber"
            />
            <MiniCard
              label="Progress"
              value={`${safeNumber(goalFocus.progress).toFixed(1)}%`}
              tone="cyan"
            />
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <InfoPanel
              label="Monthly Target"
              text={formatMoney(goalFocus.monthly_target || 0)}
            />
            <InfoPanel
              label="Goal Next Step"
              text={goalFocus.next_step || "Keep the goal moving steadily."}
            />
          </div>
        </div>
      ) : null}

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
          Recommended Assets
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {recommendedAssets.length ? (
            recommendedAssets.map((asset) => (
              <span
                key={asset}
                className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700"
              >
                {asset}
              </span>
            ))
          ) : (
            <span className="text-sm text-slate-500">
              No asset suggestions available.
            </span>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
          Why This Plan
        </p>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          {why.length ? why.map((item) => <li key={item}>- {item}</li>) : <li>- No explanation available.</li>}
        </ul>
      </div>

      {warnings.length ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-900">
          <p className="text-xs uppercase tracking-[0.3em] text-amber-700">
            Warning
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {warnings.map((item) => (
              <li key={item}>- {item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
            Chart
          </p>
          <div className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">
            Requested {formatMoney(split.requested_amount)}
          </div>
        </div>

        <div className="mt-3 max-h-60 overflow-y-auto pr-1">
          <SplitChart labels={labels} values={values} colors={colors} />
        </div>
      </div>

      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-950">
        <p className="text-xs uppercase tracking-[0.3em] text-emerald-700">
          Next Step
        </p>
        <p className="mt-3 text-sm leading-6">{nextStep}</p>
      </div>
    </div>
  );
}

function SplitChart({ labels, values, colors }) {
  const numericValues = labels.map((_, index) => safeNumber(values[index]));
  const total = numericValues.reduce((sum, value) => sum + value, 0);

  if (total <= 0) {
    return (
      <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
        No allocation data available yet.
      </div>
    );
  }

  return (
    <div className="mt-4 space-y-3">
      {labels.map((label, index) => {
        const value = numericValues[index];
        const percent = total > 0 ? Math.max((value / total) * 100, 0) : 0;

        return (
          <div key={label} className="space-y-1.5">
            <div className="flex items-center justify-between gap-3 text-sm text-slate-600">
              <span>{label}</span>
              <span>{formatMoney(value)}</span>
            </div>

            <div className="h-3 overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${percent}%`,
                  backgroundColor:
                    colors[index] || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RecentQueryList({ items, activeId, onSelect }) {
  if (!items.length) {
    return (
      <div className="rounded-3xl border border-dashed border-white/10 bg-white/5 p-4 text-sm text-slate-400">
        No recent chats yet.
      </div>
    );
  }

  return (
    <div className="max-h-[calc(100vh-420px)] space-y-2 overflow-y-auto pr-1">
      {items.map((item) => {
        const active = item.id === activeId;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item)}
            className={`w-full rounded-3xl border p-4 text-left transition ${
              active
                ? "border-cyan-400/70 bg-cyan-400/10"
                : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">
                  {item.question}
                </p>
                <p className="mt-2 max-h-10 overflow-hidden text-sm leading-5 text-slate-300">
                  {takeSnippet(item.answer || item.response?.summary)}
                </p>
              </div>

              <ChevronRight
                size={16}
                className={active ? "shrink-0 text-cyan-300" : "shrink-0 text-slate-500"}
              />
            </div>

            <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-400">
              <span className="inline-flex items-center gap-1">
                <Clock3 size={12} />
                {formatDateLabel(item.createdAt)}
              </span>
              <span className="rounded-full bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.24em] text-slate-300">
                {active ? "Open" : "View"}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function TypingBubble() {
  return (
    <div className="flex justify-start">
      <div className="inline-flex items-center gap-2 rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
        <Loader2 size={16} className="animate-spin" />
        Thinking...
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-3">
      <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function MiniCard({ label, value, tone = "emerald" }) {
  const toneClasses =
    tone === "cyan"
      ? "bg-cyan-50 text-cyan-700"
      : tone === "amber"
      ? "bg-amber-50 text-amber-700"
      : "bg-emerald-50 text-emerald-700";

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{label}</p>
      <div className={`mt-2 inline-flex rounded-full px-3 py-1 text-sm font-semibold ${toneClasses}`}>
        {value}
      </div>
    </div>
  );
}

function InfoPanel({ label, text }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{label}</p>
      <p className="mt-3 text-sm leading-6 text-slate-700">{text}</p>
    </div>
  );
}

function formatIntentLabel(intent) {
  const value = String(intent || "mixed").trim().toLowerCase();
  if (!value) return "Mixed";
  return value.charAt(0).toUpperCase() + value.slice(1);
}
