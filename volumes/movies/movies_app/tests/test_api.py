import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from django.test import override_settings
from rest_framework.test import APITestCase

from movies_app.models import Comment, Download, Movie, SourceItem, Subtitle, Torrent, WatchRecord
from movies_app.services import streaming


def make_user(username="ana"):
    return SimpleNamespace(id=str(uuid.uuid4()), pk=None, username=username, is_authenticated=True, is_anonymous=False)


class ApiTestCase(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)
        # No test may reach the external sources.
        for target in ("refresh_popular", "refresh_search", "refresh_pdt_catalog"):
            patcher = mock.patch(f"movies_app.services.catalog.{target}")
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_movie(self, title="Charade", **fields):
        fields.setdefault("metadata_status", Movie.MetadataStatus.MATCHED)
        return Movie.objects.create(title=title, **fields)


class AuthenticationTests(ApiTestCase):
    def test_everything_but_the_front_page_needs_authentication(self):
        movie = self.make_movie()
        self.client.force_authenticate(None)
        for url in (
            f"/api/movies/{movie.pk}/",
            f"/api/movies/{movie.pk}/comments/",
            f"/api/movies/{movie.pk}/download/",
            f"/api/movies/{movie.pk}/stream/",
            f"/api/movies/{movie.pk}/subtitles/",
            "/api/movies/genres/",
            "/api/comments/",
        ):
            self.assertEqual(self.client.get(url).status_code, 401, url)
        self.assertEqual(self.client.get("/api/movies/").status_code, 200)

    def test_forged_tokens_are_rejected(self):
        self.client.force_authenticate(None)
        response = self.client.get("/api/comments/", HTTP_AUTHORIZATION="Bearer not.a.token")
        self.assertEqual(response.status_code, 401)

    def test_unsupported_methods(self):
        movie = self.make_movie()
        self.assertEqual(self.client.post("/api/movies/", {"title": "x"}).status_code, 405)
        self.assertEqual(self.client.delete(f"/api/movies/{movie.pk}/").status_code, 405)


class MovieListTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.charade = self.make_movie("Charade", year=1963, rating=7.7, popularity=50)
        self.zorro = self.make_movie("Zorro", year=1975, rating=6.1, popularity=90)
        self.alibi = self.make_movie("alibi", year=1929, rating=5.6, popularity=10)

    def titles(self, query=""):
        response = self.client.get(f"/api/movies/{query}")
        self.assertEqual(response.status_code, 200, response.data)
        return [movie["title"] for movie in response.data["results"]]

    def test_front_page_is_sorted_by_popularity(self):
        self.assertEqual(self.titles(), ["Zorro", "Charade", "alibi"])

    def test_search_results_are_sorted_by_name(self):
        self.make_movie("The Charade Affair")
        self.assertEqual(self.titles("?search=charade"), ["Charade", "The Charade Affair"])

    def test_filters_and_sort(self):
        self.assertEqual(self.titles("?year_min=1960&sort=-rating"), ["Charade", "Zorro"])
        self.assertEqual(self.titles("?rating_max=6&sort=year"), ["alibi"])
        self.assertEqual(self.titles("?sort=name"), ["alibi", "Charade", "Zorro"])

    def test_invalid_parameters(self):
        for query in ("?sort=id", "?year_min=abc", "?rating_min=11", "?year_min=2000&year_max=1990"):
            self.assertEqual(self.client.get(f"/api/movies/{query}").status_code, 400, query)

    def test_pagination_exposes_the_next_page(self):
        response = self.client.get("/api/movies/?page_size=2")
        self.assertEqual((response.data["count"], response.data["pages"], response.data["next_page"]), (3, 2, 2))
        self.assertIsNone(self.client.get("/api/movies/?page_size=2&page=2").data["next_page"])

    def test_watched_flag_is_per_user(self):
        WatchRecord.objects.create(user_id=self.user.id, movie=self.charade)
        WatchRecord.objects.create(user_id=uuid.uuid4(), movie=self.zorro)
        watched = {movie["title"]: movie["watched"] for movie in self.client.get("/api/movies/").data["results"]}
        self.assertEqual(watched, {"Charade": True, "Zorro": False, "alibi": False})

    def test_anonymous_front_page_ignores_parameters(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.titles("?search=charade&sort=name&page=5"), ["Zorro", "Charade", "alibi"])


class MovieDetailTests(ApiTestCase):
    def test_detail(self):
        movie = self.make_movie(year=1963, runtime=113, directors=["Stanley Donen"])
        Comment.objects.create(movie=movie, user_id=self.user.id, username="ana", content="great")
        Subtitle.objects.create(movie=movie, language="en", status=Subtitle.Status.READY)
        Subtitle.objects.create(movie=movie, language="fr")
        data = self.client.get(f"/api/movies/{movie.pk}/").data
        self.assertEqual((data["title"], data["year"], data["runtime"]), ("Charade", 1963, 113))
        self.assertEqual((data["comments_count"], data["subtitles"], data["download_status"]), (1, ["en"], None))

    def test_unknown_movie(self):
        self.assertEqual(self.client.get("/api/movies/999/").status_code, 404)


class CommentTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.movie = self.make_movie()

    def test_author_comes_from_the_token(self):
        response = self.client.post(
            "/api/comments/",
            {"comment": "  <b>nice</b>  ", "movie_id": self.movie.pk, "username": "mallory", "user_id": str(uuid.uuid4())},
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data["username"], response.data["comment"]), ("ana", "<b>nice</b>"))
        self.assertEqual(str(Comment.objects.get().user_id), self.user.id)

    def test_post_on_movie(self):
        response = self.client.post(f"/api/movies/{self.movie.pk}/comments/", {"comment": "hello"})
        self.assertEqual(response.status_code, 201)
        listing = self.client.get(f"/api/movies/{self.movie.pk}/comments/").data
        self.assertEqual([comment["comment"] for comment in listing["results"]], ["hello"])

    def test_validation(self):
        self.assertEqual(self.client.post("/api/comments/", {"comment": "x"}).status_code, 400)
        self.assertEqual(self.client.post("/api/comments/", {"comment": "x", "movie_id": 999}).status_code, 400)
        self.assertEqual(self.client.post("/api/comments/", {"comment": "   ", "movie_id": self.movie.pk}).status_code, 400)
        self.assertEqual(self.client.post("/api/comments/", {"comment": "x" * 2001, "movie_id": self.movie.pk}).status_code, 400)
        self.assertEqual(self.client.post("/api/movies/999/comments/", {"comment": "x"}).status_code, 404)

    def test_only_the_author_edits_or_deletes(self):
        comment = Comment.objects.create(movie=self.movie, user_id=uuid.uuid4(), username="bob", content="mine")
        url = f"/api/comments/{comment.pk}/"
        self.assertEqual(self.client.get(url).data["comment"], "mine")
        self.assertEqual(self.client.patch(url, {"comment": "hacked"}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertEqual(self.client.put(url, {"comment": "x"}).status_code, 405)

        own = Comment.objects.create(movie=self.movie, user_id=self.user.id, username="ana", content="first")
        url = f"/api/comments/{own.pk}/"
        self.assertEqual(self.client.patch(url, {"comment": "edited"}).data["comment"], "edited")
        self.assertEqual(self.client.delete(url).status_code, 204)


class PlaybackTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.movie = self.make_movie(original_language="en")
        source = SourceItem.objects.create(
            movie=self.movie,
            provider="archive",
            external_id="charade",
            title="Charade",
            item_url="https://archive.org/details/charade",
            details_fetched_at="2026-01-01T00:00:00Z",
        )
        self.torrent = Torrent.objects.create(source=source, torrent_url="https://archive.org/download/charade/charade_archive.torrent")
        self.url = f"/api/movies/{self.movie.pk}/download/"

    def test_download_is_created_once(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        with mock.patch("movies_app.services.users.preferred_language", return_value="fr"):
            first = self.client.put(self.url)
            second = self.client.put(self.url)
        self.assertEqual((first.status_code, second.status_code), (201, 200))
        download = Download.objects.get()
        self.assertEqual((download.status, download.torrent), (Download.Status.QUEUED, self.torrent))
        self.assertEqual((first.data["playable"], first.data["stream_url"]), (False, None))
        # English always, plus the language of a viewer who does not speak the film's one.
        self.assertEqual(sorted(self.movie.subtitles.values_list("language", flat=True)), ["en", "fr"])

    def test_failed_download_can_be_retried(self):
        Download.objects.create(movie=self.movie, status=Download.Status.FAILED, error="stalled", attempted_torrent_ids=[self.torrent.pk])
        response = self.client.put(self.url, {"language": "en"})
        self.assertEqual((response.status_code, response.data["status"], response.data["error"]), (200, "queued", ""))

    def test_movie_without_torrent(self):
        self.torrent.delete()
        self.assertEqual(self.client.put(self.url, {"language": "en"}).status_code, 409)
        self.assertEqual(self.client.put(self.url, {"language": "english"}).status_code, 400)

    def test_stream_waits_for_enough_data(self):
        Download.objects.create(movie=self.movie, status=Download.Status.DOWNLOADING, file_size=10**9, buffered_bytes=1000)
        self.assertEqual(self.client.get(f"/api/movies/{self.movie.pk}/stream/").status_code, 409)

    def test_stream_ranges_with_a_token(self):
        content = bytes(range(256)) * 40
        with tempfile.TemporaryDirectory() as root, override_settings(MOVIES_DOWNLOAD_DIR=root):
            download = Download.objects.create(
                movie=self.movie,
                status=Download.Status.PROCESSING,
                local_path="1/data/charade.mp4",
                file_size=len(content),
                file_offset=0,
                piece_length=4096,
            )
            path = Path(root) / download.local_path
            path.parent.mkdir(parents=True)
            path.write_bytes(content)

            token = self.client.get(self.url).data["stream_url"].split("token=")[1]
            self.client.force_authenticate(None)
            stream = f"/api/movies/{self.movie.pk}/stream/"

            response = self.client.get(f"{stream}?token={token}", HTTP_RANGE="bytes=100-4999", HTTP_ACCEPT="video/mp4")
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response["Content-Range"], f"bytes 100-4999/{len(content)}")
            self.assertEqual(b"".join(response.streaming_content), content[100:5000])

            full = self.client.get(f"{stream}?token={token}")
            self.assertEqual((full.status_code, full["Content-Length"]), (200, str(len(content))))
            self.assertEqual(b"".join(full.streaming_content), content)

            self.assertEqual(self.client.get(f"{stream}?token={token}", HTTP_RANGE="bytes=99999-").status_code, 416)
            other = streaming.make_token(self.user.id, self.movie.pk + 1)
            self.assertEqual(self.client.get(f"{stream}?token={other}").status_code, 401)
            self.assertEqual(self.client.get(stream).status_code, 401)

        self.assertTrue(WatchRecord.objects.filter(user_id=self.user.id, movie=self.movie).exists())
        self.movie.refresh_from_db()
        self.assertIsNotNone(self.movie.last_watched_at)

    def test_subtitle_track(self):
        Subtitle.objects.create(movie=self.movie, language="en", status=Subtitle.Status.READY, storage_key="1/subtitles/en.vtt")
        with mock.patch("movies_app.services.storage.read", return_value=b"WEBVTT\n"):
            response = self.client.get(f"/api/movies/{self.movie.pk}/subtitles/en/")
        self.assertEqual((response.status_code, response["Content-Type"]), (200, "text/vtt; charset=utf-8"))
        self.assertEqual(self.client.get(f"/api/movies/{self.movie.pk}/subtitles/fr/").status_code, 404)
