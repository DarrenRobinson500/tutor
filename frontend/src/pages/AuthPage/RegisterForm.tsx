import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../utils/apiFetch";


export default function RegisterForm() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("tutor");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

//     const res = await apiFetch("/api/auth/register/", {
//       method: "POST",
//       body: JSON.stringify({ email, password, role }),
//     });
    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");

    const res = await fetch(`${API_URL}/api/auth/register/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, role }),
    });


    const data = await res.json();

    if (!res.ok) {
      setError(data.error || "Registration failed");
      return;
    }

    // Show success message
    setSuccess("Registration successful! Redirecting...");

    // Redirect based on role
    if (data.role === "tutor") navigate(`/tutor/${data.id}`);
    if (data.role === "parent") navigate(`/parent/${data.id}`);
    if (data.role === "student") navigate(`/student/${data.id}`);
  }

  return (
    <form onSubmit={handleRegister} className="auth-form">
      <input
        type="text"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      <div className="role-select">
        <label>
          <input
            type="radio"
            name="role"
            value="tutor"
            checked={role === "tutor"}
            onChange={() => setRole("tutor")}
          />
          Tutor
        </label>

        <label>
          <input
            type="radio"
            name="role"
            value="parent"
            checked={role === "parent"}
            onChange={() => setRole("parent")}
          />
          Parent
        </label>

        <label>
          <input
            type="radio"
            name="role"
            value="student"
            checked={role === "student"}
            onChange={() => setRole("student")}
          />
          Student
        </label>
      </div>

      {error && <div className="auth-error">{error}</div>}
      {success && <div className="auth-success">{success}</div>}

      <button type="submit">Register</button>
    </form>
  );
}