import { FcGoogle } from "react-icons/fc";
import { useGoogleAuth } from "../services/googleAuth";

export default function GoogleButton({ onSuccess }) {
  const googleLogin = useGoogleAuth(onSuccess);

  return (
    <button
      onClick={() => googleLogin()}
      className="w-full flex items-center justify-center gap-2 border border-gray-200 bg-white py-3 rounded-xl text-slate-700 hover:bg-gray-50"
    >
      <FcGoogle size={20} />
      Continue with Google
    </button>
  );
}
