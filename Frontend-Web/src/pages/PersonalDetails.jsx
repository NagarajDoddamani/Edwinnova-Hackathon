import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";

export default function PersonalDetails() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    age: "",
    employment_type: "",
    location: "",
  });

  const [loading, setLoading] = useState(true);

  // 🔒 LOAD USER DATA
  useEffect(() => {
    const loadUser = async () => {
      try {
        const res = await api.get("/user/me");

        setFormData({
          name: res.data.name || "",
          email: res.data.email || "",
          age: res.data.age || "",
          employment_type: res.data.employment_type || "",
          location: res.data.location || "",
        });

      } catch (err) {
        console.error(err);
        navigate("/login");
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  // ✅ UPDATE USER
  const handleUpdate = async (e) => {
    e.preventDefault();

    try {
      await api.put("/user/update", formData);
      alert("Profile updated");
      navigate("/dashboard");

    } catch (err) {
      console.error(err);
      alert("Update failed");
    }
  };

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">

      <div className="bg-white p-8 rounded-2xl shadow w-[400px]">

        <h2 className="text-xl font-bold mb-6">Personal Details</h2>

        <form onSubmit={handleUpdate} className="space-y-4">

          <input
            value={formData.name}
            onChange={(e) =>
              setFormData({ ...formData, name: e.target.value })
            }
            placeholder="Name"
            className="input"
          />

          <input
            value={formData.email}
            disabled
            className="input bg-gray-100"
          />

          <input
            value={formData.age}
            onChange={(e) =>
              setFormData({ ...formData, age: e.target.value })
            }
            placeholder="Age"
            className="input"
          />

          <select
            value={formData.employment_type}
            onChange={(e) =>
              setFormData({
                ...formData,
                employment_type: e.target.value,
              })
            }
            className="input"
          >
            <option value="">Employment Type</option>
            <option value="student">Student</option>
            <option value="salaried">Salaried</option>
            <option value="self-employed">Self Employed</option>
          </select>

          <input
            value={formData.location}
            onChange={(e) =>
              setFormData({ ...formData, location: e.target.value })
            }
            placeholder="Location"
            className="input"
          />

          <button className="btn">
            Save Changes
          </button>

        </form>

      </div>
    </div>
  );
}