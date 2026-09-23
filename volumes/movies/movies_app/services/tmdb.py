from dataclasses import dataclass, field
from difflib import SequenceMatcher

import requests
from django.conf import settings

from movies_app.models import normalize_title
from movies_app.services import http

API_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p"
MIN_TITLE_SIMILARITY = 0.85
MAX_CAST = 10


class TMDbError(Exception):
    pass


@dataclass
class TMDbMovie:
    tmdb_id: int
    title: str
    imdb_id: str = ""
    year: int | None = None
    overview: str = ""
    cover_url: str = ""
    backdrop_url: str = ""
    rating: float | None = None
    vote_count: int = 0
    runtime: int | None = None
    original_language: str = ""
    genres: list[str] = field(default_factory=list)
    directors: list[str] = field(default_factory=list)
    producers: list[str] = field(default_factory=list)
    cast: list[dict] = field(default_factory=list)


def is_configured():
    return bool(settings.TMDB_API_KEY)


def _get(path, **params):
    key = settings.TMDB_API_KEY
    headers = {"Accept": "application/json"}
    # v4 read tokens are JWTs sent as a bearer, v3 keys are a query parameter.
    if len(key) > 40:
        headers["Authorization"] = f"Bearer {key}"
    else:
        params["api_key"] = key
    try:
        return http.get(f"{API_URL}{path}", params=params, headers=headers).json()
    except (requests.RequestException, ValueError) as error:
        # The key travels in the URL for v3: never echo the request in errors.
        status = getattr(getattr(error, "response", None), "status_code", None)
        raise TMDbError(f"TMDb request to {path} failed (status {status})") from None


def _image(path, size):
    return f"{IMAGE_URL}/{size}{path}" if path else ""


def _year(release_date):
    return int(release_date[:4]) if release_date and release_date[:4].isdigit() else None


def _similarity(left, right):
    return SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio()


def _pick(results, title, year):
    """Only accept a confident match: source titles are too noisy to trust the first hit."""
    best, best_score = None, 0.0
    for result in results:
        score = max(
            _similarity(title, result.get("title", "")),
            _similarity(title, result.get("original_title", "")),
        )
        if score < MIN_TITLE_SIMILARITY:
            continue
        result_year = _year(result.get("release_date"))
        if year and result_year and abs(result_year - year) > 1:
            continue
        if year and result_year == year:
            score += 0.1
        if score > best_score:
            best, best_score = result, score
    return best


def find_id(title, year=None, imdb_id=""):
    """Resolve a TMDb id from an IMDb id when the source provides one, else by title."""
    if imdb_id:
        results = _get(f"/find/{imdb_id}", external_source="imdb_id").get("movie_results", [])
        if results:
            return results[0]["id"]

    params = {"query": title, "include_adult": "false"}
    if year:
        params["year"] = year
    match = _pick(_get("/search/movie", **params).get("results", []), title, year)
    if match is None and year:
        # Sources are often off on the year: retry without it, _pick still checks it loosely.
        params.pop("year")
        match = _pick(_get("/search/movie", **params).get("results", []), title, year)
    return match["id"] if match else None


def movie(tmdb_id):
    data = _get(f"/movie/{tmdb_id}", append_to_response="credits", language="en-US")
    credits = data.get("credits", {})
    crew = credits.get("crew", [])
    return TMDbMovie(
        tmdb_id=data["id"],
        title=data.get("title") or data.get("original_title") or "",
        imdb_id=data.get("imdb_id") or "",
        year=_year(data.get("release_date")),
        overview=data.get("overview") or "",
        cover_url=_image(data.get("poster_path"), "w500"),
        backdrop_url=_image(data.get("backdrop_path"), "w1280"),
        rating=round(data["vote_average"], 1) if data.get("vote_count") else None,
        vote_count=data.get("vote_count") or 0,
        runtime=data.get("runtime") or None,
        original_language=data.get("original_language") or "",
        genres=[genre["name"] for genre in data.get("genres", [])],
        directors=[member["name"] for member in crew if member.get("job") == "Director"],
        producers=[member["name"] for member in crew if member.get("job") == "Producer"],
        cast=[
            {
                "name": member["name"],
                "character": member.get("character") or "",
                "picture_url": _image(member.get("profile_path"), "w185"),
            }
            for member in credits.get("cast", [])[:MAX_CAST]
        ],
    )
