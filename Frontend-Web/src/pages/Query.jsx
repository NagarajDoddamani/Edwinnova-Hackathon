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
  Sparkles,
  User,
} from "lucide-react";
import { api } from "../services/api";
import { isAuthenticated } from "../services/auth";

const DEFAULT_COLORS = ["#06b6d4", "#2563eb", "#8b5cf6", "#10b981"];
const QUICK_PROMPTS = [
  "How to improve savings?",
  "Investment plan?",
  "Can I buy a car in 2 years?",
];

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
  const chatScrollRef = useRef(null);
  const autoScrollRef = useRef(true);

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
    const node = chatScrollRef.current;
    if (!node) return undefined;

    const onScroll = () => {
      const distanceFromBottom =
        node.scrollHeight - node.scrollTop - node.clientHeight;
      autoScrollRef.current = distanceFromBottom < 120;
    };

    onScroll();
    node.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      node.removeEventListener("scroll", onScroll);
    };
  }, [messages, loading]);

  useEffect(() => {
    if (!autoScrollRef.current) return;

    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const openHistory = (item) => {
    autoScrollRef.current = true;
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
    autoScrollRef.current = true;
    setMessages([]);
    setQuery("");
    setActiveHistoryId(null);
    setError("");
    focusComposer();
  };

  const applyPrompt = (value) => {
    setQuery(value);
    focusComposer();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const prompt = query.trim();
    if (!prompt || loading) return;
    autoScrollRef.current = true;

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
    <div className="flex h-[100dvh] overflow-hidden bg-[radial-gradient(circle_at_top,_#f8fafc,_#eef2ff_35%,_#e2e8f0_100%)] text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <aside className="hidden w-64 min-h-0 flex-col overflow-hidden border-r border-gray-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 lg:flex">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-gray-400 dark:text-slate-400">
            FinArmor
          </p>
          <h2 className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-100">
            Chat workspace
          </h2>
        </div>

        <button
          type="button"
          onClick={startNewChat}
          className="mb-4 inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 dark:bg-cyan-400 dark:text-slate-950 dark:hover:bg-cyan-300"
        >
          <RefreshCcw size={15} />
          New Chat
        </button>

        <div className="mb-4 rounded-2xl border border-gray-200 bg-gray-50 p-4 dark:border-slate-800 dark:bg-slate-950">
          <p className="text-xs uppercase tracking-[0.3em] text-gray-400 dark:text-slate-400">
            Snapshot
          </p>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <MiniStat label="Income" value={formatMoney(analysis?.income)} />
            <MiniStat label="Expenses" value={formatMoney(analysis?.expenses)} />
            <MiniStat label="Savings" value={formatMoney(analysis?.savings)} />
            <MiniStat label="Goals" value={String(analysis?.goals || 0)} />
          </div>
        </div>

        <p className="mb-3 text-xs uppercase tracking-[0.3em] text-gray-400 dark:text-slate-400">
          Recent chats
        </p>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 scroll-smooth">
          {booting ? (
            <div className="rounded-3xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
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

      <main className="flex min-w-0 flex-1 min-h-0 flex-col overflow-hidden">
        <header className="border-b border-gray-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="inline-flex size-10 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white dark:bg-white dark:text-slate-950">
                <Sparkles size={16} />
              </div>
              <div className="min-w-0">
                <h1 className="truncate text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                  FinArmor AI
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  ChatGPT-style financial assistant
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={startNewChat}
                className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-slate-800 lg:hidden"
              >
                <RefreshCcw size={15} />
                New
              </button>

              <button
                type="button"
                onClick={() => navigate("/dashboard")}
                className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-slate-800"
              >
                <ArrowLeft size={15} />
                Dashboard
              </button>
            </div>
          </div>
        </header>

        <div
          ref={chatScrollRef}
          className="flex-1 overflow-y-auto overscroll-contain scroll-smooth px-4 py-6"
        >
          <div className="mx-auto w-full max-w-3xl">
            {error && messages.length === 0 ? (
              <div className="rounded-3xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
                {error}
              </div>
            ) : null}

            {messages.length === 0 ? (
              <EmptyState analysis={analysis} onPickPrompt={applyPrompt} />
            ) : (
              messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))
            )}

            {loading ? <TypingBubble /> : null}
            <div ref={bottomRef} />
          </div>
        </div>

        <footer className="border-t border-gray-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <form onSubmit={handleSubmit}>
            <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
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
                placeholder="Ask anything about your finances..."
                rows={1}
                onInput={(e) => {
                  e.target.style.height = "auto";
                  e.target.style.height = `${e.target.scrollHeight}px`;
                }}
                className="min-h-[52px] flex-1 resize-none rounded-2xl border border-gray-200 bg-white px-4 py-3 text-sm outline-none transition placeholder:text-gray-400 focus:border-cyan-500 focus:ring-2 focus:ring-cyan-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-100 dark:focus:border-cyan-400 dark:focus:ring-cyan-500/30"
              />

              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-cyan-400 text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-gray-300 dark:bg-cyan-400 dark:text-slate-950 dark:hover:bg-cyan-300 dark:disabled:bg-slate-700 dark:disabled:text-slate-400"
              >
                {loading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Send size={16} />
                )}
              </button>
            </div>

            <p className="mx-auto mt-2 w-full max-w-3xl text-xs text-gray-500 dark:text-slate-400">
              Shift+Enter for a new line.
            </p>
          </form>
        </footer>
      </main>
    </div>
  );
}

function EmptyState({ analysis, onPickPrompt }) {
  const completion = analysis?.profile_completion || "0%";
  const grade = analysis?.grade || "F";
  const score = analysis?.total_score || 0;

  return (
    <div className="mt-20 space-y-4 text-center">
      <div className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.24em] text-gray-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
        <Sparkles size={13} />
        FinArmor AI
      </div>

      <h2 className="text-xl font-medium text-gray-700 dark:text-slate-200">
        How can I help you today?
      </h2>

      <p className="text-sm leading-6 text-gray-500 dark:text-slate-400">
        Profile {completion} complete · Grade {grade} · Score {score}/100.
      </p>

      <div className="flex flex-wrap justify-center gap-2">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onPickPrompt(prompt)}
            className="rounded-full border border-gray-200 bg-white px-3 py-2 text-sm transition hover:bg-cyan-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}

function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const isError = Boolean(message.error);
  const intent = String(message?.data?.intent || "").trim().toLowerCase();
  const showDecisionPanel = !isUser && message.data && intent !== "general";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} chat-fade-in`}>
      <article
        className={`w-full rounded-[28px] border p-4 shadow-sm transition sm:p-5 ${
          isUser
            ? "max-w-[88%] border-slate-900 bg-slate-900 text-white shadow-slate-950/15 dark:border-white/10 dark:bg-white dark:text-slate-950"
            : isError
            ? "max-w-full border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200"
            : "max-w-full border-gray-200 bg-white text-slate-900 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
        }`}
      >
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.32em] text-slate-500 dark:text-slate-400">
          <span
            className={`inline-flex size-7 items-center justify-center rounded-full ${
              isUser
                ? "bg-white/10 text-white dark:bg-slate-950 dark:text-white"
                : isError
                ? "bg-rose-500/15 text-rose-700 dark:bg-rose-500/20 dark:text-rose-100"
                : "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
            }`}
          >
            {isUser ? <User size={13} /> : <Bot size={13} />}
          </span>
          <span>{isUser ? "You" : "FinArmor AI"}</span>
        </div>

        <p
          className={`mt-3 whitespace-pre-line text-sm leading-6 sm:text-[15px] ${
            isUser ? "text-white/90 dark:text-slate-900/90" : ""
          }`}
        >
          {message.text}
        </p>

        {showDecisionPanel ? (
          <div className="mt-4">
            <DecisionPanel data={message.data} />
          </div>
        ) : null}
      </article>
    </div>
  );
}

function DecisionPanel({ data }) {
  const intent = String(data?.intent || "general").trim().toLowerCase();
  if (intent === "general") {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-5">
        <p className="text-sm leading-6 text-slate-800">
          {data?.summary || "No summary available."}
        </p>
      </div>
    );
  }

  const theme = getIntentTheme(intent);
  const decision = data?.decision || data?.readiness?.label || "Needs Review";
  const readiness = data?.readiness || {};
  const risk = data?.risk || {};
  const hasBreakdown = data?.breakdown && typeof data.breakdown === "object";
  const recommendedAssets = Array.isArray(data?.recommended_assets)
    ? data.recommended_assets.filter(Boolean)
    : [];
  const plan = resolvePlanItems(data);
  const breakdown = resolveBreakdown(data, intent);
  const investmentStrategy = resolveInvestmentStrategy(data, intent, recommendedAssets);
  const goalProjection = resolveGoalProjection(data, intent);
  const warnings = Array.isArray(data?.warnings)
    ? data.warnings.filter(Boolean)
    : [];
  const nextStep = data?.next_step || goalProjection?.next_step || "No next step available.";
  const readinessReason = readiness.reason || "";
  const riskReason = risk.reason || "";
  const chart = data?.chart && typeof data.chart === "object" ? data.chart : null;
  const labels =
    Array.isArray(chart?.labels) && chart.labels.length
      ? chart.labels
      : ["Savings", breakdown.allocationLabel, "Expenses", "EMI"];
  const values =
    Array.isArray(chart?.values) && chart.values.length
      ? chart.values
      : [breakdown.savings, breakdown.investment, breakdown.expenses, breakdown.emi];
  const colors =
    Array.isArray(chart?.colors) && chart.colors.length
      ? chart.colors
      : DEFAULT_COLORS;
  const showChart =
    hasBreakdown &&
    ["investment", "purchase", "savings"].includes(intent) &&
    values.some((value) => safeNumber(value) > 0);
  const showBreakdownCards =
    hasBreakdown && ["investment", "purchase", "savings"].includes(intent);
  const showInvestmentPanel = hasBreakdown && intent === "investment" && investmentStrategy;
  const showGoalPanel = hasBreakdown && intent === "goal" && goalProjection;
  const showDebtPanel = hasBreakdown && intent === "debt";

  return (
    <div className="space-y-4">
      <section className={`rounded-3xl border p-5 ${theme.shell}`}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
              Matched category
            </p>
            <h3 className="mt-2 text-2xl font-semibold text-slate-900">
              {theme.label}
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-700">
              {data?.summary || "No summary available."}
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${theme.badge}`}>
              {decision}
            </span>
            <span className="inline-flex items-center justify-center rounded-full bg-white/80 px-3 py-1 text-xs font-semibold text-slate-700">
              {risk.level || "Moderate"} risk
            </span>
          </div>
        </div>
      </section>

      {hasBreakdown ? (
        <>
          <div className="grid gap-3 md:grid-cols-3">
            <MiniCard label="Readiness" value={readiness.label || "Unknown"} tone={theme.tone} />
            <MiniCard label="Intent" value={theme.label} tone={theme.tone} />
            <MiniCard label="Risk" value={risk.level || "Moderate"} tone="amber" />
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
        </>
      ) : null}

      {plan.length ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
            Plan
          </p>
          <ol className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            {plan.map((item, index) => (
              <li key={`${item}-${index}`} className="flex gap-3">
                <span className="mt-0.5 inline-flex size-6 flex-shrink-0 items-center justify-center rounded-full bg-slate-900 text-[11px] font-semibold text-white">
                  {index + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}

      {showBreakdownCards ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MiniCard label="Savings" value={formatMoney(breakdown.savings)} tone="emerald" />
          <MiniCard label={breakdown.allocationLabel} value={formatMoney(breakdown.investment)} tone={theme.tone} />
          <MiniCard label="Expenses" value={formatMoney(breakdown.expenses)} tone="slate" />
          <MiniCard label="EMI" value={formatMoney(breakdown.emi)} tone="rose" />
        </div>
      ) : null}

      {showInvestmentPanel ? (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-600">
            Investment Strategy
          </p>

          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <InfoPanel label="Low Risk" text={investmentStrategy.low_risk || "Use safer assets."} />
            <InfoPanel label="Medium Risk" text={investmentStrategy.medium_risk || "Use a balanced SIP."} />
            <InfoPanel label="High Risk" text={investmentStrategy.high_risk || "Keep high-risk assets small."} />
          </div>

          <div className="mt-4">
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-600">
              Recommended Assets
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {recommendedAssets.length ? (
                recommendedAssets.map((asset) => (
                  <span
                    key={asset}
                    className="rounded-full border border-cyan-200 bg-white px-3 py-1 text-xs font-medium text-cyan-800"
                  >
                    {asset}
                  </span>
                ))
              ) : (
                <span className="text-sm text-cyan-700">
                  No asset suggestions available.
                </span>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {showGoalPanel ? (
        <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 text-cyan-950">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-700">
            Goal Projection
          </p>

          <div className="mt-3 grid gap-3 md:grid-cols-4">
            <MiniCard label="Target" value={formatMoney(goalProjection.target_amount)} tone="cyan" />
            <MiniCard label="Monthly Required" value={formatMoney(goalProjection.monthly_required)} tone="cyan" />
            <MiniCard label="Estimated Months" value={String(goalProjection.estimated_months || 0)} tone="cyan" />
            <MiniCard label="Progress" value={`${safeNumber(goalProjection.progress).toFixed(1)}%`} tone="cyan" />
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <InfoPanel label="Saved" text={formatMoney(goalProjection.saved_amount || 0)} />
            <InfoPanel label="Remaining" text={formatMoney(goalProjection.remaining_amount || 0)} />
          </div>
        </div>
      ) : null}

      {showDebtPanel ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-950">
          <p className="text-xs uppercase tracking-[0.3em] text-rose-700">
            EMI Plan
          </p>

          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <MiniCard label="Monthly EMI" value={formatMoney(breakdown.emi)} tone="rose" />
            <MiniCard label="Risk" value={risk.level || "Moderate"} tone="rose" />
            <MiniCard label="Focus" value={readiness.label || "Review"} tone="rose" />
          </div>

          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <InfoPanel
              label="Repayment Reason"
              text={readinessReason || "Reduce EMI pressure first."}
            />
            <InfoPanel
              label="Action"
              text={nextStep}
            />
          </div>
        </div>
      ) : null}

      {showChart ? (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
              Allocation View
            </p>
            <div className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600">
              Requested {formatMoney(data?.split?.requested_amount || breakdown.investment)}
            </div>
          </div>

          <div className="mt-3 max-h-60 overflow-y-auto pr-1">
            <SplitChart labels={labels} values={values} colors={colors} />
          </div>
        </div>
      ) : null}

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

      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-950">
        <p className="text-xs uppercase tracking-[0.3em] text-emerald-700">
          Next Step
        </p>
        <p className="mt-3 text-sm leading-6">{nextStep}</p>
      </div>
    </div>
  );
}

function getIntentTheme(intent) {
  const value = String(intent || "general").trim().toLowerCase();

  if (value === "investment") {
    return {
      label: formatIntentLabel(value),
      shell: "border-cyan-200 bg-cyan-50/70",
      badge: "bg-cyan-600 text-white",
      tone: "cyan",
    };
  }

  if (value === "goal") {
    return {
      label: formatIntentLabel(value),
      shell: "border-cyan-200 bg-cyan-50/70",
      badge: "bg-cyan-600 text-white",
      tone: "cyan",
    };
  }

  if (value === "debt") {
    return {
      label: formatIntentLabel(value),
      shell: "border-rose-200 bg-rose-50/70",
      badge: "bg-rose-600 text-white",
      tone: "rose",
    };
  }

  if (value === "purchase") {
    return {
      label: formatIntentLabel(value),
      shell: "border-amber-200 bg-amber-50/70",
      badge: "bg-amber-600 text-white",
      tone: "amber",
    };
  }

  if (value === "savings") {
    return {
      label: formatIntentLabel(value),
      shell: "border-emerald-200 bg-emerald-50/70",
      badge: "bg-emerald-600 text-white",
      tone: "emerald",
    };
  }

  return {
    label: formatIntentLabel(value),
    shell: "border-slate-200 bg-slate-50",
    badge: "bg-slate-700 text-white",
    tone: "slate",
  };
}

function resolvePlanItems(data) {
  const plan = Array.isArray(data?.plan) ? data.plan.filter(Boolean) : [];
  if (plan.length) return plan;

  const why = Array.isArray(data?.why) ? data.why.filter(Boolean) : [];
  if (why.length) return why;

  return [];
}

function getAllocationLabel(intent) {
  const value = String(intent || "general").trim().toLowerCase();
  if (value === "goal") return "Goal Contribution";
  if (value === "debt") return "Debt Paydown";
  if (value === "savings") return "Savings Buffer";
  if (value === "purchase") return "Purchase Budget";
  if (value === "investment") return "Investment";
  return "Surplus";
}

function resolveBreakdown(data, intent) {
  const breakdown = data?.breakdown && typeof data.breakdown === "object" ? data.breakdown : null;
  const split = data?.split && typeof data.split === "object" ? data.split : null;
  const inputs = data?.inputs && typeof data.inputs === "object" ? data.inputs : null;

  return {
    savings: safeNumber(breakdown?.savings ?? split?.savings ?? inputs?.savings ?? 0),
    investment: safeNumber(breakdown?.investment ?? split?.investment ?? inputs?.requested_amount ?? 0),
    expenses: safeNumber(breakdown?.expenses ?? inputs?.expenses ?? 0),
    emi: safeNumber(breakdown?.emi ?? split?.debt_emi ?? inputs?.emi ?? 0),
    allocationLabel: breakdown?.allocation_label || getAllocationLabel(intent),
  };
}

function resolveInvestmentStrategy(data, intent, recommendedAssets) {
  if (String(intent || "").trim().toLowerCase() !== "investment") return null;

  const strategy =
    data?.investment_strategy && typeof data.investment_strategy === "object"
      ? data.investment_strategy
      : null;
  return strategy;
}

function resolveGoalProjection(data, intent) {
  const value = String(intent || "").trim().toLowerCase();
  if (value !== "goal") return null;

  const projection =
    data?.goal_projection && typeof data.goal_projection === "object"
      ? data.goal_projection
      : null;
  return projection;
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
      <div className="rounded-3xl border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
        No recent chats yet.
      </div>
    );
  }

  return (
    <div className="space-y-2 pr-1">
      {items.map((item) => {
        const active = item.id === activeId;

        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelect(item)}
            className={`w-full rounded-3xl border p-4 text-left transition ${
              active
                ? "border-cyan-200 bg-cyan-50 shadow-sm dark:border-cyan-900/40 dark:bg-cyan-950/30"
                : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800"
            }`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {item.question}
                </p>
                <p className="mt-2 max-h-10 overflow-hidden text-sm leading-5 text-gray-500 dark:text-slate-400">
                  {takeSnippet(item.answer || item.response?.summary)}
                </p>
              </div>

              <ChevronRight
                size={16}
                className={active ? "shrink-0 text-cyan-600 dark:text-cyan-300" : "shrink-0 text-slate-400"}
              />
            </div>

            <div className="mt-3 flex items-center justify-between gap-3 text-xs text-gray-400 dark:text-slate-500">
              <span className="inline-flex items-center gap-1">
                <Clock3 size={12} />
                {formatDateLabel(item.createdAt)}
              </span>
              <span className="rounded-full bg-gray-100 px-2 py-1 text-[10px] uppercase tracking-[0.24em] text-gray-500 dark:bg-white/5 dark:text-slate-300">
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
      <div className="inline-flex items-center gap-2 rounded-3xl border border-gray-200 bg-white px-4 py-3 text-sm text-gray-600 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
        <Loader2 size={16} className="animate-spin" />
        Thinking...
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white px-3 py-3 dark:border-slate-800 dark:bg-slate-900">
      <p className="text-[11px] uppercase tracking-[0.28em] text-gray-400 dark:text-slate-500">
        {label}
      </p>
      <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
        {value}
      </p>
    </div>
  );
}

function MiniCard({ label, value, tone = "emerald" }) {
  const toneClasses =
    tone === "cyan"
      ? "bg-cyan-50 text-cyan-700"
      : tone === "violet"
      ? "bg-violet-50 text-violet-700"
      : tone === "rose"
      ? "bg-rose-50 text-rose-700"
      : tone === "amber"
      ? "bg-amber-50 text-amber-700"
      : tone === "slate"
      ? "bg-slate-100 text-slate-700"
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
