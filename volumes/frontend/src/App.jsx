import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Signup from './pages/Signup';
import Home from './pages/Home';
import Profile from './pages/Profile';
import Header from './components/Header'
import Footer from './components/Footer'
import { Toaster } from "@/components/ui/toast";
import ProtectedRoute from './components/ProtectedRoute';
import { useState, useEffect } from 'react';
import { fetchWithAuth } from './lib/refreshFlow';


const PUBLIC_ROUTES = ['/login', '/signup', '/forgot-password', '/reset-password'];

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    if (PUBLIC_ROUTES.includes(location.pathname)) {
      setLoading(false);
      return;
    }

    async function checkAuth() {
      try {
        const response = await fetchWithAuth('https://localhost:8080/api/auth/me/', {
          method: 'GET',
        });
        setIsAuthenticated(response.ok);
      } catch {
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    }
    checkAuth();
  }, [location.pathname]);

  if (loading) return <p>Chargement...</p>;

  return (
    <div className='flex flex-col min-h-screen'>
      <Header onLogout={() => setIsAuthenticated(false)}/>
      <main className="flex-1 flex items-center justify-center">
        <Routes>
          <Route path="/login" element={<Login onLoginSuccess={() => setIsAuthenticated(true)} />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/signup" element={<Signup />} />

          <Route 
            path="/home"
            element={
              <ProtectedRoute isAuthenticated={isAuthenticated}>
                <Home />
              </ProtectedRoute>
              }
          />
          
          <Route path="/profile"
            element={
              <ProtectedRoute isAuthenticated={isAuthenticated}>
                <Profile />
              </ProtectedRoute>
              }
          />
        </Routes>
      </main>
      <Footer />
      <Toaster />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;