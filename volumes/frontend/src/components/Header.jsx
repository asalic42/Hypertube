import { useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { LogOut, Menu, Search, UserRound, X } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/useAuth";

const linkClass = "flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-medium hover:bg-black/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70";

function Header() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [searchParams] = useSearchParams();
    const searched = searchParams.get('search') || '';
    const [search, setSearch] = useState(searched);
    const [lastSearched, setLastSearched] = useState(searched);
    const [menuOpen, setMenuOpen] = useState(false);
    const pagesAuth = ['/login', '/signup', '/forgot-password', '/reset-password'];

    // Keep the field in sync when the query changes from elsewhere (back button, "Clear").
    if (searched !== lastSearched) {
        setLastSearched(searched);
        setSearch(searched);
    }

    // The mobile menu closes as soon as the viewer goes somewhere.
    const [menuPath, setMenuPath] = useState(location.pathname);
    if (location.pathname !== menuPath) {
        setMenuPath(location.pathname);
        setMenuOpen(false);
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

    const menu = (
        <>
            <Link to="/profile" className={linkClass}>
                <UserRound className="size-4 shrink-0" aria-hidden="true" />
                <span className="truncate">{user.username}</span>
            </Link>
            <button type="button" onClick={handleLogout} className={linkClass}>
                <LogOut className="size-4 shrink-0" aria-hidden="true" />
                Logout
            </button>
        </>
    );

    return (
        <header className="sticky top-0 z-10 bg-gray-700 text-white shadow-md">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2 sm:flex-nowrap sm:gap-x-4">
                <Link to="/home" className="flex min-h-11 items-center text-lg font-bold tracking-tight">
                    Hypertube
                </Link>

                {/* On phones the search takes its own full-width line under the brand. */}
                <form onSubmit={handleSearch} role="search" className="order-last w-full sm:order-none sm:ml-auto sm:w-auto sm:max-w-sm sm:flex-1">
                    <div className="relative">
                        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-gray-500" aria-hidden="true" />
                        <Input
                            type="search"
                            aria-label="Search"
                            placeholder="Search movies..."
                            className="h-10 w-full bg-white pl-8 text-black sm:h-9"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </form>

                <nav className="hidden items-stretch gap-1 sm:flex" aria-label="Account">
                    {menu}
                </nav>

                <button
                    type="button"
                    className="ml-auto flex size-11 items-center justify-center rounded-md hover:bg-black/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70 sm:hidden"
                    aria-label={menuOpen ? "Close menu" : "Open menu"}
                    aria-expanded={menuOpen}
                    aria-controls="mobile-menu"
                    onClick={() => setMenuOpen((open) => !open)}
                >
                    {menuOpen ? <X className="size-6" aria-hidden="true" /> : <Menu className="size-6" aria-hidden="true" />}
                </button>
            </div>

            {menuOpen && (
                <nav id="mobile-menu" className="flex flex-col gap-1 border-t border-gray-600 px-4 py-2 sm:hidden" aria-label="Account">
                    {menu}
                </nav>
            )}
        </header>
    );
}

export default Header;
