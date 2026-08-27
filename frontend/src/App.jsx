import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './routes/ProtectedRoute'
import RequireRole from './routes/RequireRole'
import LoginPage from './pages/LoginPage'
import UnauthorizedPage from './pages/UnauthorizedPage'
import NotFoundPage from './pages/NotFoundPage'
import AdminLayout from './layouts/AdminLayout'
import DashboardPage from './pages/admin/DashboardPage'
import MonitoringEventsPage from './pages/admin/MonitoringEventsPage'
import AuditHistoryPage from './pages/admin/AuditHistoryPage'
import StudentLayout from './layouts/StudentLayout'
import StudentHome from './pages/student/StudentHome'
import ExamListPage from './pages/student/ExamListPage'
import ExamDetailPage from './pages/student/ExamDetailPage'
import InstructionsPage from './pages/student/InstructionsPage'
import ReadinessPage from './pages/student/ReadinessPage'
import TakeExamPage from './pages/student/TakeExamPage'
import ResultPage from './pages/student/ResultPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<RequireRole role="admin" />}>
          <Route element={<AdminLayout />}>
            <Route path="/admin" element={<DashboardPage />} />
            <Route path="/admin/monitoring" element={<MonitoringEventsPage />} />
            <Route path="/admin/audit" element={<AuditHistoryPage />} />
          </Route>
        </Route>

        <Route element={<RequireRole role="student" />}>
          <Route element={<StudentLayout />}>
            <Route path="/student" element={<StudentHome />} />
            <Route path="/student/exams" element={<ExamListPage />} />
            <Route path="/student/exams/:examId" element={<ExamDetailPage />} />
            <Route path="/student/exams/:examId/instructions" element={<InstructionsPage />} />
            <Route path="/student/exams/:examId/readiness" element={<ReadinessPage />} />
            <Route path="/student/exams/:examId/take" element={<TakeExamPage />} />
            <Route path="/student/exams/:examId/result" element={<ResultPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
