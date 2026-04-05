import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Mail, Lock, TrendingUp } from "lucide-react";
import { FcGoogle } from "react-icons/fc";
import { useGoogleAuth } from "../services/googleAuth";
import { api } from "../services/api";
import { setToken } from "../services/auth";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ✅ NORMAL LOGIN
  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    const email = formData.email.trim().toLowerCase();
    const password = formData.password;

    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }

    try {
      setLoading(true);
      const res = await api.post("/auth/login", { email, password });

      // ✅ STORE JWT
      setToken(res.data.access_token);

      navigate("/dashboard", { replace: true });

    } catch (err) {
      console.error(err);
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  // ✅ GOOGLE LOGIN
  const googleLogin = useGoogleAuth({
    mode: "login",
    onLoginSuccess: () => navigate("/dashboard"),
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">

      <div className="w-full max-w-md">

        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="size-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <TrendingUp className="text-white size-6" />
          </div>
          <span className="text-2xl font-bold">FinArmor</span>
        </div>

        <div className="bg-white rounded-3xl shadow-xl p-8">

          <h2 className="text-2xl font-bold text-center mb-6">
            Welcome Back
          </h2>

          {(location.state?.message || error) && (
            <div
              className={`mb-4 rounded-xl px-4 py-3 text-sm ${
                error
                  ? "bg-red-50 text-red-700 border border-red-200"
                  : "bg-green-50 text-green-700 border border-green-200"
              }`}
            >
              {error || location.state?.message}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">

            <div className="relative">
              <Mail className="icon" />
              <input
                type="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                placeholder="Email"
                className="input"
                required
              />
            </div>

            <div className="relative">
              <Lock className="icon" />
              <input
                type="password"
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
                placeholder="Password"
                className="input"
                required
              />
            </div>

            <button type="submit" className="btn" disabled={loading}>
              {loading ? "Signing In..." : "Sign In"}
            </button>

          </form>

          <div className="divider">OR</div>

          <button type="button" onClick={() => googleLogin()} className="googleBtn">
            <FcGoogle size={20} />
            Continue with Google
          </button>

          <p className="footer">
            Don’t have an account?{" "}
            <span onClick={() => navigate("/signup")}>
              Sign Up
            </span>
          </p>

        </div>
      </div>
    </div>
  );
}
