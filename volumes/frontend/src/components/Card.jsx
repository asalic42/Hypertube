import './Card.css'

// affiches de films
function Card({ film }) {
    const root_path = 'https://image.tmdb.org/t/p/w500';
    return(
        <div className='movie-card'>
            <img src={`${root_path}${film.poster_path}`} alt={film.title} ></img>
            <h4>{film.title}</h4>
            <p> Note : {film.vote_average}/10</p>
            <button>{film.favori ? '❤️' : '🤍'}</button>
        </div>
    );
}

export default Card;