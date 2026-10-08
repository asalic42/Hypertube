import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from botocore.exceptions import ClientError

from django.test import SimpleTestCase, TestCase, override_settings

from movies_app.models import Comment, Download, MergedMovie, Movie, Rendition, SourceItem, Subtitle, Torrent, WatchRecord
from movies_app.services import catalog, media, renditions, streaming, subtitles, tmdb
from movies_app.services.providers import ProviderItem, ProviderTorrent, archive, publicdomaintorrents
from movies_app.services.titles import clean_title

USER = "6f1f0d3c-5a44-4c55-9d0e-0a1b2c3d4e5f"


class TitleTests(SimpleTestCase):
    def test_strips_noise_and_extracts_year(self):
        self.assertEqual(clean_title("Night of the Living Dead (1968) [HD]"), ("Night of the Living Dead", 1968))
        self.assertEqual(clean_title("his_girl_friday"), ("his girl friday", None))

    def test_source_year_wins_and_numeric_title_survives(self):
        self.assertEqual(clean_title("Metropolis 1927 restored", 1927), ("Metropolis", 1927))
        self.assertEqual(clean_title("1984"), ("1984", 1984))


class SubtitleTests(SimpleTestCase):
    def test_srt_is_converted_to_vtt(self):
        vtt = subtitles.to_vtt("﻿1\r\n00:00:01,500 --> 00:00:03,000\r\nHello, world\r\n")
        self.assertTrue(vtt.startswith("WEBVTT\n\n1\n00:00:01.500 --> 00:00:03.000\nHello, world"))

    def test_vtt_is_kept(self):
        self.assertEqual(subtitles.to_vtt("WEBVTT\n\n00:01.000 --> 00:02.000\nHi"), "WEBVTT\n\n00:01.000 --> 00:02.000\nHi\n")

    def test_language_is_read_from_file_name(self):
        self.assertEqual(subtitles.guess_language("movie.eng.srt"), "en")
        self.assertEqual(subtitles.guess_language("Film_french.vtt"), "fr")
        self.assertIsNone(subtitles.guess_language("movie.srt"))


class RangeTests(SimpleTestCase):
    def test_ranges(self):
        self.assertEqual(streaming.parse_range("bytes=0-99", 1000), (0, 99))
        self.assertEqual(streaming.parse_range("bytes=900-", 1000), (900, 999))
        self.assertEqual(streaming.parse_range("bytes=-100", 1000), (900, 999))
        self.assertEqual(streaming.parse_range("bytes=0-5000", 1000), (0, 999))
        self.assertIsNone(streaming.parse_range(None, 1000))
        self.assertIsNone(streaming.parse_range("bytes=0-1,5-9", 1000))

    def test_unsatisfiable(self):
        for header in ("bytes=1000-", "bytes=5-2", "bytes=-0"):
            with self.assertRaises(streaming.RangeNotSatisfiable):
                streaming.parse_range(header, 1000)


class StreamTokenTests(SimpleTestCase):
    def test_token_is_bound_to_its_movie(self):
        token = streaming.make_token(USER, 7)
        self.assertEqual(streaming.read_token(token, 7), USER)
        self.assertIsNone(streaming.read_token(token, 8))
        self.assertIsNone(streaming.read_token(token + "x", 7))

    def test_token_expires(self):
        token = streaming.make_token(USER, 7)
        with override_settings(STREAM_TOKEN_MAX_AGE=-1):
            self.assertIsNone(streaming.read_token(token, 7))


class MediaPathTests(SimpleTestCase):
    @override_settings(MOVIES_DOWNLOAD_DIR="/downloads")
    def test_paths_escaping_the_download_root_are_refused(self):
        for local_path in ("", "../etc/passwd", "1/data/../../../etc/passwd", "/etc/passwd"):
            with self.assertRaises(media.MediaError):
                media.local_video_path(SimpleNamespace(local_path=local_path))
        self.assertEqual(
            str(media.local_video_path(SimpleNamespace(local_path="1/data/film/film.mp4"))),
            "/downloads/1/data/film/film.mp4",
        )


class RenditionLadderTests(SimpleTestCase):
    @override_settings(MOVIE_RENDITION_HEIGHTS=(1080, 720, 480, 360))
    def test_only_lower_resolutions_are_made(self):
        self.assertEqual(media.rendition_heights(1080), [720, 480, 360])
        self.assertEqual(media.rendition_heights(720), [480, 360])
        self.assertEqual(media.rendition_heights(2160), [1080, 720, 480, 360])
        self.assertEqual(media.rendition_heights(360), [])
        self.assertEqual(media.rendition_heights(None), [])

    def test_probe_ignores_cover_art(self):
        streams = {
            "streams": [
                {"codec_type": "video", "codec_name": "mjpeg", "width": 300, "height": 300},
                {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
                {"codec_type": "audio", "codec_name": "aac"},
            ]
        }
        with mock.patch("movies_app.services.media._run", return_value=SimpleNamespace(stdout=json.dumps(streams).encode())):
            info = media.probe(Path("/x/video.mp4"))
        self.assertEqual((info["width"], info["height"]), (1280, 720))
        self.assertEqual((info["video_codecs"], info["audio_codecs"]), ({"mjpeg", "h264"}, {"aac"}))


class RenditionWorkerTests(TestCase):
    def make_download(self, **fields):
        movie = Movie.objects.create(title="Charade")
        fields = {"status": Download.Status.READY, "storage_key": f"{movie.pk}/video.mp4", "storage_size": 10, **fields}
        return Download.objects.create(movie=movie, **fields)

    @override_settings(MOVIE_RENDITION_HEIGHTS=(1080, 720, 480, 360))
    def test_planning_records_the_frame_size_and_queues_the_ladder(self):
        download = self.make_download()
        with mock.patch("movies_app.services.media.probe", return_value={"width": 1280, "height": 720, "video_codecs": set(), "audio_codecs": set()}):
            renditions.plan(download, Path("/x/final.mp4"))
        download.refresh_from_db()
        self.assertEqual((download.width, download.height, download.renditions_planned), (1280, 720, True))
        self.assertEqual(list(download.renditions.values_list("height", "status")), [(480, "pending"), (360, "pending")])

    def test_unreadable_file_makes_no_rendition(self):
        download = self.make_download()
        with mock.patch("movies_app.services.media.probe", side_effect=media.MediaError("bad")):
            renditions.plan(download, Path("/x/final.mp4"))
        download.refresh_from_db()
        self.assertEqual((download.height, download.renditions_planned, download.renditions.count()), (None, True, 0))

    @override_settings(MOVIE_RENDITION_HEIGHTS=(720, 480))
    def test_worker_encodes_from_the_stored_file(self):
        stale = self.make_download(renditions_planned=True)  # nothing pending: never picked
        download = self.make_download()
        self.assertEqual(renditions.next_download(), download)

        def fake_encode(source, target, height):
            target.write_bytes(b"v" * height)
            return target, "video/mp4"

        with tempfile.TemporaryDirectory() as root, override_settings(MOVIES_DOWNLOAD_DIR=root), \
                mock.patch("movies_app.services.storage.download_file", side_effect=lambda key, path: Path(path).write_bytes(b"src")), \
                mock.patch("movies_app.services.storage.upload_file") as upload, \
                mock.patch("movies_app.services.media.probe", return_value={"width": 1920, "height": 1080, "video_codecs": set(), "audio_codecs": set()}), \
                mock.patch("movies_app.services.media.encode_rendition", side_effect=fake_encode):
            self.assertTrue(renditions.process_next())
            self.assertFalse(Path(root, "renditions").exists() and any(Path(root, "renditions").iterdir()))
        self.assertEqual([call.args[1] for call in upload.call_args_list], [f"{download.movie_id}/video_720p.mp4", f"{download.movie_id}/video_480p.mp4"])
        self.assertEqual(
            list(download.renditions.values_list("height", "status", "storage_size", "width")),
            [(720, "ready", 720, 1920), (480, "ready", 480, 1920)],
        )
        self.assertIsNone(renditions.next_download())
        self.assertFalse(renditions.process_next())
        self.assertEqual(stale.renditions.count(), 0)

    def test_encoding_failure_is_recorded_and_not_retried_forever(self):
        download = self.make_download(renditions_planned=True, height=720)
        Rendition.objects.create(download=download, height=480)
        with tempfile.TemporaryDirectory() as root, override_settings(MOVIES_DOWNLOAD_DIR=root), \
                mock.patch("movies_app.services.storage.download_file", side_effect=lambda key, path: Path(path).write_bytes(b"src")), \
                mock.patch("movies_app.services.media.encode_rendition", side_effect=media.MediaError("ffmpeg failed")):
            self.assertTrue(renditions.process_next())
        rendition = download.renditions.get()
        self.assertEqual((rendition.status, rendition.error), ("failed", "ffmpeg failed"))
        self.assertIsNone(renditions.next_download())

    def test_missing_stored_file_gives_up(self):
        download = self.make_download()
        error = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        with tempfile.TemporaryDirectory() as root, override_settings(MOVIES_DOWNLOAD_DIR=root), \
                mock.patch("movies_app.services.storage.download_file", side_effect=error):
            self.assertTrue(renditions.process_next())
        download.refresh_from_db()
        self.assertTrue(download.renditions_planned)
        self.assertIsNone(renditions.next_download())

    def test_removal_erases_every_stored_file(self):
        download = self.make_download()
        Rendition.objects.create(download=download, height=480, status=Rendition.Status.READY, storage_key="k/480")
        Rendition.objects.create(download=download, height=360)
        with mock.patch("movies_app.services.storage.delete") as delete:
            renditions.remove_stored(download)
        self.assertEqual([call.args[0] for call in delete.call_args_list], [download.storage_key, "k/480"])
        self.assertEqual(download.renditions.count(), 0)


class ProviderTests(SimpleTestCase):
    def test_archive_results(self):
        payload = {"response": {"docs": [{"identifier": "his_girl_friday", "title": "His Girl Friday", "year": "1940", "downloads": 42}]}}
        with mock.patch("movies_app.services.http.get", return_value=mock.Mock(json=lambda: payload)) as get:
            (item,) = archive.search(["girl", "fri(day"])
        self.assertIn(r"title:(girl AND fri\(day)", get.call_args.kwargs["params"]["q"])
        self.assertEqual((item.external_id, item.year, item.downloads), ("his_girl_friday", 1940, 42))
        self.assertEqual(
            item.torrents[0].torrent_url,
            "https://archive.org/download/his_girl_friday/his_girl_friday_archive.torrent",
        )

    def test_publicdomaintorrents_pages(self):
        listing = '<a href="nshowmovie.html?movieid=836">A Bucket of Blood</a> <a href=nshowmovie.html?movieid=374>Abilene Town</a>'
        with mock.patch("movies_app.services.http.get", return_value=mock.Mock(text=listing)):
            items = publicdomaintorrents.catalog()
        self.assertEqual([(item.external_id, item.title) for item in items], [("836", "A Bucket of Blood"), ("374", "Abilene Town")])

        page = (
            "<a href=http://imdb.com/title/tt0052655/>imdb</a>"
            "<a href=http://x.com/bt/btdownload.php?type=torrent&file=Blood.avi.torrent>avi</a>"
            "<a href=http://x.com/bt/btdownload.php?type=torrent&file=Blood.mp4.torrent>mp4</a>"
            "<a href=http://x.com/bt/btdownload.php?type=torrent&file=Blood_PSP.MP4.torrent>psp</a>"
        )
        with mock.patch("movies_app.services.http.get", return_value=mock.Mock(text=page)):
            details = publicdomaintorrents.details("836")
        self.assertEqual(details.imdb_id, "tt0052655")
        self.assertEqual([torrent.video_format for torrent in details.torrents], ["avi", "mp4"])


class TMDbMatchTests(SimpleTestCase):
    def test_only_confident_matches_are_accepted(self):
        results = [
            {"id": 1, "title": "Night of the Living Dead", "release_date": "1990-10-19"},
            {"id": 2, "title": "Night of the Living Dead", "release_date": "1968-10-04"},
            {"id": 3, "title": "Dawn of the Dead", "release_date": "1968-01-01"},
        ]
        self.assertEqual(tmdb._pick(results, "night of the living dead", 1968)["id"], 2)
        self.assertIsNone(tmdb._pick(results, "Some Home Video", None))


def make_item(external_id, title, downloads=0, provider=SourceItem.Provider.ARCHIVE):
    return ProviderItem(
        provider=provider,
        external_id=external_id,
        title=title,
        item_url=f"https://archive.org/details/{external_id}",
        downloads=downloads,
        torrents=[ProviderTorrent(torrent_url=f"https://archive.org/download/{external_id}/{external_id}_archive.torrent")],
    )


class CatalogTests(TestCase):
    def test_upsert_is_idempotent_and_tracks_popularity(self):
        catalog.upsert_items([make_item("a", "Charade (1963)", downloads=10)])
        catalog.upsert_items([make_item("a", "Charade (1963)", downloads=25)])
        movie = Movie.objects.get()
        self.assertEqual((movie.title, movie.year, movie.popularity), ("Charade", 1963, 25))
        self.assertEqual(Torrent.objects.count(), 1)

    def test_search_words_ignore_accents_and_punctuation(self):
        Movie.objects.create(title="Les Misérables")
        words = catalog.search_words("  MISERABLES, les! ")
        self.assertEqual(words, ["miserables", "les"])
        self.assertEqual(catalog.filter_by_words(Movie.objects.all(), words).count(), 1)

    def test_merge_keeps_everything_and_old_ids_resolve(self):
        catalog.upsert_items([make_item("a", "Charade", 10), make_item("b", "Charade 1963 HD", 5)])
        keep, duplicate = Movie.objects.order_by("id")
        old_id = duplicate.pk
        Comment.objects.create(movie=duplicate, user_id=USER, username="ana", content="great")
        WatchRecord.objects.create(movie=duplicate, user_id=USER)
        Subtitle.objects.create(movie=duplicate, language="en")

        catalog.merge_movies(keep=keep, duplicate=duplicate)

        keep.refresh_from_db()
        self.assertEqual(Movie.objects.count(), 1)
        self.assertEqual(keep.sources.count(), 2)
        self.assertEqual(keep.popularity, 15)
        self.assertEqual((keep.comments.count(), keep.watch_records.count(), keep.subtitles.count()), (1, 1, 1))
        self.assertEqual(MergedMovie.objects.get(old_id=old_id).movie, keep)
        self.assertEqual(catalog.resolve_movie(old_id), keep)

    def test_enrichment_merges_items_matching_the_same_film(self):
        catalog.upsert_items([make_item("a", "Charade", 10), make_item("b", "Charade 1963", 5)])
        metadata = tmdb.TMDbMovie(tmdb_id=4808, title="Charade", year=1963, rating=7.7, genres=["Comedy", "Mystery"])
        with (
            override_settings(TMDB_API_KEY="key"),
            mock.patch.object(tmdb, "find_id", return_value=4808),
            mock.patch.object(tmdb, "movie", return_value=metadata),
        ):
            catalog.enrich(list(Movie.objects.prefetch_related("sources")))

        movie = Movie.objects.get()
        self.assertEqual((movie.tmdb_id, movie.rating, movie.metadata_status), (4808, 7.7, Movie.MetadataStatus.MATCHED))
        self.assertEqual(sorted(movie.genres.values_list("name", flat=True)), ["Comedy", "Mystery"])
        self.assertEqual(movie.sources.count(), 2)

    def test_archive_torrents_are_preferred(self):
        movie = Movie.objects.create(title="Charade")
        pdt = SourceItem.objects.create(movie=movie, provider="pdt", external_id="1", title="Charade", item_url="https://x.test/1")
        ia = SourceItem.objects.create(movie=movie, provider="archive", external_id="c", title="Charade", item_url="https://x.test/c")
        avi = Torrent.objects.create(source=pdt, torrent_url="https://x.test/c.avi.torrent", video_format="avi")
        mp4 = Torrent.objects.create(source=pdt, torrent_url="https://x.test/c.mp4.torrent", video_format="mp4")
        web_seeded = Torrent.objects.create(source=ia, torrent_url="https://x.test/c_archive.torrent")
        self.assertEqual(catalog.candidate_torrents(movie), [web_seeded, mp4, avi])
        self.assertEqual(catalog.candidate_torrents(movie, exclude_ids=[web_seeded.pk]), [mp4, avi])
