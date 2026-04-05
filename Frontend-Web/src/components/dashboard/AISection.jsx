import { Sparkles } from "lucide-react";

export default function AISection({ onAsk }) {
  return (
    <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white mb-8">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles />
        <h2 className="text-xl font-bold">AI Assistant</h2>
      </div>

      <button
        onClick={onAsk}
        className="mt-3 bg-white text-blue-600 px-4 py-2 rounded-xl"
      >
        Ask a Question
      </button>
    </div>
  );
}