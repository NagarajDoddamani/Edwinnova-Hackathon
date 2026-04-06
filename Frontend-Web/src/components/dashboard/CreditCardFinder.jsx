import { useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  CreditCard,
  Loader2,
  Plus,
  X,
  Sparkles,
  RefreshCcw,
} from "lucide-react";

import { api } from "../../services/api";

const REQUIREMENTS = [
  { key: "petrol", label: "Petrol / Fuel" },
  { key: "flight_booking", label: "Flight booking" },
  { key: "travel", label: "Travel" },
  { key: "hotel_booking", label: "Hotel booking" },
  { key: "dining", label: "Dining" },
  { key: "online_shopping", label: "Online shopping" },
  { key: "grocery", label: "Grocery" },
  { key: "cashback", label: "Cashback" },
  { key: "lounge_access", label: "Lounge access" },
  { key: "movie_entertainment", label: "Movies / entertainment" },
  { key: "fee_waiver", label: "Fee waiver" },
];

const REQUIREMENT_LABELS = Object.fromEntries(REQUIREMENTS.map((item) => [item.key, item.label]));

function formatMoney(value) {
  const amount = Number(value) || 0;
  return `Rs. ${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function RequirementChip({ label, selected, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition ${
        selected
          ? "border-cyan-500 bg-cyan-50 text-cyan-900"
          : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <span
        className={`flex size-4 items-center justify-center rounded-full border text-[10px] ${
          selected ? "border-cyan-500 bg-cyan-500 text-white" : "border-slate-300 text-transparent"
        }`}
      >
        <Check className="size-3" />
      </span>
      {label}
    </button>
  );
}

export default function CreditCardFinder() {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState([]);
  const [customRequirement, setCustomRequirement] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const selectedLabels = useMemo(
    () =>
      selected
        .map((key) => REQUIREMENTS.find((item) => item.key === key)?.label || key)
        .filter(Boolean),
    [selected]
  );

  const normalizeRequirement = (value) => value.trim().toLowerCase().replace(/\s+/g, " ");
  const isPresetRequirement = (value) => REQUIREMENTS.some((item) => item.key === value);
  const displayRequirement = (value) => REQUIREMENT_LABELS[value] || value.trim().replace(/\s+/g, " ");

  const toggleRequirement = (key) => {
    setError("");
    setSelected((current) =>
      current.includes(key) ? current.filter((item) => item !== key) : [...current, key]
    );
  };

  const addCustomRequirement = () => {
    const value = customRequirement.trim();
    if (!value) return;

    const normalizedValue = normalizeRequirement(value);
    const duplicate = selected.some((item) => normalizeRequirement(item) === normalizedValue);
    if (duplicate) {
      setCustomRequirement("");
      return;
    }

    setError("");
    setSelected((current) => [...current, value]);
    setCustomRequirement("");
  };

  const removeRequirement = (value) => {
    setError("");
    setSelected((current) =>
      current.filter((item) => normalizeRequirement(item) !== normalizeRequirement(value))
    );
  };

  const selectAll = () => {
    setError("");
    setSelected((current) => {
      const customOnly = current.filter((item) => !isPresetRequirement(item));
      const merged = [...REQUIREMENTS.map((item) => item.key), ...customOnly];
      const unique = [];

      for (const item of merged) {
        if (!unique.some((existing) => normalizeRequirement(existing) === normalizeRequirement(item))) {
          unique.push(item);
        }
      }

      return unique;
    });
  };

  const clearAll = () => {
    setError("");
    setSelected([]);
    setCustomRequirement("");
  };

  const handleSubmit = async () => {
    if (!selected.length) {
      setError("Please select at least one requirement.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await api.post("/cards/personalized", {
        selected_requirements: selected,
        prompt:
          "Suggest the best credit card for this user using only the retrieved card catalog, the user's financial snapshot, and the selected requirements. Keep the answer concise, specific, and practical.",
      });

      setResult(res.data?.result || res.data?.response || null);
    } catch (err) {
      console.error(err);
      const message =
        err?.response?.data?.detail ||
        "Unable to get a card recommendation right now. Please check the backend console.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const rankedCards = Array.isArray(result?.ranked_cards) ? result.ranked_cards : [];
  const matchedRequirements = Array.isArray(result?.matched_requirements)
    ? result.matched_requirements
    : [];
  const warnings = Array.isArray(result?.warnings) ? result.warnings : [];

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <CreditCard className="size-5 text-cyan-600" />
            <h2 className="text-lg font-semibold text-slate-900">Find the best credit card</h2>
          </div>
          <p className="mt-2 max-w-2xl text-sm text-slate-500">
            Pick the spending needs you care about, then FinArmor will suggest the best card from
            the catalog using your financial profile.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-cyan-50 px-4 py-2.5 text-sm font-semibold text-cyan-900 transition hover:bg-cyan-100"
        >
          <Sparkles size={16} />
          {open ? "Close finder" : "Open finder"}
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {open ? (
        <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Requirements</p>
              <p className="mt-1 text-sm text-slate-500">
                Choose one or more categories. You can select all if you want a full comparison.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={selectAll}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Select all
              </button>
              <button
                type="button"
                onClick={clearAll}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                Clear
              </button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {REQUIREMENTS.map((item) => (
              <RequirementChip
                key={item.key}
                label={item.label}
                selected={selected.includes(item.key)}
                onClick={() => toggleRequirement(item.key)}
              />
            ))}
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
            <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3 py-2.5">
              <input
                type="text"
                value={customRequirement}
                onChange={(e) => setCustomRequirement(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addCustomRequirement();
                  }
                }}
                placeholder="Add other requirement like airport lounge access"
                className="min-w-0 flex-1 bg-transparent text-sm text-slate-700 outline-none placeholder:text-slate-400"
              />
              <button
                type="button"
                onClick={addCustomRequirement}
                className="inline-flex items-center gap-2 rounded-full bg-cyan-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-cyan-500"
              >
                <Plus size={14} />
                Add
              </button>
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Sparkles size={16} />}
              {loading ? "Finding card..." : "Get personalized suggestion"}
            </button>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <p className="text-xs text-slate-400">
              Selected: {selectedLabels.length ? `${selectedLabels.length} requirement(s)` : "none"}
            </p>
          </div>

          {selected.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {selected.map((item) => (
                <span
                  key={item}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
                >
                  {displayRequirement(item)}
                  <button
                    type="button"
                    onClick={() => removeRequirement(item)}
                    className="rounded-full p-0.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                    aria-label={`Remove ${displayRequirement(item)}`}
                  >
                    <X size={12} />
                  </button>
                </span>
              ))}
            </div>
          ) : null}

          {error ? (
            <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </div>
      ) : null}

      {result ? (
        <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-400">AI result</p>
              <h3 className="mt-1 text-base font-semibold text-slate-900">
                {result.decision || "Card suggestion"}
              </h3>
            </div>

            {matchedRequirements.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {matchedRequirements.slice(0, 3).map((item) => (
                  <span
                    key={item}
                    className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-700"
                  >
                    {REQUIREMENT_LABELS[item] || item.replaceAll("_", " ")}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          {result.summary ? <p className="mt-3 text-sm text-slate-600">{result.summary}</p> : null}

          {result.best_card ? (
            <div className="mt-4 rounded-2xl border border-cyan-200 bg-cyan-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-cyan-600">Best match</p>
                  <p className="mt-1 text-base font-semibold text-slate-900">
                    {result.best_card.card_name}
                  </p>
                  <p className="text-xs text-slate-500">{result.best_card.bank}</p>
                </div>

                <div className="text-right">
                  <p className="text-sm font-bold text-emerald-600">
                    +{formatMoney(result.best_card.net_annual_benefit)}/yr
                  </p>
                  <p className="text-xs text-slate-500">
                    Fee: {formatMoney(result.best_card.annual_fee)}
                  </p>
                </div>
              </div>

              {result.best_card.why ? (
                <p className="mt-3 text-sm text-cyan-900">{result.best_card.why}</p>
              ) : null}
            </div>
          ) : null}

          {rankedCards.length > 0 ? (
            <div className="mt-4 space-y-3">
              <p className="text-sm font-semibold text-slate-700">Top ranked cards</p>
              {rankedCards.slice(0, 3).map((card, index) => (
                <div
                  key={`${card.card_name}-${index}`}
                  className="rounded-2xl border border-slate-200 p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-slate-900">{card.card_name}</p>
                      <p className="text-xs text-slate-500">{card.bank}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-emerald-600">
                        +{formatMoney(card.net_annual_benefit)}/yr
                      </p>
                      <p className="text-xs text-slate-500">Score: {card.score ?? 0}</p>
                    </div>
                  </div>

                  {card.why ? <p className="mt-2 text-xs text-slate-500">{card.why}</p> : null}
                </div>
              ))}
            </div>
          ) : null}

          {warnings.length > 0 ? (
            <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <p className="text-sm font-semibold text-amber-800">Warnings</p>
              <ul className="mt-2 space-y-1 text-sm text-amber-800">
                {warnings.slice(0, 3).map((warning, index) => (
                  <li key={`${warning}-${index}`}>• {warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.next_step ? (
            <p className="mt-4 text-sm text-slate-600">
              <span className="font-semibold text-slate-800">Next step: </span>
              {result.next_step}
            </p>
          ) : null}

          <button
            type="button"
            onClick={() => {
              setResult(null);
              setOpen(true);
            }}
            className="mt-4 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            <RefreshCcw size={14} />
            Try another mix
          </button>
        </div>
      ) : null}
    </section>
  );
}
