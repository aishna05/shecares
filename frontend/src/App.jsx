import { Navigate, Route, Routes } from "react-router-dom";
import Shell from "./components/Shell";
import { useAuth } from "./auth";
import { homeFor } from "./format";
import { AdminComplaints, AdminDoctors, AdminForum, AdminHome, AdminLogs, AdminUrgent } from "./pages/admin";
import { ArticleDetail, ArticleList } from "./pages/Articles";
import { Login, Register } from "./pages/AuthPages";
import Complaints from "./pages/Complaints";
import { DoctorHome, Schedule, Visit, WriteArticle } from "./pages/doctor";
import { ForumList, ForumThread } from "./pages/Forum";
import Landing from "./pages/Landing";
import { Appointments, DoctorDetail, FindDoctor, PatientHome, Records, Tracker } from "./pages/patient";

function Protected({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to={homeFor(user)} replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Landing />} />
        <Route path="about" element={<Navigate to="/" replace />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route path="forum" element={<Protected><ForumList /></Protected>} />
        <Route path="forum/:id" element={<Protected><ForumThread /></Protected>} />
        <Route path="articles" element={<Protected><ArticleList /></Protected>} />
        <Route path="articles/:id" element={<Protected><ArticleDetail /></Protected>} />
        <Route path="complaints" element={<Protected><Complaints /></Protected>} />
        <Route path="patient" element={<Protected role="patient"><PatientHome /></Protected>} />
        <Route path="patient/doctors" element={<Protected role="patient"><FindDoctor /></Protected>} />
        <Route path="patient/doctors/:id" element={<Protected role="patient"><DoctorDetail /></Protected>} />
        <Route path="patient/appointments" element={<Protected role="patient"><Appointments /></Protected>} />
        <Route path="patient/records" element={<Protected role="patient"><Records /></Protected>} />
        <Route path="patient/tracker" element={<Protected role="patient"><Tracker /></Protected>} />
        <Route path="doctor" element={<Protected role="doctor"><DoctorHome /></Protected>} />
        <Route path="doctor/schedule" element={<Protected role="doctor"><Schedule /></Protected>} />
        <Route path="doctor/visits/:id" element={<Protected role="doctor"><Visit /></Protected>} />
        <Route path="doctor/articles/new" element={<Protected role="doctor"><WriteArticle /></Protected>} />
        <Route path="admin" element={<Protected role="admin"><AdminHome /></Protected>} />
        <Route path="admin/doctors" element={<Protected role="admin"><AdminDoctors /></Protected>} />
        <Route path="admin/forum" element={<Protected role="admin"><AdminForum /></Protected>} />
        <Route path="admin/urgent" element={<Protected role="admin"><AdminUrgent /></Protected>} />
        <Route path="admin/complaints" element={<Protected role="admin"><AdminComplaints /></Protected>} />
        <Route path="admin/logs" element={<Protected role="admin"><AdminLogs /></Protected>} />
        <Route path="*" element={<p className="empty">That page is not on SheCares.</p>} />
      </Route>
    </Routes>
  );
}
