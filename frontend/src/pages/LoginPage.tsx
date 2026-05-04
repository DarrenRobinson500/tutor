// import { Layout } from "./components/Layout";
import React, { useState, useEffect } from "react";
import { apiFetch } from "../utils/apiFetch"

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

useEffect(() => {
  const token = localStorage.getItem("access");
  if (!token) return;

  // Validate token with backend
  apiFetch("/api/auth/me/", {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => {
      if (res.ok) {
        // Token is valid → redirect
        return res.json().then((user) => {
        window.location.href = "/templates";

//           if (user.role === "tutor") window.location.href = `/tutor/${user.id}/`;
//           else if (user.role === "student") window.location.href = `/student/${user.id}/`;
//           else if (user.role === "parent") window.location.href = `/parent/${user.id}/`;
//           else if (user.role === "admin") window.location.href = `/admin`;
//           else window.location.href = "/";
        });
      }

      // Token invalid → clear it
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user");
    })
    .catch(() => {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user");
    });
}, []);

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");

    // 1. Call JWT login endpoint
    const res = await apiFetch("/api/auth/login/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      setError("Invalid username or password");
      return;
    }

    const tokens = await res.json(); // { access, refresh }

    // 2. Store tokens
    localStorage.setItem("access", tokens.access);
    localStorage.setItem("refresh", tokens.refresh);

    // 3. Fetch current user info using the access token
    const meRes = await apiFetch("/api/auth/me/", {
      headers: {
        "Authorization": `Bearer ${tokens.access}`,
      },
    });

    if (!meRes.ok) {
      setError("Login succeeded but failed to load user profile");
      return;
    }

    const user = await meRes.json(); // { id, role, ... }

    // 4. Store user info if you like
    localStorage.setItem("user", JSON.stringify(user));

    // 5. Redirect based on role
    if (user.role === "tutor") window.location.href = `/tutor/${user.id}/`;
    else if (user.role === "student") window.location.href = `/student/${user.id}/`;
    else if (user.role === "parent") window.location.href = `/parent/${user.id}/`;
    else if (user.role === "admin") window.location.href = `/admin`;
    else window.location.href = "/";
  };

  return (
      <div className="container mt-4" style={{ maxWidth: 400 }}>
        <h1>Login</h1>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={submit}>
          <div className="mb-3">
            <label>Username</label>
            <input
              className="form-control"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="mb-3">
            <label>Password</label>
            <input
              className="form-control"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button className="btn btn-primary">Login</button>
        </form>
      </div>
  );
}
