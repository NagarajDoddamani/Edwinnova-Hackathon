import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { Mail, Lock, User, TrendingUp } from "lucide-react";
import { FcGoogle } from "react-icons/fc";
import { api } from "../services/api";
import { useGoogleAuth } from "../services/googleAuth";
import { clearToken } from "../services/auth";

export default function Signup() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ✅ NORMAL SIGNUP
  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");

    const name = formData.name.trim();
    const email = formData.email.trim().toLowerCase();
    const password = formData.password;

    if (!name || !email || !password) {
      setError("Please fill in name, email, and password.");
      return;
    }

    try {
      setLoading(true);
      await api.post("/auth/register", { name, email, password });
      clearToken();
      navigate("/login", {
        replace: true,
        state: { message: "Account created successfully. Please sign in." },
      });

    } catch (err) {
      console.error(err);
      const detail = err?.response?.data?.detail || "Signup failed";

      if (String(detail).toLowerCase().includes("already exists")) {
        clearToken();
        navigate("/login", {
          replace: true,
          state: { message: "Account already exists. Please sign in." },
        });
        return;
      }

      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  // ✅ GOOGLE AUTOFILL
  const googleFill = useGoogleAuth({
    mode: "fill",
    setFormData,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 flex items-center justify-center p-4">

      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="size-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
            <TrendingUp className="text-white size-6" />
          </div>
          <span className="text-2xl font-bold">FinArmor</span>
        </div>

        {/* Card */}
        <div className="bg-white rounded-3xl shadow-xl p-8">

          <h2 className="text-2xl font-bold text-center mb-6">
            Create Account
          </h2>

          {error && (
            <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSignup} className="space-y-4">

            {/* Name */}
            <div className="relative">
              <User className="icon" />
              <input
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="Full Name"
                className="input"
                required
              />
            </div>

            {/* Email */}
            <div className="relative">
              <Mail className="icon" />
              <input
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                placeholder="Email"
                className="input"
                required
              />
            </div>

            {/* Password */}
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
              {loading ? "Creating..." : "Create Account"}
            </button>

          </form>

          {/* Divider */}
          <div className="divider">OR</div>

          {/* ✅ FIXED BUTTON */}
          <button type="button" onClick={() => googleFill()} className="googleBtn">
            <FcGoogle size={20} />
            Continue with Google
          </button>

          {/* Footer */}
          <p className="footer">
            Already have an account?{" "}
            <span onClick={() => navigate("/login")}>
              Login
            </span>
          </p>

        </div>
      </div>
    </div>
  );
}
