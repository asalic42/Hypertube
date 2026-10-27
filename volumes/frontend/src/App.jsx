import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import OAuthCallback from './pages/OAuthCallback';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Signup from './pages/Signup';
import Home from './pages/Home';
import Profile from './pages/Profile';
import UserProfile from './pages/UserProfile';
import Watch from './pages/Watch';
import Header from './components/Header'
import Footer from './components/Footer'
import ProtectedRoute from './components/ProtectedRoute';
import { Toaster } from "@/components/ui/toast";
import { AuthProvider } from '@/lib/auth';
import { I18nProvider } from '@/lib/i18nProvider';
import { ThemeProvider } from '@/lib/theme';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <I18nProvider>
        <ThemeProvider>
        <div className='flex flex-col min-h-screen'>
          <Header />
          <main className="flex-1 flex items-start justify-center">
            <Routes>
              <Route path="/" element={<Navigate to="/home" replace />} />
              <Route path="/login" element={<Login />} />
              <Route path="/oauth/callback" element={<OAuthCallback />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/home" element={<ProtectedRoute><Home /></ProtectedRoute>} />
              <Route path="/movies/:id" element={<ProtectedRoute><Watch /></ProtectedRoute>} />
              <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
              <Route path="/users/:id" element={<ProtectedRoute><UserProfile /></ProtectedRoute>} />
            </Routes>
          </main>
          <Footer />
          <Toaster />
        </div>
        </ThemeProvider>
        </I18nProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
