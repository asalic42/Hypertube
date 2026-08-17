import { useLocation, useNavigate } from 'react-router-dom'
import { Link } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";


function Header({ onLogout }) {
    const navigate = useNavigate();
    const location = useLocation();
    const pagesAuth = ['/login', '/signup', '/forgot-password', '/reset-password'];

    async function handleLogout() {
        try{
            const response = await fetch('https://localhost:8080/api/auth/logout/', {
                method: 'POST',
                credentials: 'include',
            });
            if(!response.ok) {
                throw new Error(`Erreur ${response.status} lors de la déconnexion`);
            }
        } catch (err) {
            console.log(err);
            toast.add({
                title: "Error",
                description: err.message,
                type: "error",
            });
        } finally {
            localStorage.removeItem('access_token');
            onLogout();
            navigate('/login');
        }
    }

    if (pagesAuth.includes(location.pathname)) {
        return null;
    }

    return (
        <header className="sticky top-0 flex items-center justify-between bg-gray-700 px-4 text-white">
        <div>
            <Link 
                to="/home" 
                className="flex items-center text-lg font-bold"
            >
                Hypertube
            </Link>
        </div>
        <nav className="flex items-stretch">
            <div className="flex items-stretch gap-4">
            <div className="flex items-center py-2">
                <Input type="search" aria-label="Search" placeholder="Search..." className="w-48" />
            </div>
            </div>

            <div className="flex items-stretch gap-4 ml-6">
            <Link to="/home" className="flex items-center px-4 hover:bg-black">
                Language
            </Link>

            <button type="button" onClick={handleLogout} className="flex items-center px-4 hover:bg-black">
                Logout
            </button>
            
            <Link to="/profile" className="flex items-center px-4 hover:bg-black">
                Profile
            </Link>
            </div>
        </nav>
        </header>
    );
}

export default Header;