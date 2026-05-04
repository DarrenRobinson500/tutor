import { useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch"
// import { useNavigate } from "react-router-dom";

export function TutorCreatePage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [result, setResult] = useState<any>(null);
//   const navigate = useNavigate();


  async function handleSubmit(e: any) {
    e.preventDefault();

    const res = await apiFetch("/api/tutors/create_tutor/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();
    setResult(data);
  }

//   {result && (
//   <div className="alert alert-success mt-4">
//     <h5>Student Created</h5>
//     <p><strong>Name:</strong> {result.name}</p>
//     <p><strong>Email:</strong> {result.email}</p>
//     {result.password && (
//       <p><strong>Password:</strong> {result.password}</p>
//     )}

// <button
//   className="btn btn-primary mt-3"
//   onClick={() => navigate("/admin/tutors")}
// >
//   Return to Tutor List
// </button>
//
//   </div>
//   )}


  return (
  <Layout>
    <div className="container mt-4">
      <h2>Create New Tutor</h2>

      <form onSubmit={handleSubmit} className="mt-3">

        <div className="mb-3">
          <label className="form-label">Tutor Name</label>
          <input className="form-control"
                 value={name}
                 onChange={e => setName(e.target.value)} />
        </div>

        <div className="mb-3">
          <label className="form-label">Email (username)</label>
          <input className="form-control"
                 value={email}
                 onChange={e => setEmail(e.target.value)} />
        </div>

        <div className="mb-3">
          <label className="form-label">Password (optional)</label>
          <input className="form-control"
                 value={password}
                 onChange={e => setPassword(e.target.value)}
                 placeholder="Leave blank for auto-generated" />
        </div>

        <button className="btn btn-primary">Create Tutor</button>
      </form>

      {result && (
        <div className="alert alert-success mt-4">
          <h5>Tutor Created</h5>
          <p><strong>Name:</strong> {result.name}</p>
          <p><strong>Email:</strong> {result.email}</p>
          {result.password && (
            <p><strong>Password:</strong> {result.password}</p>
          )}
        </div>
      )}
    </div>
</Layout>
    );
}