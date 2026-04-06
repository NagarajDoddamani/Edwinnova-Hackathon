import { Bot, User } from "lucide-react";

export default function MessageBubble({
  role = "assistant",
  label = "FinArmor AI",
  className = "",
  children,
}) {
  const isUser = role === "user";
  const widthClass = isUser
    ? "max-w-[88%] sm:max-w-[82%] lg:max-w-[78%]"
    : "max-w-full";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} chat-fade-in`}>
      <article
        className={`w-full ${widthClass} rounded-[28px] border p-4 shadow-sm transition sm:p-5 ${
          isUser
            ? "border-slate-900 bg-slate-900 text-white shadow-slate-950/20 dark:border-white/10 dark:bg-white dark:text-slate-950"
            : "border-slate-200 bg-white text-slate-900 shadow-slate-200/60 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100 dark:shadow-black/20"
        } ${className}`}
      >
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.32em] text-slate-500 dark:text-slate-400">
          <span
            className={`inline-flex size-7 items-center justify-center rounded-full ${
              isUser
                ? "bg-white/10 text-white dark:bg-slate-950 dark:text-white"
                : "bg-slate-950 text-white dark:bg-white dark:text-slate-950"
            }`}
          >
            {isUser ? <User size={13} /> : <Bot size={13} />}
          </span>
          <span>{isUser ? "You" : label}</span>
        </div>

        <div className="mt-3">{children}</div>
      </article>
    </div>
  );
}
