import { useNavigate } from "react-router-dom";
import { ArrowRight, TrendingUp, Shield, BookOpen, Sparkles } from "lucide-react";

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="container mx-auto px-4 py-6 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="size-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <TrendingUp className="size-6 text-white" />
          </div>
          <span className="text-xl font-semibold">FinanceGuide</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/login")}
            className="px-5 py-2 rounded-full border border-gray-300 text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Login
          </button>
          <button
            onClick={() => navigate("/signup")}
            className="px-5 py-2 rounded-full bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            Sign Up
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 text-blue-700 mb-6">
            <Sparkles className="size-4" />
            <span className="text-sm font-medium">AI-Powered Financial Guidance</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Your Personal Finance Companion
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Get instant answers to your financial questions, track your progress, and make smarter money decisions with AI-powered insights.
          </p>
          <button
            onClick={() => navigate("/signup")}
            className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full font-medium text-lg hover:shadow-lg transition-all flex items-center gap-2 mx-auto"
          >
            Get Started Free
            <ArrowRight className="size-5" />
          </button>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          <div className="bg-white rounded-2xl p-8 shadow-sm hover:shadow-md transition-shadow">
            <div className="size-12 rounded-xl bg-blue-100 flex items-center justify-center mb-4">
              <Sparkles className="size-6 text-blue-600" />
            </div>
            <h3 className="text-xl font-semibold mb-3">AI-Powered Answers</h3>
            <p className="text-gray-600">
              Ask any finance question and get instant, personalized answers powered by advanced AI technology.
            </p>
          </div>

          <div className="bg-white rounded-2xl p-8 shadow-sm hover:shadow-md transition-shadow">
            <div className="size-12 rounded-xl bg-purple-100 flex items-center justify-center mb-4">
              <Shield className="size-6 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Secure & Private</h3>
            <p className="text-gray-600">
              Your financial data is encrypted and secure. We never share your personal information.
            </p>
          </div>

          <div className="bg-white rounded-2xl p-8 shadow-sm hover:shadow-md transition-shadow">
            <div className="size-12 rounded-xl bg-green-100 flex items-center justify-center mb-4">
              <BookOpen className="size-6 text-green-600" />
            </div>
            <h3 className="text-xl font-semibold mb-3">Learn & Grow</h3>
            <p className="text-gray-600">
              Build your financial literacy with personalized guidance tailored to your goals and situation.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-20">
        <div className="max-w-4xl mx-auto bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-12 text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Take Control of Your Finances?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join thousands of users making smarter financial decisions every day.
          </p>
          <button
            onClick={() => navigate("/signup")}
            className="px-8 py-4 bg-white text-blue-600 rounded-full font-medium text-lg hover:shadow-xl transition-all"
          >
            Start Your Journey
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-8 mt-20">
        <div className="container mx-auto px-4 text-center text-gray-600">
          <p>&copy; 2026 FinanceGuide. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}