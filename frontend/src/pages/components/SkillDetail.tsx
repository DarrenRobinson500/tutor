// src/pages/SkillDetailPage.tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSkillsApi, Skill } from "../../api/useSkillsApi";
import { useTemplateApi } from "../../api/useTemplateApi";
import type { TemplateSummary } from "../../types/TemplateMetadata";
import { Layout } from "./Layout";
import { Breadcrumbs } from "./Breadcrumbs";

interface SkillDetailProps {
  skillId: string;
}

export function SkillDetail({ skillId }: SkillDetailProps) {

  const { id } = useParams();
  const navigate = useNavigate();
  const { getSkill, getParents, listSkills, deleteSkill } = useSkillsApi();
  const [parents, setParents] = useState<Skill[]>([]);
  const [skill, setSkill] = useState<Skill | null>(null);
  const [children, setChildren] = useState<Skill[]>([]);

  const { generateTemplate } = useTemplateApi();

    useEffect(() => {
      getSkill(Number(skillId)).then(setSkill);
      listSkills(Number(skillId)).then(setChildren);
      getParents(Number(skillId)).then((p) => {
        console.log("PARENTS FROM API:", p);
        setParents(p);
      });
    }, [skillId]);


  async function handleDelete() {
    if (!window.confirm("Delete this skill?")) return;
    await deleteSkill(Number(skillId));
    navigate("/skills");
  }

//     function handleCreateTemplate() {
//       generateTemplate(Number(skillId))
//         .then((template) => {
//           console.log("Generated template:", template);
//           navigate(`/templates/${template.id}`);
//         })
//         .catch((err) => {
//           console.error("Template generation failed:", err);
//         });
//     }


  if (!skill) return <p>Loading…</p>;

  return (
  <Layout>

    <div className="container mt-4">
    <Breadcrumbs parents={parents} current={skill} />

      <h1 className="h4">{skill.code}</h1>
      <p>{skill.description}</p>

{/*       <button */}
{/*         className="btn btn-danger mb-3" */}
{/*         onClick={handleDelete} */}
{/*         disabled={children.length > 0} */}
{/*       > */}
{/*         Delete Skill */}
{/*       </button> */}

{/*       <button */}
{/*         className="btn btn-primary mb-3 ms-2" */}
{/*         onClick={() => navigate(`/skills/${skillId}/new`)} */}
{/*       > */}
{/*         Add Sub‑Skill */}
{/*       </button> */}

{/*         {skill.children_count === 0 && ( */}
{/*           <button className="btn btn-success" onClick={handleCreateTemplate}> */}
{/*             Create Template */}
{/*           </button> */}
{/*         )} */}

      <h2 className="h5 mt-4">Sub‑Skills</h2>

      <table className="table table-hover">
        <thead>
          <tr>
            <th>Code</th>
            <th>Description</th>
            <th>Children</th>
          </tr>
        </thead>
        <tbody>
          {children.map((child) => (
            <tr
              key={child.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/skills/${child.id}`)}
            >
              <td>{child.code}</td>
              <td>{child.description}</td>
              <td>{child.children_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
</Layout>

  );
}