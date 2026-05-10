export interface MultiStep {
  steps: Array<{
    svg: string;
    answer: string;
    solution: string;
    question?: string;
    tolerance?: number;
    format_instruction?: string;
    answer_format?: string;
    choices?: Array<{ text: string; correct: boolean }>;
    multiple_answers?: MultipleAnswerEntry[];
  }>;
}

export interface KnowledgeItem {
  id: number;
  title: string;
  text: string;
  text_2: string;
  diagram_svg: string;
}

export interface MultipleAnswerEntry {
  value: string;
  label?: string;
  width?: number;
}

export interface InlineKnowledge {
  title: string;
  text: string;
  text_2: string;
  diagram_svg: string;
  show: string; // "question" | "solution" | "both"
}

export interface PreviewResponse {
  question: string;
  answers: any[];
  params: Record<string, any>;
  solution: string;
  post_answer?: string;
  diagram_svg: string;
  diagram_code: string;
  substituted_yaml: string;
  errors?: string[];
  multi_step?: MultiStep | null;
  knowledge_items?: KnowledgeItem[];
  inline_knowledge?: InlineKnowledge[];
  multiple_answers?: MultipleAnswerEntry[] | null;
}

export interface StudentRecordResponse {
  next_question: PreviewResponse;
  mastery: number;
  competence_label: string;
  skill_name: string;
  template_id: number;
  correct?: boolean;
  loop_complete?: boolean;
  student_answer?: string;
}

