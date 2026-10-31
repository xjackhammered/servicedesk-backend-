import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import NewRequestPage from './pages/NewRequestPage';
import RegisterPage from './pages/RegisterPage';
import RequestDetailPage from './pages/RequestDetailPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<DashboardPage />} />
        <Route
          path="/requests/new"
          element={<ProtectedRoute role="OPERATOR"><NewRequestPage /></ProtectedRoute>}
        />
        <Route path="/requests/:id" element={<RequestDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
