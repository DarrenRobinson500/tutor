import { useParams } from "react-router-dom";
import LandingPage from "./LandingPage";

export default function ReferralLandingPage() {
  const { code } = useParams<{ code: string }>();
  return <LandingPage refCode={code} />;
}
