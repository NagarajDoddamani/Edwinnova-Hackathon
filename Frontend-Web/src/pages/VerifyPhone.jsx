import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function VerifyPhone() {
  const navigate = useNavigate();

  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [timer, setTimer] = useState(60);
  const [otpSent, setOtpSent] = useState(false);

  // timer
  useEffect(() => {
    if (!otpSent) return;

    const interval = setInterval(() => {
      setTimer((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(interval);
  }, [otpSent]);

  // send OTP
  const sendOtp = () => {
    if (phone.length < 10) return;

    setOtpSent(true);
    setTimer(60);

    // TODO: backend API
    console.log("Send OTP to:", phone);
  };

  // handle OTP input
  const handleChange = (value, index) => {
    if (!/^[0-9]?$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      document.getElementById(`phone-otp-${index + 1}`).focus();
    }
  };

  // verify
  const handleVerify = () => {
    const code = otp.join("");

    // TODO: backend verify
    console.log("Phone:", phone, "OTP:", code);

    navigate("/complete-profile");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="bg-slate-800 p-8 rounded-xl w-[380px] shadow-lg text-center">

        <h2 className="text-2xl font-bold text-white mb-4">
          Verify Phone
        </h2>

        {!otpSent ? (
          <>
            <input
              type="tel"
              placeholder="Enter phone number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full p-3 rounded-lg bg-slate-900 border border-slate-600 text-white mb-4 outline-none focus:border-green-500"
            />

            <button
              onClick={sendOtp}
              className="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded-lg font-semibold"
            >
              Send OTP
            </button>
          </>
        ) : (
          <>
            {/* OTP */}
            <div className="flex justify-center gap-2 mb-5">
              {otp.map((digit, index) => (
                <input
                  key={index}
                  id={`phone-otp-${index}`}
                  type="text"
                  maxLength="1"
                  value={digit}
                  onChange={(e) => handleChange(e.target.value, index)}
                  className="w-12 h-12 text-center text-white text-lg rounded-lg bg-slate-900 border border-slate-600 focus:border-green-500 outline-none"
                />
              ))}
            </div>

            <button
              onClick={handleVerify}
              className="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded-lg font-semibold"
            >
              Verify Phone
            </button>

            {/* resend */}
            <div className="mt-4 text-sm text-slate-400">
              {timer > 0 ? (
                <span>Resend in {timer}s</span>
              ) : (
                <span
                  onClick={sendOtp}
                  className="text-green-500 cursor-pointer"
                >
                  Resend OTP
                </span>
              )}
            </div>
          </>
        )}

      </div>
    </div>
  );
}