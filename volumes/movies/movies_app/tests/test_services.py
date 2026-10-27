import json
import re
import tempfile
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from botocore.exceptions import ClientError

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

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

    def test_cue_times_are_written_the_one_way_browsers_read(self):
        # Two decimals and a comma, as archive.org files come; no hours; one-digit hours; SubRip coordinates.
        srt = "1\n00:01:01,95 --> 00:01:08,9\nMean any American\n\n2\n01:08,950 --> 1:01:14.37 X1:100 X2:200 Y1:400 Y2:450\nof course\n"
        vtt = subtitles.to_vtt(srt)
        self.assertIn("00:01:01.950 --> 00:01:08.900\nMean any American", vtt)
        self.assertIn("00:01:08.950 --> 01:01:14.370\nof course", vtt)
        # Text that is not a timing line is left alone, and a WEBVTT file with commas is repaired too.
        self.assertIn("Meet at 10:30,5 tonight", subtitles.to_vtt("1\n00:00:01,000 --> 00:00:02,000\nMeet at 10:30,5 tonight"))
        self.assertEqual(subtitles.to_vtt("WEBVTT\n\n00:00:01,50 --> 00:00:02,00\nHi"), "WEBVTT\n\n00:00:01.500 --> 00:00:02.000\nHi\n")

    def test_vtt_is_kept(self):
        self.assertEqual(subtitles.to_vtt("WEBVTT\n\n00:01.000 --> 00:02.000\nHi"), "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi\n")

    def test_times_are_rescaled_to_the_speed_of_the_video(self):
        # A subtitle made for a 25 fps transfer runs 4% early on a film-speed video.
        vtt = subtitles.to_vtt("1\n00:01:00,000 --> 00:01:01,000\nHi", scale=25 / 23.976)
        self.assertIn("00:01:02.563 --> 00:01:03.605\nHi", vtt)
        self.assertEqual(subtitles.last_cue_end(vtt), 63.605)
        self.assertIsNone(subtitles.last_cue_end("WEBVTT\n\nNOTE nothing"))

    def test_running_speed_and_fit(self):
        self.assertEqual([subtitles.speed(rate) for rate in (23.976, 24, 29.97, 30, 25, 50, 19.2, None, 0)], [23.976] * 4 + [25.0] * 2 + [23.976, None, None])
        cue = "WEBVTT\n\n00:00:01.000 --> {}\nHi\n"
        self.assertTrue(subtitles.fits(cue.format("01:27:36.000"), 5504))  # ends a little before the credits
        self.assertTrue(subtitles.fits(cue.format("01:32:50.000"), 5504))  # 66 s past the end: longer credits
        self.assertFalse(subtitles.fits(cue.format("01:34:00.000"), 5504))  # a longer cut
        self.assertFalse(subtitles.fits(cue.format("00:11:42.000"), 5504))  # another film, or a sample
        self.assertTrue(subtitles.fits(cue.format("00:11:42.000"), None))  # running time unknown: nothing to check
        self.assertFalse(subtitles.fits("WEBVTT\n", 5504))

    def test_language_is_read_from_file_name(self):
        self.assertEqual(subtitles.guess_language("movie.eng.srt"), "en")
        self.assertEqual(subtitles.guess_language("Film_french.vtt"), "fr")
        self.assertIsNone(subtitles.guess_language("movie.srt"))


def srt_ending_at(seconds):
    minutes, secs = divmod(int(seconds), 60)
    return f"1\n00:00:01,000 --> 00:00:02,000\nFirst\n\n2\n00:{minutes:02d}:{secs:02d},000 --> 00:{minutes:02d}:{secs:02d},500\nLast\n"


def json_response(payload):
    return SimpleNamespace(json=lambda: payload, content=b"")


def shift_by(seconds):
    """A stand-in for ffsubsync: every cue of the input moved by `seconds`. Remembers the input it was given."""

    def align_subtitle(source, srt_in, srt_out):
        align_subtitle.received = srt_in.read_text()
        srt_out.write_text(re.sub(r"(\d\d):(\d\d):(\d\d),(\d\d\d)", lambda match: _moved(match, seconds), align_subtitle.received))
        return seconds, 1.0

    return align_subtitle


def _moved(match, seconds):
    total = round(((int(match[1]) * 60 + int(match[2])) * 60 + int(match[3])) * 1000 + int(match[4]) + seconds * 1000)
    hours, rest = divmod(total, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


@override_settings(OPENSUBTITLES_API_KEY="key", OPENSUBTITLES_USERNAME="")
class SubtitleMatchingTests(TestCase):
    """Subtitles are matched to the file the viewer gets, not to the film in general."""

    def setUp(self):
        self.movie = Movie.objects.create(title="His Girl Friday", imdb_id="tt0032599", original_language="en")
        self.item = SourceItem.objects.create(
            movie=self.movie, provider=SourceItem.Provider.ARCHIVE, external_id="his_girl_friday", title="x", item_url="https://archive.org/details/x"
        )
        SourceItem.objects.create(
            movie=self.movie, provider=SourceItem.Provider.ARCHIVE, external_id="HisGirlFriday1940", title="x", item_url="https://archive.org/details/y"
        )
        self.torrent = Torrent.objects.create(source=self.item, torrent_url="https://archive.org/x.torrent")
        self.download = Download.objects.create(
            movie=self.movie, torrent=self.torrent, status=Download.Status.READY, storage_key=f"{self.movie.pk}/video.mp4",
            local_path="4/data/his_girl_friday/his_girl_friday.mp4", duration=5504.0, frame_rate=29.97,
        )
        self.subtitle = Subtitle.objects.create(movie=self.movie, language="en")

    def process(self, **mocks):
        patches = {
            "archive": mock.patch("movies_app.services.providers.archive.subtitle_files", return_value=mocks.get("files", [])),
            "fetch": mock.patch("movies_app.services.subtitles._fetch", side_effect=mocks.get("fetch", lambda url, headers=None: "")),
            "get": mock.patch("movies_app.services.http.get", return_value=json_response({"data": mocks.get("entries", [])})),
            "post": mock.patch("movies_app.services.http.post", side_effect=mocks.get("post", lambda url, json, headers: json_response({"link": f"https://dl/{json['file_id']}"}))),
            "upload": mock.patch("movies_app.services.storage.upload_bytes"),
            "url": mock.patch("movies_app.services.storage.presigned_url", return_value="https://fs/video.mp4"),
            "align": mock.patch("movies_app.services.media.align_subtitle", side_effect=mocks.get("align", shift_by(0))),
        }
        with patches["archive"] as archive_files, patches["fetch"] as fetch, patches["get"] as get, patches["post"] as post, \
                patches["upload"] as upload, patches["url"], patches["align"] as align:
            mocks.get("run", subtitles.process)(self.subtitle)
        self.subtitle.refresh_from_db()
        return SimpleNamespace(archive_files=archive_files, fetch=fetch, get=get, post=post, upload=upload, align=align)

    def test_the_files_of_the_items_own_video_come_first_and_transcriptions_never(self):
        files = [
            ("his_girl_friday.asr.srt", "https://a/asr"),  # archive.org's speech recognition: garbage
            ("his_girl_friday_512kb.srt", "https://a/other"),  # another derivative of the same item
            ("his_girl_friday.srt", "https://a/own"),
            ("his_girl_friday.fre.srt", "https://a/fr"),
        ]
        calls = self.process(files=files, fetch=lambda url, headers=None: srt_ending_at(5400))
        calls.archive_files.assert_called_once_with("his_girl_friday")
        self.assertEqual([call.args[0] for call in calls.fetch.call_args_list], ["https://a/own"])
        self.assertEqual((self.subtitle.status, self.subtitle.origin, self.subtitle.storage_key), ("ready", "archive", f"{self.movie.pk}/subtitles/en.vtt"))
        calls.get.assert_not_called()

    def test_a_video_from_another_source_does_not_use_the_archive_files(self):
        pdt = SourceItem.objects.create(movie=self.movie, provider=SourceItem.Provider.PUBLIC_DOMAIN_TORRENTS, external_id="42", title="x", item_url="https://pdt/x")
        self.download.torrent = Torrent.objects.create(source=pdt, torrent_url="https://pdt/x.torrent")
        self.download.save()
        calls = self.process(files=[("his_girl_friday.srt", "https://a/own")])
        calls.archive_files.assert_not_called()
        self.assertEqual(self.subtitle.status, "unavailable")

    def test_opensubtitles_entries_are_ranked_by_speed_checked_against_the_running_time_and_rescaled(self):
        def entry(file_id, fps, downloads):
            return {"attributes": {"fps": fps, "download_count": downloads, "moviehash_match": None, "release": f"r{file_id}", "files": [{"file_id": file_id}]}}

        entries = [entry(25, 25.0, 2892), entry(2397, 23.976, 1639), entry(0, 0.0, 1559)]
        # The 23.976 one is for another cut; the one of unknown speed has no link; the 25 fps one fits once rescaled.
        texts = {"https://dl/2397": srt_ending_at(700), "https://dl/25": srt_ending_at(5256)}
        post = lambda url, json, headers: json_response({"link": None if json["file_id"] == 0 else f"https://dl/{json['file_id']}"})  # noqa: E731
        calls = self.process(entries=entries, fetch=lambda url, headers=None: texts[url], post=post)
        self.assertEqual([call.kwargs["json"]["file_id"] for call in calls.post.call_args_list], [2397, 0, 25])
        self.assertEqual(calls.get.call_args.kwargs["params"]["imdb_id"], 32599)
        self.assertEqual((self.subtitle.status, self.subtitle.origin), ("ready", "opensubtitles"))
        stored = calls.upload.call_args.args[0].decode()
        self.assertIn("01:31:20.480 --> 01:31:21.002\nLast", stored)  # 5256 s x 25/23.976

    def test_the_hash_of_the_file_is_sent_and_an_exact_match_is_never_rescaled(self):
        self.download.file_hash = "8e245d9679d31e12"
        self.download.save()
        entries = [{"attributes": {"fps": 25.0, "download_count": 1, "moviehash_match": True, "files": [{"file_id": 7}]}}]
        calls = self.process(entries=entries, fetch=lambda url, headers=None: srt_ending_at(5400))
        self.assertEqual(calls.get.call_args.kwargs["params"]["moviehash"], "8e245d9679d31e12")
        self.assertIn("01:30:00.000 --> 01:30:00.500\nLast", calls.upload.call_args.args[0].decode())

    def test_no_more_than_three_downloads_per_subtitle(self):
        entries = [{"attributes": {"fps": 0, "download_count": 9 - i, "files": [{"file_id": i}]}} for i in range(5)]
        calls = self.process(entries=entries, fetch=lambda url, headers=None: srt_ending_at(100))
        self.assertEqual(calls.post.call_count, 3)
        self.assertEqual(self.subtitle.status, "unavailable")

    def test_a_downloading_film_gets_its_subtitle_at_once_and_lined_up_once_stored(self):
        self.download.status, self.download.duration, self.download.frame_rate = Download.Status.DOWNLOADING, None, None
        self.download.file_size, self.download.buffered_bytes = 1000 * 1024 * 1024, 1024
        self.download.save()
        calls = self.process()
        self.assertEqual(self.subtitle.status, "pending", "nothing of the video yet: looked at again later")
        calls.get.assert_not_called()

        self.download.buffered_bytes = 8 * 1024 * 1024
        self.download.save()
        with tempfile.TemporaryDirectory() as root, override_settings(MOVIES_DOWNLOAD_DIR=root), \
                mock.patch("movies_app.services.media.probe", side_effect=media.MediaError("moov not there yet")) as probe:
            self.process()
            self.process()
        self.assertEqual((self.subtitle.status, probe.call_count), ("pending", 1), "a partial file is not probed again until more of it is there")

        self.download.buffered_bytes += subtitles.PROBE_STEP
        self.download.save()
        info = {"duration": 5504.0, "frame_rate": 25.0, "width": 640, "height": 480, "video_codecs": set(), "audio_codecs": set()}
        entries = [{"attributes": {"fps": 25.0, "download_count": 1, "files": [{"file_id": 7}]}}]
        with tempfile.TemporaryDirectory() as root, override_settings(MOVIES_DOWNLOAD_DIR=root), \
                mock.patch("movies_app.services.media.probe", return_value=info) as probe:
            calls = self.process(entries=entries, fetch=lambda url, headers=None: srt_ending_at(5400))
        self.assertEqual(probe.call_args.args[0], Path(root, self.download.local_path))
        self.assertEqual((self.subtitle.status, self.subtitle.aligned), ("ready", False), "served as it came, lined up later")
        self.assertNotIn("moviehash", calls.get.call_args.kwargs["params"], "the hash needs the whole file")
        self.assertIn("01:30:00.000 --> 01:30:00.500\nLast", calls.upload.call_args.args[0].decode(), "same speed: times kept")
        calls.align.assert_not_called()

        stored = calls.upload.call_args.args[0]
        with mock.patch("movies_app.services.storage.read", return_value=stored):
            calls = self.process(run=lambda subtitle: subtitles.align_pending(), align=shift_by(-6.39))
        calls.align.assert_not_called()
        self.assertFalse(self.subtitle.aligned, "still downloading: the first minutes alone line up on noise")

        self.download.status, self.download.duration, self.download.frame_rate = Download.Status.READY, 5504.0, 25.0
        self.download.save()
        with mock.patch("movies_app.services.storage.read", return_value=stored):
            calls = self.process(run=lambda subtitle: subtitles.align_pending(), align=shift_by(-6.39))
        self.assertEqual(calls.align.call_args.args[0], "https://fs/video.mp4")
        self.assertIn("01:29:53.610 --> 01:29:54.110\nLast", calls.upload.call_args.args[0].decode())
        self.assertTrue(self.subtitle.aligned)

    def test_subtitles_of_a_failed_download_wait_for_the_next_attempt(self):
        self.subtitle.status, self.subtitle.storage_key = Subtitle.Status.READY, "k"
        self.subtitle.save()
        self.download.status = Download.Status.FAILED
        self.download.save()
        calls = self.process(run=lambda subtitle: subtitles.align_pending())
        calls.align.assert_not_called()
        self.assertFalse(self.subtitle.aligned)

    def test_reset_starts_the_subtitles_over_for_another_file(self):
        self.subtitle.status, self.subtitle.storage_key, self.subtitle.aligned = Subtitle.Status.READY, "k", True
        self.subtitle.save()
        with mock.patch("movies_app.services.storage.delete") as delete:
            subtitles.reset(self.movie)
        delete.assert_called_once_with("k")
        self.subtitle.refresh_from_db()
        self.assertEqual((self.subtitle.status, self.subtitle.storage_key, self.subtitle.aligned), ("pending", "", False))

    def test_the_chosen_subtitle_is_lined_up_on_the_sound_track(self):
        entries = [{"attributes": {"fps": 29.97, "download_count": 1, "files": [{"file_id": 7}]}}]
        calls = self.process(entries=entries, fetch=lambda url, headers=None: srt_ending_at(5400), align=shift_by(-6.39))
        self.assertEqual(calls.align.call_args.args[0], "https://fs/video.mp4")
        self.assertEqual(calls.align.side_effect.received, subtitles.to_srt(subtitles.to_vtt(srt_ending_at(5400))), "the candidate, as SubRip")
        stored = calls.upload.call_args.args[0].decode()
        self.assertIn("01:29:53.610 --> 01:29:54.110\nLast", stored)
        self.assertEqual((self.subtitle.status, self.subtitle.aligned), ("ready", True))

    def test_a_failed_alignment_keeps_the_subtitle_as_it_came(self):
        entries = [{"attributes": {"fps": 29.97, "download_count": 1, "files": [{"file_id": 7}]}}]
        calls = self.process(entries=entries, fetch=lambda url, headers=None: srt_ending_at(5400), align=media.MediaError("ffsubsync failed"))
        self.assertIn("01:30:00.000 --> 01:30:00.500\nLast", calls.upload.call_args.args[0].decode())
        self.assertEqual((self.subtitle.status, self.subtitle.aligned), ("ready", True), "not tried again and again")

    def test_vtt_to_srt(self):
        vtt = "WEBVTT\n\nNOTE made by hand\n\n1\n00:00:01.000 --> 00:00:02.500 align:start\nHello\nthere\n\n00:00:03.000 --> 00:00:04.000\nAgain\n\n00:00:05.000 --> 00:00:06.000\n\n"
        self.assertEqual(subtitles.to_srt(vtt), "1\n00:00:01,000 --> 00:00:02,500\nHello\nthere\n\n2\n00:00:03,000 --> 00:00:04,000\nAgain\n")

    def test_a_film_stored_before_its_profile_was_recorded_is_probed_from_storage(self):
        self.download.duration = self.download.frame_rate = None
        self.download.save()
        info = {"duration": 5504.0, "frame_rate": 29.97, "width": 640, "height": 480, "video_codecs": set(), "audio_codecs": set()}
        with mock.patch("movies_app.services.storage.presigned_url", return_value="https://fs/video.mp4"), \
                mock.patch("movies_app.services.media.probe", return_value=info) as probe:
            self.assertEqual(subtitles.video_profile(self.download), {"duration": 5504.0, "frame_rate": 29.97, "file_hash": ""})
        probe.assert_called_once_with("https://fs/video.mp4")
        self.download.refresh_from_db()
        self.assertEqual((self.download.duration, self.download.frame_rate), (5504.0, 29.97))

        self.download.duration = self.download.frame_rate = None
        with mock.patch("movies_app.services.storage.presigned_url", return_value="https://fs/video.mp4"), \
                mock.patch("movies_app.services.media.probe", side_effect=media.MediaError("unreadable")):
            profile = subtitles.video_profile(self.download)
        self.assertEqual(profile, {"duration": None, "frame_rate": None, "file_hash": ""}, "stored but unreadable: matched on the film alone")

    def test_a_failed_download_settles_its_subtitles(self):
        self.download.status = Download.Status.FAILED
        self.download.save()
        self.process()
        self.assertEqual(self.subtitle.status, "unavailable")


class VideoProfileTests(SimpleTestCase):
    def test_probe_reads_the_frame_rate_and_the_running_time(self):
        report = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 640, "height": 480, "avg_frame_rate": "30000/1001"},
                {"codec_type": "audio", "codec_name": "aac", "avg_frame_rate": "0/0"},
            ],
            "format": {"duration": "5504.566000"},
        }
        with mock.patch("movies_app.services.media._run", return_value=SimpleNamespace(stdout=json.dumps(report).encode())):
            info = media.probe(Path("/x/video.mp4"))
        self.assertEqual((info["frame_rate"], info["duration"]), (29.97, 5504.566))
        with mock.patch("movies_app.services.media._run", return_value=SimpleNamespace(stdout=b"{}")):
            info = media.probe(Path("/x/video.mp4"))
        self.assertEqual((info["frame_rate"], info["duration"]), (None, None))

    def test_opensubtitles_hash(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, "video.mp4")
            path.write_bytes((1).to_bytes(8, "little") + bytes(2 * 64 * 1024 - 8))
            self.assertEqual(media.opensubtitles_hash(path), f"{2 * 64 * 1024 + 1:016x}")
            path.write_bytes(bytes(10))
            with self.assertRaises(media.MediaError):
                media.opensubtitles_hash(path)

    def test_alignment_reads_the_offset_ffsubsync_reports(self):
        report = b"INFO score: 16961.000\nINFO offset seconds: -6.390\nINFO framerate scale factor: 0.999\n"
        with tempfile.TemporaryDirectory() as root:
            out = Path(root, "out.srt")

            def run(command, timeout):
                self.assertEqual(command[:2], ["ffsubsync", "https://fs/video.mp4"])
                out.write_text("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
                return SimpleNamespace(stderr=report)

            with mock.patch("movies_app.services.media._run", side_effect=run):
                self.assertEqual(media.align_subtitle("https://fs/video.mp4", Path(root, "in.srt"), out), (-6.39, 0.999))
            with mock.patch("movies_app.services.media._run", return_value=SimpleNamespace(stderr=b"boom")), self.assertRaises(media.MediaError):
                media.align_subtitle("https://fs/video.mp4", Path(root, "in.srt"), out)
            noise = b"INFO score: -12213.000\nINFO offset seconds: 17.170\nINFO framerate scale factor: 0.960\n"
            with mock.patch("movies_app.services.media._run", return_value=SimpleNamespace(stderr=noise)), self.assertRaises(media.MediaError):
                media.align_subtitle("https://fs/video.mp4", Path(root, "in.srt"), out)

    def test_profile_keeps_what_it_could_read(self):
        with tempfile.TemporaryDirectory() as root, mock.patch("movies_app.services.media.probe", side_effect=media.MediaError("bad")):
            path = Path(root, "video.mp4")
            path.write_bytes(bytes(2 * 64 * 1024))
            self.assertEqual(media.video_profile(path), {"duration": None, "frame_rate": None, "file_hash": f"{2 * 64 * 1024:016x}"})


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

    def test_token_must_name_a_real_user_id(self):
        self.assertIsNone(streaming.read_token(streaming.make_token("not-a-uuid", 7), 7))


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


class PurgeTests(TestCase):
    """The monthly purge, run by the worker: `torrent_worker.purge`."""

    def stored_movie(self, title, **download_fields):
        movie = Movie.objects.create(title=title)
        download = Download.objects.create(
            movie=movie, status=Download.Status.READY, storage_key=f"{movie.pk}/video.mp4", storage_size=10,
            completed_at=timezone.now() - timedelta(days=60), **download_fields,
        )
        Rendition.objects.create(download=download, height=480, status=Rendition.Status.READY, storage_key=f"{movie.pk}/video_480p.mp4")
        Subtitle.objects.create(movie=movie, language="en", status=Subtitle.Status.READY, storage_key=f"{movie.pk}/subtitles/en.vtt")
        Subtitle.objects.create(movie=movie, language="fr", status=Subtitle.Status.UNAVAILABLE)
        return movie

    def test_erases_the_video_its_renditions_and_its_subtitles(self):
        from movies_app.management.commands.torrent_worker import purge

        stale = self.stored_movie("Charade")
        Movie.objects.filter(pk=stale.pk).update(last_watched_at=timezone.now() - timedelta(days=31))
        never_watched = self.stored_movie("Nosferatu")
        fresh = self.stored_movie("Metropolis")
        Movie.objects.filter(pk=fresh.pk).update(last_watched_at=timezone.now() - timedelta(days=2))

        with tempfile.TemporaryDirectory() as root, \
                override_settings(MOVIES_DOWNLOAD_DIR=root), \
                mock.patch("movies_app.services.storage.delete") as delete:
            purge()

        deleted = sorted(call.args[0] for call in delete.call_args_list)
        self.assertEqual(deleted, sorted([
            f"{stale.pk}/video.mp4", f"{stale.pk}/video_480p.mp4", f"{stale.pk}/subtitles/en.vtt",
            f"{never_watched.pk}/video.mp4", f"{never_watched.pk}/video_480p.mp4", f"{never_watched.pk}/subtitles/en.vtt",
        ]))
        for movie in (stale, never_watched):
            self.assertFalse(Download.objects.filter(movie=movie).exists())
            self.assertEqual(movie.subtitles.count(), 0, "every subtitle row goes, stored or not")
            self.assertTrue(Movie.objects.filter(pk=movie.pk).exists(), "the catalogue entry stays")
        self.assertTrue(Download.objects.filter(movie=fresh).exists())
        self.assertEqual(fresh.subtitles.count(), 2)
        self.assertEqual(fresh.download.renditions.count(), 1)


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


class RankTests(TestCase):
    def test_each_source_ranks_its_own_items_and_pdt_uses_votes(self):
        PDT = SourceItem.Provider.PUBLIC_DOMAIN_TORRENTS
        catalog.upsert_items([make_item("big", "Big Hit", downloads=1000), make_item("mid", "Mid", downloads=100), make_item("none", "Unknown", downloads=0)])
        catalog.upsert_items([make_item("p1", "Loved", provider=PDT), make_item("p2", "Liked", provider=PDT), make_item("p3", "Obscure", provider=PDT)])
        by_title = {movie.title: movie for movie in Movie.objects.all()}
        Movie.objects.filter(pk=by_title["Loved"].pk).update(vote_count=900)
        Movie.objects.filter(pk=by_title["Liked"].pk).update(vote_count=30)

        catalog.refresh_ranks()

        ranks = {movie.title: movie.rank for movie in Movie.objects.all()}
        # archive.org by downloads, PDT by TMDb votes: the best of each source is on a par.
        self.assertEqual(ranks["Big Hit"], 100.0)
        self.assertEqual(ranks["Loved"], 100.0)
        self.assertAlmostEqual(ranks["Mid"], 200 / 3)
        self.assertAlmostEqual(ranks["Liked"], 200 / 3)
        # No signal at all: unranked, whatever the source.
        self.assertEqual((ranks["Unknown"], ranks["Obscure"]), (0.0, 0.0))

    def test_a_movie_on_two_sources_takes_its_best_rank(self):
        PDT = SourceItem.Provider.PUBLIC_DOMAIN_TORRENTS
        catalog.upsert_items([make_item("a", "Charade", downloads=1), make_item("b", "Zorro", downloads=500)])
        catalog.upsert_items([make_item("p", "Charade", provider=PDT)])
        keep = Movie.objects.get(title="Charade", sources__provider=SourceItem.Provider.ARCHIVE)
        catalog.merge_movies(keep=keep, duplicate=Movie.objects.get(sources__provider=PDT))
        Movie.objects.filter(pk=keep.pk).update(vote_count=50)

        catalog.refresh_ranks()

        keep.refresh_from_db()
        self.assertEqual(keep.rank, 100.0, "last on archive.org, but the only ranked PDT title")


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
