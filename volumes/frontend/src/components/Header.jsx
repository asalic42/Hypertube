import { useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { LogOut, Menu, Search, UserRound, X } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { useAuth } from "@/hooks/useAuth";
import { useTranslation } from "@/hooks/useTranslation";
import ThemeToggle from "@/components/ThemeToggle";

// Dark chrome in the dark theme; in the light one the header is a card in the page's own colors.
const linkClass = "flex min-h-11 items-center gap-2 rounded-md px-3 text-sm font-medium text-foreground/85 hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/70 dark:text-white/85 dark:hover:bg-primary/40 dark:hover:text-white";

function Header() {
    const { user, logout } = useAuth();
    const { t } = useTranslation();
    const navigate = useNavigate();
    const location = useLocation();
    const [searchParams] = useSearchParams();
    const searched = searchParams.get('search') || '';
    const [search, setSearch] = useState(searched);
    const [lastSearched, setLastSearched] = useState(searched);
    const [menuOpen, setMenuOpen] = useState(false);
    const pagesAuth = ['/login', '/signup', '/forgot-password', '/reset-password'];

    if (searched !== lastSearched) {
        setLastSearched(searched);
        setSearch(searched);
    }

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
            toast.add({ title: t("Error"), description: err.message, type: "error" });
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
                {t("Logout")}
            </button>
            <ThemeToggle className="hover:bg-accent dark:hover:bg-primary/40" />
        </>
    );

    return (
        <header className="sticky top-0 z-10 border-b border-border bg-card text-foreground shadow-md shadow-black/10 dark:border-primary/60 dark:bg-black dark:text-white dark:shadow-black/40">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-2 px-4 py-2 sm:flex-nowrap sm:gap-x-4">
                <Link to="/home" className="flex min-h-11 items-center text-lg font-bold tracking-tight">
                    Hyper<span className="text-brand">tube</span>
                </Link>

                <form onSubmit={handleSearch} role="search" className="order-last w-full sm:order-none sm:ml-auto sm:w-auto sm:max-w-sm sm:flex-1">
                    <div className="relative">
                        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground dark:text-white/50" aria-hidden="true" />
                        <Input
                            type="search"
                            aria-label={t("Search")}
                            placeholder={t("Search movies...")}
                            className="h-10 w-full border-border bg-muted pl-8 text-foreground placeholder:text-muted-foreground focus-visible:border-brand focus-visible:ring-brand/40 sm:h-9 dark:border-white/15 dark:bg-white/5 dark:text-white dark:placeholder:text-white/40"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>
                </form>

                <nav className="hidden items-center gap-1 sm:flex" aria-label={t("Account")}>
                    {menu}
                </nav>

                <button
                    type="button"
                    className="ml-auto flex size-11 items-center justify-center rounded-md hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/70 sm:hidden dark:hover:bg-primary/40"
                    aria-label={menuOpen ? t("Close menu") : t("Open menu")}
                    aria-expanded={menuOpen}
                    aria-controls="mobile-menu"
                    onClick={() => setMenuOpen((open) => !open)}
                >
                    {menuOpen ? <X className="size-6" aria-hidden="true" /> : <Menu className="size-6" aria-hidden="true" />}
                </button>
            </div>

            {menuOpen && (
                <nav id="mobile-menu" className="flex flex-col gap-1 border-t border-border px-4 py-2 sm:hidden dark:border-white/10" aria-label={t("Account")}>
                    {menu}
                </nav>
            )}
        </header>
    );
}

export default Header;
