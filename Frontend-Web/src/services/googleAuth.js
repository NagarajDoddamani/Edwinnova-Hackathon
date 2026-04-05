import { useGoogleLogin } from "@react-oauth/google";
import axios from "axios";
import { api } from "./api";
import { setToken } from "./auth";

// ✅ MODE BASED GOOGLE AUTH
export const useGoogleAuth = ({ mode = "fill", setFormData, onLoginSuccess }) => {
  return useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const res = await axios.get(
          "https://www.googleapis.com/oauth2/v3/userinfo",
          {
            headers: {
              Authorization: `Bearer ${tokenResponse.access_token}`,
            },
          }
        );

        const user = {
          name: res.data.name,
          email: res.data.email,
        };

        // 🟢 MODE 1: ONLY FILL FORM (SIGNUP)
        if (mode === "fill" && setFormData) {
          setFormData((prev) => ({
            ...prev,
            name: user.name || "",
            email: user.email || "",
          }));
        }

        // 🔵 MODE 2: LOGIN WITH BACKEND (JWT)
        if (mode === "login") {
          const backendRes = await api.post("/auth/google", user);

          // ✅ SAVE JWT
          setToken(backendRes.data.access_token);

          // ✅ CALLBACK
          if (onLoginSuccess) onLoginSuccess();
        }

      } catch (err) {
        console.error("Google Auth Error:", err);
      }
    },

    onError: () => {
      console.log("Google Login Failed");
    },
  });
};