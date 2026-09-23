import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import FilmCard from '../components/FilmCard'
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect, NativeSelectOption } from "@/components/ui/native-select";
import { toast } from "@/components/ui/toast";
import { movies as moviesApi } from "@/lib/api";

const FILTERS = ['search', 'genre', 'sort', 'year_min', 'year_max', 'rating_min'];
const SORTS = [
    ['', 'Default'],
    ['name', 'Name A→Z'],
    ['-name', 'Name Z→A'],
    ['-rating', 'Best rated'],
    ['rating', 'Worst rated'],
    ['-year', 'Newest'],
    ['year', 'Oldest'],
    ['-popularity', 'Most popular'],
];

function Results({ params, onCount }) {
    const [films, setFilms] = useState([]);
    const [nextPage, setNextPage] = useState(null);
    const [count, setCount] = useState(null);
    // Page being fetched; null once it has arrived. Page 1 loads on mount.
    const [loadingPage, setLoadingPage] = useState(1);
    const sentinel = useRef(null);

    useEffect(() => {
        if (!loadingPage) return undefined;
        let cancelled = false;
        moviesApi.list({ ...params, page: loadingPage }).then((data) => {
            if (cancelled) return;
            setFilms((current) => (loadingPage === 1 ? data.results : [...current, ...data.results]));
            setNextPage(data.next_page);
            setCount(data.count);
            onCount(data.count);
        }).catch((err) => {
            if (!cancelled) toast.add({ title: "Error", description: err.message, type: "error" });
        }).finally(() => {
            if (!cancelled) setLoadingPage(null);
        });
        return () => {
            cancelled = true;
        };
    }, [params, loadingPage, onCount]);

    // Infinite scroll: the next page loads when the sentinel below the grid becomes visible.
    useEffect(() => {
        const element = sentinel.current;
        if (!element || !nextPage || loadingPage) return undefined;
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) setLoadingPage(nextPage);
        }, { rootMargin: '400px' });
        observer.observe(element);
        return () => observer.disconnect();
    }, [nextPage, loadingPage]);

    return (
        <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {films.map((film) => (
                    <FilmCard key={film.id} film={film} />
                ))}
            </div>
            {!loadingPage && count === 0 && (
                <p className="text-center text-muted-foreground py-8">No movie matches your search.</p>
            )}
            {loadingPage && <p className="text-center text-muted-foreground py-4">Loading...</p>}
            <div ref={sentinel} aria-hidden="true" />
        </>
    );
}

function Home() {
    const [searchParams, setSearchParams] = useSearchParams();
    const filtersKey = searchParams.toString();
    const filters = useMemo(() => Object.fromEntries(FILTERS.map((key) => [key, searchParams.get(key) || ''])), [searchParams]);
    const params = useMemo(() => Object.fromEntries(new URLSearchParams(filtersKey)), [filtersKey]);

    const [genres, setGenres] = useState([]);
    const [count, setCount] = useState(null);
    const [draft, setDraft] = useState(filters);
    const [lastFilters, setLastFilters] = useState(filters);
    // The form follows the URL (back button, header search) until the user edits it.
    if (filters !== lastFilters) {
        setLastFilters(filters);
        setDraft(filters);
        setCount(null);
    }

    useEffect(() => {
        moviesApi.genres().then(setGenres).catch(() => setGenres([]));
    }, []);

    function applyFilters(e) {
        e.preventDefault();
        const params = new URLSearchParams();
        for (const key of FILTERS) {
            if (draft[key]) params.set(key, draft[key]);
        }
        setSearchParams(params);
    }

    function updateDraft(e) {
        setDraft({ ...draft, [e.target.name]: e.target.value });
    }

    return (
        <div className="w-full max-w-7xl p-4 flex flex-col gap-4">
            <form onSubmit={applyFilters} className="flex flex-wrap items-end gap-3 rounded-xl bg-card p-4 shadow-xs ring-1 ring-foreground/10">
                <div className="grid gap-1">
                    <Label htmlFor="genre">Genre</Label>
                    <NativeSelect id="genre" name="genre" value={draft.genre} onChange={updateDraft}>
                        <NativeSelectOption value="">All</NativeSelectOption>
                        {genres.map((genre) => <NativeSelectOption key={genre} value={genre}>{genre}</NativeSelectOption>)}
                    </NativeSelect>
                </div>
                <div className="grid gap-1">
                    <Label htmlFor="year_min">Year from</Label>
                    <Input id="year_min" name="year_min" type="number" min="1880" max="2100" className="w-24" value={draft.year_min} onChange={updateDraft} />
                </div>
                <div className="grid gap-1">
                    <Label htmlFor="year_max">Year to</Label>
                    <Input id="year_max" name="year_max" type="number" min="1880" max="2100" className="w-24" value={draft.year_max} onChange={updateDraft} />
                </div>
                <div className="grid gap-1">
                    <Label htmlFor="rating_min">Min. rating</Label>
                    <Input id="rating_min" name="rating_min" type="number" min="0" max="10" step="0.5" className="w-24" value={draft.rating_min} onChange={updateDraft} />
                </div>
                <div className="grid gap-1">
                    <Label htmlFor="sort">Sort by</Label>
                    <NativeSelect id="sort" name="sort" value={draft.sort} onChange={updateDraft}>
                        {SORTS.map(([value, label]) => <NativeSelectOption key={value} value={value}>{label}</NativeSelectOption>)}
                    </NativeSelect>
                </div>
                <Button type="submit">Apply</Button>
                {filtersKey && (
                    <Button type="button" variant="outline" onClick={() => setSearchParams({})}>Clear</Button>
                )}
                <p className="ml-auto text-sm text-muted-foreground">
                    {filters.search ? <>Results for “{filters.search}”</> : "Most popular"}
                    {count !== null && <> · {count} movie{count === 1 ? "" : "s"}</>}
                </p>
            </form>

            <Results key={filtersKey} params={params} onCount={setCount} />
        </div>
    );
}

export default Home;
