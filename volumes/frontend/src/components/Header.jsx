import { useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/useAuth";

function Header() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [searchParams] = useSearchParams();
    const searched = searchParams.get('search') || '';
    const [search, setSearch] = useState(searched);
    const [lastSearched, setLastSearched] = useState(searched);
    const pagesAuth = ['/login', '/signup', '/forgot-password', '/reset-password'];

    // Keep the field in sync when the query changes from elsewhere (back button, "Clear").
    if (searched !== lastSearched) {
        setLastSearched(searched);
        setSearch(searched);
    }

    function handleSearch(e) {
        e.preventDefault();
        const params = new URLSearchParams();
        if (search.trim()) params.set('search', search.trim());
        navigate(`/home?${params}`);
    }

    async function handleLogout() {
        try {
            await logout();
        } catch (err) {
            toast.add({ title: "Error", description: err.message, type: "error" });
        } finally {
            navigate('/login');
        }
    }

    if (pagesAuth.includes(location.pathname) || !user) {
        return null;
    }

    return (
        <header className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 bg-gray-700 px-4 text-white">
        <div>
            <Link 
                to="/home" 
                className="flex items-center text-lg font-bold"
            >
                Hypertube
            </Link>
        </div>
        <nav className="flex flex-wrap items-stretch">
            <form onSubmit={handleSearch} className="flex items-center py-2">
                <Input
                    type="search"
                    aria-label="Search"
                    placeholder="Search..."
                    className="w-48 bg-white text-black"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </form>

            <div className="flex items-stretch gap-2 ml-6">
            <Link to="/profile" className="flex items-center px-4 hover:bg-black">
                {user.username}
            </Link>
            <button type="button" onClick={handleLogout} className="flex items-center px-4 hover:bg-black">
                Logout
            </button>
            </div>
        </nav>
        </header>
    );
}

export default Header;
