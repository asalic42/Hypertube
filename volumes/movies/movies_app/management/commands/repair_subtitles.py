"""
Rewrite the stored subtitle files with the current WebVTT conversion, or
resolve every subtitle again.

Files converted before the cue times were normalized (two decimals, a comma,
no hours) load in the browser but show no text: the parser drops every
malformed cue. Run once after upgrading; a file already in shape is left alone.

With --refetch, the stored files are erased and every subtitle is looked up
again, matched to its video (same archive.org item, frame rate, running
time): what was fetched before that matching existed may be out of sync.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from movies_app.models import Subtitle
from movies_app.services import storage, subtitles


class Command(BaseCommand):
    help = "Re-normalize the stored subtitle files, or (--refetch) resolve every subtitle again against its video."

    def add_arguments(self, parser):
        parser.add_argument("--refetch", action="store_true", help="Erase the stored subtitles and look them all up again.")

    def handle(self, *args, **options):
        if options["refetch"]:
            self.refetch()
        else:
            self.normalize()

    def refetch(self):
        for key in Subtitle.objects.exclude(storage_key="").values_list("storage_key", flat=True):
            storage.delete(key)
        count = Subtitle.objects.update(status=Subtitle.Status.PENDING, origin="", storage_key="", updated_at=timezone.now())
        self.stdout.write(f"{count} subtitle(s) pending again; the worker resolves them in the background")

    def normalize(self):
        repaired = unchanged = failed = 0
        for subtitle in Subtitle.objects.filter(status=Subtitle.Status.READY).exclude(storage_key=""):
            try:
                data = storage.read(subtitle.storage_key)
                before = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
                after = subtitles.to_vtt(before)
                if after == before:
                    unchanged += 1
                    continue
                storage.upload_bytes(after.encode("utf-8"), subtitle.storage_key, "text/vtt; charset=utf-8")
                repaired += 1
                self.stdout.write(f"repaired {subtitle}")
            except Exception as error:  # one bad file must not stop the others
                failed += 1
                self.stderr.write(f"{subtitle}: {type(error).__name__}: {error}")
        self.stdout.write(f"{repaired} repaired, {unchanged} unchanged, {failed} failed")
