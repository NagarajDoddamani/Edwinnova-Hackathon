import { FcGoogle } from "react-icons/fc";
import { useGoogleAuth } from "../services/googleAuth";

export default function GoogleButton({ onSuccess }) {
  const googleLogin = useGoogleAuth(onSuccess);

  return (
    <button
      onClick={() => googleLogin()}
      className="w-full flex items-center justify-center gap-2 border py-3 rounded-xl hover:bg-gray-50"
    >
      <FcGoogle size={20} />
      Continue with Google
    </button>
  );
}