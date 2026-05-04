import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../utils/apiFetch";

export default function LoginForm() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");

    const res = await fetch(`${API_URL}/api/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

//     const res = await apiFetch("/api/auth/login/", {
//       method: "POST",
//       body: JSON.stringify({ email, password }),
//     });

    const data = await res.json();

    if (!res.ok) {
      setError(data.error || "Login failed");
      return;
    }

    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    localStorage.setItem("user", JSON.stringify(data.user));

    const role = data.user.role;
    if (role === "tutor") navigate(`/tutors/${data.user.id}`);
    else if (role === "student") navigate(`/students/${data.user.id}`);
    else if (role === "parent") navigate(`/parents/${data.user.id}`);
    else if (role === "admin") navigate("/admin/tutors");
  }

  return (
    <form onSubmit={handleLogin} className="auth-form">
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

      {error && <div className="auth-error">{error}</div>}

      <button type="submit">Login</button>
    </form>
  );
}