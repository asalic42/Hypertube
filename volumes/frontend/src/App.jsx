import { BrowserRouter, Routes, Route } from 'react-router-dom';
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


function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkAuth() {
      try {
        const accessToken = localStorage.getItem('access_token');
        const response = await fetch('https://localhost:8080/api/auth/me/', {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          credentials: 'include',
        });
        setIsAuthenticated(response.ok);
      } catch {
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    }
    checkAuth();
  }, []);

  if (loading) return <p>Chargement...</p>;

  return (
    <BrowserRouter>
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
    </BrowserRouter>
  );
}

export default App;