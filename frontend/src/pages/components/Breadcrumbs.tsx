import { Link } from "react-router-dom";
import { Skill } from "../../api/useSkillsApi";

interface BreadcrumbsProps {
  parents: Skill[];
  current: Skill | null;
}

export function Breadcrumbs({ parents, current }: BreadcrumbsProps) {
  return (
    <nav aria-label="breadcrumb">
      <ol className="breadcrumb">

        {parents.map((p) => (
          <li key={p.id} className="breadcrumb-item">
            <Link to={`/skills/${p.id}`}>{p.description}</Link>
          </li>
        ))}

        {current && (
          <li className="breadcrumb-item active" aria-current="page">
            {current.description}
          </li>
        )}

      </ol>
    </nav>
  );
}
