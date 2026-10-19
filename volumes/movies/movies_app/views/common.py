from rest_framework.exceptions import NotFound

from movies_app.services import catalog


def get_movie_or_404(movie_id):
    movie = catalog.resolve_movie(movie_id)
    if movie is None:
        raise NotFound("Movie not found.")
    return movie
