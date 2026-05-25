import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import RequestTutorFlow from "../components/RequestTutorFlow";
import type { Tutor, TutorSelection } from "../components/RequestTutorFlow";
import { apiFetch } from "../utils/apiFetch";

interface LocationState {
  childId?: number;
  childFirstName?: string;
  yearGroup?: number;
  parentHasDistributor?: boolean;
}

export default function RequestTutorPage() {
  const { id: parentId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const state = (useLocation().state as LocationState) ?? {};

  const [tutors, setTutors] = useState<Tutor[] | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [requestingMobile, setRequestingMobile] = useState(false);

  useEffect(() => {
    apiFetch("/api/tutors/available/")
      .then(r => r.json())
      .then(setTutors)
      .catch(() => setTutors([]));
  }, []);

  async function handleConfirm(selection: TutorSelection) {
    setConfirming(true);
    try {
      const body: Record<string, unknown> = {
        child_id: state.childId,
        tutor_id: selection.tutor.id,
      };
      if (selection.slot) {
        body.weekday   = selection.slot.weekday;
        body.start_time = selection.slot.startTime;
        body.end_time   = selection.slot.endTime;
      }
      const res = await apiFetch("/api/auth/select_tutor/", {
        method: "POST",
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        alert(d.error || "Could not save tutor selection. Please try again.");
        return;
      }
    } catch {
      alert("Something went wrong. Please try again.");
      return;
    } finally {
      setConfirming(false);
    }
    navigate(`/parents/${parentId}`);
  }

  async function handleRequestMobile(tutorId: string) {
    setRequestingMobile(true);
    try {
      const res = await apiFetch("/api/auth/request_tutor_mobile/", {
        method: "POST",
        body: JSON.stringify({ tutor_id: tutorId, child_id: state.childId }),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) {
        alert(d.error || "Could not send the request. Please try again.");
      } else {
        alert("Done — we've sent the tutor's number to your email.");
      }
    } catch {
      alert("Something went wrong. Please try again.");
    } finally {
      setRequestingMobile(false);
    }
  }

  function handleCancel() {
    navigate(`/parents/${parentId}`);
  }

  if (tutors === null) return <div className="container mt-4">Loading…</div>;

  return (
    <RequestTutorFlow
      childName={state.childFirstName}
      yearGroup={state.yearGroup}
      parentHasDistributor={state.parentHasDistributor ?? false}
      tutors={tutors}
      confirming={confirming}
      requestingMobile={requestingMobile}
      onConfirm={handleConfirm}
      onRequestMobile={handleRequestMobile}
      onCancel={handleCancel}
    />
  );
}
