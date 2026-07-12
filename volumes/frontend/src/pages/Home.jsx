import { useEffect, useState } from 'react';
import Card from '../components/Card'
import './Home.css'

function Home() {
    const [films, setFilms] = useState([]);
    const [erreur, setError] = useState(null);
    const TMDB_API = import.meta.env.VITE_TMDB_API_KEY;
    const options = {method: 'GET', headers: {
        accept: 'application/json',
        Authorization: `Bearer ${TMDB_API}`
    }};

    useEffect(() => {
        async function getFilms() {
            try {
                const response = await fetch('https://api.themoviedb.org/3/movie/popular?language=en-US&page=1', options);

                if (!response.ok) {
                    throw new Error('Error fetch movies');
                }

                const data = await response.json();
                setFilms(data.results);
            } catch (err) {
                setError(err.message);
            }
        }

        getFilms();
    }, []);
    
    if (erreur) return <p>Erreur : {erreur}</p>;

    return (
        <div className='film-list'>
            {films.map((film) => (<Card key={film.id} film={film} />))}
        </div>
    );
}

export default Home;