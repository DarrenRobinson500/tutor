import "./App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

import { TemplateListPage } from "./pages/TemplateListPage";
import { TemplateEditorPage } from "./pages/TemplateEditorPage";
import { TemplateGroupEditorPage } from "./pages/TemplateGroupEditorPage";
import { NewTemplatePage } from "./pages/NewTemplatePage";
import { SkillCreatePage } from "./pages/SkillCreatePage";
import { TutorListPage } from "./pages/TutorListPage";
import { TutorHomePage } from "./pages/TutorHomePage";
import TutorSetFeePage from "./pages/TutorSetFeePage";
import { TutorEditPage } from "./pages/TutorEditPage";
import { TutorCreatePage } from "./pages/TutorCreatePage";
import { TutorSchedulePage } from "./pages/TutorSchedulePage";
import { TutorBookingPage } from "./pages/TutorBookingPage";
import { TutorSMSInboxPage } from "./pages/TutorSMSInboxPage";
import { TutorSMSConversationPage } from "./pages/TutorSMSConversationPage";
import { AdminSMSInboxPage } from "./pages/AdminSMSInboxPage";
import { AdminSMSConversationPage } from "./pages/AdminSMSConversationPage";
import { AdminEmailPage } from "./pages/AdminEmailPage";

import { StudentListPage } from "./pages/StudentListPage";
import { StudentEditPage } from "./pages/StudentEditPage";
import { StudentQuestionPage } from "./pages/StudentQuestionPage";
import { StudentHomePage } from "./pages/StudentHomePage";
import { TestPage } from "./pages/TestPage";
import { StudentBookingPage } from "./pages/StudentBookingPage";
import { StudentCreatePage } from "./pages/StudentCreatePage";
import { StudentFocusPage } from "./pages/StudentFocusPage";
import SkillsPage from "./pages/SkillsPage";
import SkillsS6Page from "./pages/SkillsS6Page";
import { SkillOverviewPage } from "./pages/SkillOverviewPage";
import { SkillParentOverviewPage } from "./pages/SkillParentOverviewPage";
import { SkillDetailEditPage } from "./pages/SkillDetailEditPage";
import { TemplateMetadataPage } from "./pages/TemplateMetadataPage";
import PrinciplesPage from "./pages/PrinciplesPage";
import FeedbackPage from "./pages/FeedbackPage";
import { DocsPage } from "./pages/DocsPage";
import { KnowledgeEditorPage } from "./pages/KnowledgeEditorPage";
import { KnowledgeListPage } from "./pages/KnowledgeListPage";
import { PastTestsPage } from "./pages/PastTestsPage";
import AuthPage from "./pages/AuthPage/AuthPage";
import LandingPage from "./pages/public/LandingPage";
import DistributorPage from "./pages/public/DistributorPage";
import TutorPage from "./pages/public/TutorPage";
import CompetitionPage from "./pages/public/CompetitionPage";
import DistributorRegisterPage from "./pages/public/DistributorRegisterPage";
import ReferralLandingPage from "./pages/public/ReferralLandingPage";
import TeachersLandingPage from "./pages/public/TeachersLandingPage";
import TeacherRegisterPage from "./pages/public/TeacherRegisterPage";
import { TeacherHomePage } from "./pages/TeacherHomePage";
import { TeacherClassPage } from "./pages/TeacherClassPage";
import { TeacherGapReportPage } from "./pages/TeacherGapReportPage";
import { TeacherClassFocusPage } from "./pages/TeacherClassFocusPage";
import { TeacherAssessmentPage } from "./pages/TeacherAssessmentPage";
import { TeacherAssessmentSetupPage } from "./pages/TeacherAssessmentSetupPage";
import { AssessmentQuestionPage } from "./pages/AssessmentQuestionPage";
import DistributorHomePage from "./pages/DistributorHomePage";
import AdminHomePage from "./pages/AdminHomePage";
import LoginPage from "./pages/public/LoginPage";
import ParentRegisterPage from "./pages/public/ParentRegisterPage";
import TutorRegisterPage from "./pages/public/TutorRegisterPage";
import AssessmentLaunchPage from "./pages/public/AssessmentLaunchPage";
import ParentHomePage from "./pages/ParentHomePage";
import RequestTutorPage from "./pages/RequestTutorPage";
import { TutoringRoomPage } from "./pages/TutoringRoomPage";
import { PostTuitionPage } from "./pages/PostTuitionPage";
import { PostTuitionListPage } from "./pages/PostTuitionListPage";
import { TutorPaymentsPage } from "./pages/TutorPaymentsPage";
import { ParentPaymentsPage } from "./pages/ParentPaymentsPage";
import { ParentBookingsPage } from "./pages/ParentBookingsPage";
import ParentPrinciplesPage from "./pages/ParentPrinciplesPage";
import { AdminPaymentsPage } from "./pages/AdminPaymentsPage";
import { PaymentAuthorisePage } from "./pages/PaymentAuthorisePage";
import { PaymentReceiptPage } from "./pages/PaymentReceiptPage";
import { PaymentRetryPage } from "./pages/PaymentRetryPage";
import { TutorBillingPage } from "./pages/TutorBillingPage";
import { TELanguagesPage } from "./pages/TELanguagesPage";
import { VariablesPage } from "./pages/VariablesPage";
import { apiFetch } from "./utils/apiFetch";
import { usePreferenceStore } from "./utils/pref";

import "bootstrap/dist/css/bootstrap.min.css";

// ------------------------------------------------------------
// HTML FILE REDIRECT (outside React Router SPA routing)
// ------------------------------------------------------------
function HtmlRedirect({ to }: { to: string }) {
  window.location.replace(to);
  return null;
}

// ------------------------------------------------------------
// PROTECTED ROUTE WRAPPER
// ------------------------------------------------------------
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const access = localStorage.getItem("access");
  const storedUser = localStorage.getItem("user");

  if (!access || !storedUser) return <Navigate to="/login" replace />;

  return <>{children}</>;
}


// ------------------------------------------------------------
// MAIN APP
// ------------------------------------------------------------
function App() {
  useEffect(() => {
    window.addEventListener("error", (e) => {
      console.log("GLOBAL ERROR:", e.error);
    });
  }, []);

  useEffect(() => {
    async function loadPrefs() {
      const res = await apiFetch("/api/preferences/flat/");
      const data = await res.json();
      usePreferenceStore.getState().load(data);
    }
    loadPrefs();
  }, []);


  return (
    <BrowserRouter>
      <Routes>

        {/* PUBLIC — marketing & auth */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register/parent" element={<ParentRegisterPage />} />
        <Route path="/register/tutor" element={<TutorRegisterPage />} />
        <Route path="/distributors" element={<DistributorPage />} />
        <Route path="/tutors" element={<TutorPage />} />
        <Route path="/teachers" element={<TeachersLandingPage />} />
        <Route path="/register/teacher" element={<TeacherRegisterPage />} />

        {/* PROTECTED — teacher */}
        <Route path="/teachers/:id" element={<ProtectedRoute><TeacherHomePage /></ProtectedRoute>} />
        <Route path="/teachers/:teacherId/classes/:classId" element={<ProtectedRoute><TeacherClassPage /></ProtectedRoute>} />
        <Route path="/teachers/:teacherId/classes/:classId/gap-report" element={<ProtectedRoute><TeacherGapReportPage /></ProtectedRoute>} />
        <Route path="/teachers/:teacherId/classes/:classId/focus" element={<ProtectedRoute><TeacherClassFocusPage /></ProtectedRoute>} />
        <Route path="/teachers/:teacherId/classes/:classId/assessment-setup" element={<ProtectedRoute><TeacherAssessmentSetupPage /></ProtectedRoute>} />
        <Route path="/teachers/:teacherId/classes/:classId/assessment/:assessmentId" element={<ProtectedRoute><TeacherAssessmentPage /></ProtectedRoute>} />
        <Route path="/competitions" element={<CompetitionPage />} />
        {/* Short aliases */}
        <Route path="/dist" element={<Navigate to="/distributors" replace />} />
        <Route path="/tut" element={<Navigate to="/tutors" replace />} />
        <Route path="/comp" element={<HtmlRedirect to="/market-makers.html" />} />
        <Route path="/admin" element={<ProtectedRoute><AdminHomePage /></ProtectedRoute>} />
        <Route path="/register/distributor" element={<DistributorRegisterPage />} />
        <Route path="/ref/:code" element={<ReferralLandingPage />} />
        <Route path="/assessment-launch" element={<AssessmentLaunchPage />} />
        <Route path="/auth" element={<AuthPage />} />

        {/* PROTECTED — distributor */}
        <Route path="/distributors/:id" element={<ProtectedRoute><DistributorHomePage /></ProtectedRoute>} />

        {/* PROTECTED — parent */}
        <Route path="/parents/:id" element={<ProtectedRoute><ParentHomePage /></ProtectedRoute>} />
        <Route path="/parents/:id/payments" element={<ProtectedRoute><ParentPaymentsPage /></ProtectedRoute>} />
        <Route path="/parents/:id/bookings" element={<ProtectedRoute><ParentBookingsPage /></ProtectedRoute>} />
        <Route path="/parents/:id/find-tutor" element={<ProtectedRoute><RequestTutorPage /></ProtectedRoute>} />
        <Route path="/parents/:id/principles" element={<ProtectedRoute><ParentPrinciplesPage /></ProtectedRoute>} />

        {/* PROTECTED — payment flow */}
        <Route path="/payments/:id/authorise" element={<ProtectedRoute><PaymentAuthorisePage /></ProtectedRoute>} />
        <Route path="/payments/:id/receipt" element={<ProtectedRoute><PaymentReceiptPage /></ProtectedRoute>} />
        <Route path="/payments/:id/retry" element={<ProtectedRoute><PaymentRetryPage /></ProtectedRoute>} />

        {/* PROTECTED — other */}
        <Route path="/templates" element={<ProtectedRoute><TemplateListPage /></ProtectedRoute>} />
        <Route path="/templates/new" element={<ProtectedRoute><NewTemplatePage /></ProtectedRoute>} />
        <Route path="/templates/editor" element={<ProtectedRoute><TemplateEditorPage /></ProtectedRoute>} />
        <Route path="/templates/group/:groupId" element={<ProtectedRoute><TemplateGroupEditorPage /></ProtectedRoute>} />
        <Route path="/templates/:id" element={<ProtectedRoute><TemplateEditorPage /></ProtectedRoute>} />
        <Route path="/templates/:id/metadata" element={<ProtectedRoute><TemplateMetadataPage /></ProtectedRoute>} />
        <Route path="/templates/:id/languages" element={<ProtectedRoute><TELanguagesPage /></ProtectedRoute>} />

        <Route path="/skills" element={<ProtectedRoute><SkillsPage /></ProtectedRoute>} />
        <Route path="/skills-s6" element={<ProtectedRoute><SkillsS6Page /></ProtectedRoute>} />
        <Route path="/skills/new" element={<ProtectedRoute><SkillCreatePage /></ProtectedRoute>} />
        <Route path="/skills/:id" element={<ProtectedRoute><SkillsPage /></ProtectedRoute>} />
        <Route path="/skills/:parentId/new" element={<ProtectedRoute><SkillCreatePage /></ProtectedRoute>} />
        <Route path="/skills/:skillId/overview/:grade" element={<ProtectedRoute><SkillOverviewPage /></ProtectedRoute>} />
        <Route path="/skills/:skillId/overview" element={<ProtectedRoute><SkillOverviewPage /></ProtectedRoute>} />
        <Route path="/skills/:skillId/edit-details" element={<ProtectedRoute><SkillDetailEditPage /></ProtectedRoute>} />
        <Route path="/skill-parents/:parentId/overview" element={<ProtectedRoute><SkillParentOverviewPage /></ProtectedRoute>} />

        <Route path="/admin/tutors" element={<ProtectedRoute><TutorListPage /></ProtectedRoute>} />
        <Route path="/admin/tutors/new" element={<ProtectedRoute><TutorCreatePage /></ProtectedRoute>} />
        <Route path="/admin/sms" element={<ProtectedRoute><AdminSMSInboxPage /></ProtectedRoute>} />
        <Route path="/admin/sms/:conversationId" element={<ProtectedRoute><AdminSMSConversationPage /></ProtectedRoute>} />
        <Route path="/admin/emails" element={<ProtectedRoute><AdminEmailPage /></ProtectedRoute>} />

        <Route path="/tutors/:id" element={<ProtectedRoute><TutorHomePage /></ProtectedRoute>} />
        <Route path="/tutors/:id/booking" element={<ProtectedRoute><TutorBookingPage /></ProtectedRoute>} />
        <Route path="/tutors/:id/schedule" element={<ProtectedRoute><TutorSchedulePage /></ProtectedRoute>} />
        <Route path="/tutors/:id/edit" element={<ProtectedRoute><TutorEditPage /></ProtectedRoute>} />
        <Route path="/tutors/:id/sms" element={<TutorSMSInboxPage />} />
        <Route path="/tutors/:id/sms/:conversationId" element={<TutorSMSConversationPage />} />
        <Route path="/tutors/:id/post-tuition" element={<ProtectedRoute><PostTuitionListPage /></ProtectedRoute>} />
        <Route path="/tutors/:id/post-tuition/review" element={<ProtectedRoute><PostTuitionPage /></ProtectedRoute>} />
        <Route path="/tutors/:id/payments" element={<ProtectedRoute><TutorPaymentsPage /></ProtectedRoute>} />
        <Route path="/tutors/:id/billing" element={<ProtectedRoute><TutorBillingPage /></ProtectedRoute>} />
        <Route path="/tutors/:id/set-fee" element={<ProtectedRoute><TutorSetFeePage /></ProtectedRoute>} />

        <Route path="/admin/payments" element={<ProtectedRoute><AdminPaymentsPage /></ProtectedRoute>} />
        <Route path="/admin/variables" element={<ProtectedRoute><VariablesPage /></ProtectedRoute>} />
        <Route path="/admin/students" element={<ProtectedRoute><StudentListPage /></ProtectedRoute>} />
        <Route path="/admin/students/new" element={<ProtectedRoute><StudentCreatePage /></ProtectedRoute>} />

        <Route path="/students/:studentId/edit" element={<ProtectedRoute><StudentEditPage /></ProtectedRoute>} />
        <Route path="/students/:studentId/focus-areas" element={<ProtectedRoute><StudentFocusPage /></ProtectedRoute>} />
        <Route path="/students/:studentId/test" element={<ProtectedRoute><TestPage /></ProtectedRoute>} />
        <Route path="/students/:studentId/test/:skillId" element={<ProtectedRoute><StudentQuestionPage /></ProtectedRoute>} />
        <Route path="/students/:id/booking" element={<ProtectedRoute><StudentBookingPage /></ProtectedRoute>} />
        <Route path="/students/:studentId/past-tests" element={<ProtectedRoute><PastTestsPage /></ProtectedRoute>} />
        <Route path="/students/:studentId/assessment/:assessmentId" element={<ProtectedRoute><AssessmentQuestionPage /></ProtectedRoute>} />
        <Route path="/students/:id" element={<ProtectedRoute><StudentHomePage /></ProtectedRoute>} />

        <Route path="/knowledge" element={<ProtectedRoute><KnowledgeListPage /></ProtectedRoute>} />
        <Route path="/knowledge/new" element={<ProtectedRoute><KnowledgeEditorPage /></ProtectedRoute>} />
        <Route path="/knowledge/:id" element={<ProtectedRoute><KnowledgeEditorPage /></ProtectedRoute>} />

        <Route path="/principles" element={<ProtectedRoute><PrinciplesPage /></ProtectedRoute>} />
        <Route path="/feedback" element={<ProtectedRoute><FeedbackPage /></ProtectedRoute>} />
        <Route path="/docs" element={<ProtectedRoute><DocsPage /></ProtectedRoute>} />

        {/* ONLINE SESSION */}
        <Route path="/session/:roomName" element={<ProtectedRoute><TutoringRoomPage /></ProtectedRoute>} />

        {/* DEFAULT */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;