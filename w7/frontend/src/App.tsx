import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import LoginPage from './pages/LoginPage';
import KnowledgeBasesPage from './pages/KnowledgeBasesPage';
import KBDetailPage from './pages/KBDetailPage';
import { Loader2 } from 'lucide-react';

/** Redirect unauthenticated users to login. */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return user ? <>{children}</> : <Navigate to="/" replace />;
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />
        <Route
          path="/knowledge-bases"
          element={
            <ProtectedRoute>
              <KnowledgeBasesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/kb"
          element={
            <ProtectedRoute>
              <KBDetailPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
