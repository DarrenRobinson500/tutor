export interface TemplateSummary {
  id: number;
  grade: string;
  skill: string;
  skill_detail: string;
  difficulty: string;
  subject: string;
  status: string;
  updated_at: string;
  note_count: number;
  notes: string[];
  question_text: string;
}


export type TemplateMetadata = {
  id: number | null;
  name: string;
  description: string;
  subject: string;          // skill_detail description — used for the subjects dropdown
  skill_detail_id: number | null;  // FK to Skill Detail node — used when saving
  topic: string;
  subtopic: string;
  difficulty: string;
  grade: string | null;
  tags: string[];
  curriculum: any[];
  status: string;
  version: number;
  skill: number | null;     // parent Skill-level node ID — used for filtering only
  validated: boolean;
  validated_filter?: "all" | "validated" | "unvalidated";
  language_filter?: string;
  group?: number | null;

}

export const emptyMetadata: TemplateMetadata = {
  id: null,
  name: "",
  description: "",
  subject: "",
  skill_detail_id: null,
  topic: "",
  subtopic: "",
  difficulty: "",
  grade: "",
  tags: [],
  curriculum: [],
  status: "draft",
  version: 1,
  skill: null,
  validated: false,
  group: null,

};

