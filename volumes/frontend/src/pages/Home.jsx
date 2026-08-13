import { useEffect, useState } from 'react';
import FilmCard from '../components/FilmCard'
import { toast } from "@/components/ui/toast";

function Home() {
    const [films, setFilms] = useState([]);
    const [erreur, setError] = useState(null);
    const TMDB_API = import.meta.env.VITE_TMDB_API_KEY;
    const options = {method: 'GET', headers: {
        accept: 'application/json',
        Authorization: `Bearer ${TMDB_API}`
    }};

    useEffect (() => {

        async function getFilms() {
            try {
                const response = await fetch('https://api.themoviedb.org/3/movie/popular?language=en-US&page=1', options);
    
                if (!response.ok) {
                    throw new Error('Error fetch movies');
                }
    
                const data = await response.json();
                setFilms(data.results);
            } catch (err) {
                console.error(err);
                toast.add({
                    title: "Error",
                    description: err.message,
                    type: "error",
                });
            }
        }
        getFilms();
    }, []);


    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 p-4">
        {films.map((film) => (
            <FilmCard key={film.id} film={film} />
        ))}
        </div>
    );
}

export default Home;