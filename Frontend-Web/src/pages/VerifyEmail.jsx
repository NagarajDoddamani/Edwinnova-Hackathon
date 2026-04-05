import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function VerifyEmail() {
  const navigate = useNavigate();

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [timer, setTimer] = useState(60);

  // countdown timer
  useEffect(() => {
    const interval = setInterval(() => {
      setTimer((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleChange = (value, index) => {
    if (!/^[0-9]?$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // move to next input
    if (value && index < 5) {
      document.getElementById(`otp-${index + 1}`).focus();
    }
  };

  const handleVerify = () => {
    const code = otp.join("");

    // TODO: backend verify
    console.log("OTP:", code);

    navigate("/verify-phone");
  };

  const handleResend = () => {
    setTimer(60);
    // TODO: resend API
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="bg-slate-800 p-8 rounded-xl w-[380px] shadow-lg text-center">

        <h2 className="text-2xl font-bold text-white mb-2">
          Verify Email
        </h2>

        <p className="text-slate-400 mb-6 text-sm">
          Enter the 6-digit code sent to your email
        </p>

        {/* OTP Inputs */}
        <div className="flex justify-center gap-2 mb-6">
          {otp.map((digit, index) => (
            <input
              key={index}
              id={`otp-${index}`}
              type="text"
              maxLength="1"
              value={digit}
              onChange={(e) => handleChange(e.target.value, index)}
              className="w-12 h-12 text-center text-white text-lg rounded-lg bg-slate-900 border border-slate-600 focus:border-green-500 outline-none"
            />
          ))}
        </div>

        {/* Verify Button */}
        <button
          onClick={handleVerify}
          className="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded-lg font-semibold transition"
        >
          Verify Email
        </button>

        {/* Resend */}
        <div className="mt-5 text-sm text-slate-400">
          {timer > 0 ? (
            <span>Resend in {timer}s</span>
          ) : (
            <span
              onClick={handleResend}
              className="text-green-500 cursor-pointer"
            >
              Resend Code
            </span>
          )}
        </div>

      </div>
    </div>
  );
}