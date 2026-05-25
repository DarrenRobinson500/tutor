export function dashboardPath(): string {
  try {
    const user = JSON.parse(localStorage.getItem("user") ?? "{}");
    const { role, id } = user;
    if (role === "parent")      return `/parents/${id}`;
    if (role === "tutor")       return `/tutors/${id}`;
    if (role === "student")     return `/students/${id}`;
    if (role === "admin")       return "/admin";
    if (role === "distributor") return `/distributors/${id}`;
    if (role === "teacher")     return `/teachers/${id}`;
  } catch {}
  return "/";
}
