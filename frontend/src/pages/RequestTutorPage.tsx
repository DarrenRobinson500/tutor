import { useLocation, useNavigate, useParams } from "react-router-dom";
import RequestTutorFlow from "../components/RequestTutorFlow";
import type { TutorSelection } from "../components/RequestTutorFlow";

interface LocationState {
  childFirstName?: string;
  yearGroup?: number;
  parentHasDistributor?: boolean;
}

export default function RequestTutorPage() {
  const { id: parentId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const state = (useLocation().state as LocationState) ?? {};

  function handleConfirm(_selection: TutorSelection) {
    // Handoff point for Build 2 — payment setup flow
    navigate(`/parents/${parentId}`);
  }

  function handleCancel() {
    navigate(`/parents/${parentId}`);
  }

  return (
    <RequestTutorFlow
      childName={state.childFirstName}
      yearGroup={state.yearGroup}
      parentHasDistributor={state.parentHasDistributor ?? false}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  );
}
