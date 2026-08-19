from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

try:
    import libtorrent as lt
except ImportError:  # pragma: no cover - handled explicitly at runtime
    lt = None


BITTORRENT_SOURCE_PAGE = "https://archive.org/details/ElephantsDream"
BITTORRENT_SOURCE_LABEL = "Internet Archive / Elephants Dream"
BITTORRENT_TORRENTS = [
    {
        "identifier": "GrazieNonnaLoverBoy1975FullMovieItalian",
        "title": "Grazie Nonna Lover Boy ( 1975) Full Movie Italian",
        "torrent_url": "https://archive.org/download/GrazieNonnaLoverBoy1975FullMovieItalian/GrazieNonnaLoverBoy1975FullMovieItalian_archive.torrent",
        "file_name": "GrazieNonnaLoverBoy1975FullMovieItalian.mp4",
    },
]
PREFERRED_VIDEO_EXTENSIONS = (".mp4", ".mkv", ".webm", ".ogv", ".avi", ".mov")
NO_PEERS_TIMEOUT_SECONDS = 120
PROGRESS_POLL_INTERVAL_SECONDS = 1


@dataclass
class DownloadJob:
    job_id: str
    identifier: str
    torrent_url: str
    save_path: str
    status: str = "queued"
    progress: float = 0.0
    download_rate: int = 0
    upload_rate: int = 0
    num_peers: int = 0
    error: str | None = None
    message: str | None = None
    file_name: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_DOWNLOAD_JOBS: dict[str, DownloadJob] = {}
_DOWNLOAD_JOBS_LOCK = threading.Lock()


def _read_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"

    with urlopen(url, timeout=20) as response:
        payload = response.read().decode("utf-8")

    return json.loads(payload)


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return value or "download"


def _snapshot_job(job: DownloadJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "identifier": job.identifier,
        "torrent_url": job.torrent_url,
        "save_path": job.save_path,
        "status": job.status,
        "progress": round(job.progress * 100, 2),
        "download_rate": job.download_rate,
        "upload_rate": job.upload_rate,
        "num_peers": job.num_peers,
        "error": job.error,
        "message": job.message,
        "file_name": job.file_name,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _store_job(job: DownloadJob) -> None:
    job.updated_at = time.time()
    with _DOWNLOAD_JOBS_LOCK:
        _DOWNLOAD_JOBS[job.job_id] = job


def _get_job(job_id: str) -> DownloadJob:
    with _DOWNLOAD_JOBS_LOCK:
        job = _DOWNLOAD_JOBS.get(job_id)

    if job is None:
        raise KeyError(job_id)

    return job

def _get_jobs() -> list[DownloadJob]:
    with _DOWNLOAD_JOBS_LOCK:
        return list(_DOWNLOAD_JOBS.values())


def _require_libtorrent() -> None:
    if lt is None:
        raise RuntimeError(
            "libtorrent n'est pas installé. Ajoute la dépendance au runtime du service avant d'utiliser BitTorrent."
        )


def build_archive_torrent_url(identifier: str) -> str:
    return _find_movie_source(identifier)["torrent_url"]


def _find_movie_source(identifier: str) -> dict[str, Any]:
    for source in BITTORRENT_TORRENTS:
        if source["identifier"] == identifier:
            return source

    raise ValueError(f"Aucune source BitTorrent connue pour {identifier}")


def start_archive_video_download(identifier: str, destination_dir: str | os.PathLike[str]) -> dict[str, Any]:
    resolved = resolve_archive_video(identifier)
    torrent_url = resolved["torrent_url"]
    save_path = str(Path(destination_dir))

    job = DownloadJob(
        job_id=uuid.uuid4().hex,
        identifier=identifier,
        torrent_url=torrent_url,
        save_path=save_path,
        status="starting",
        file_name=resolved.get("file_name"),
    )
    _store_job(job)

    thread = threading.Thread(
        target=_run_archive_video_download,
        args=(job.job_id,),
        daemon=True,
    )
    thread.start()

    return {
        **resolved,
        **_snapshot_job(job),
    }


def _run_archive_video_download(job_id: str) -> None:
    """ 
        Lance le téléchargement BitTorrent dans un thread séparé et met à jour l'état du job.
    """
    try:
        _require_libtorrent()
        job = _get_job(job_id)
        job.status = "downloading"
        job.message = "Connexion au swarm BitTorrent en cours."
        _store_job(job)

        destination_path = Path(job.save_path)
        destination_path.mkdir(parents=True, exist_ok=True)

        with urlopen(job.torrent_url, timeout=30) as response:
            torrent_payload = response.read()

        torrent_info = lt.torrent_info(lt.bdecode(torrent_payload))
        session = lt.session({"listen_interfaces": "0.0.0.0:6881"})
        handle = session.add_torrent(
            {
                "save_path": str(destination_path),
                "storage_mode": lt.storage_mode_t.storage_mode_sparse,
                "ti": torrent_info,
            }
        )

        waiting_since: float | None = None

        while True:
            status = handle.status()
            job = _get_job(job_id)
            job.progress = float(status.progress)
            job.download_rate = int(status.download_rate)
            job.upload_rate = int(status.upload_rate)
            job.num_peers = int(status.num_peers)

            if status.progress >= 1.0:
                job.status = "completed"
                job.message = "Téléchargement terminé."
                _store_job(job)
                break

            if status.num_peers == 0:
                if waiting_since is None:
                    waiting_since = time.time()
                elapsed = int(time.time() - waiting_since)
                job.status = "waiting_for_peers"
                job.message = f"Aucun pair connecté pour le moment. Attente depuis {elapsed}s."
                if elapsed >= NO_PEERS_TIMEOUT_SECONDS:
                    job.status = "failed"
                    job.error = "Aucun pair BitTorrent disponible pour ce torrent."
                    job.message = "Le swarm ne contient aucun pair actif. Essaie un autre item ou réessaie plus tard."
                    _store_job(job)
                    break
            else:
                waiting_since = None
                job.status = "downloading"
                job.message = "Téléchargement en cours."

            _store_job(job)

            time.sleep(PROGRESS_POLL_INTERVAL_SECONDS)

        if _get_job(job_id).status == "completed":
            job = _get_job(job_id)
            job.progress = 1.0
            job.file_name = torrent_info.name()
            _store_job(job)
    except Exception as error:  # pragma: no cover - surfaced through the progress endpoint
        try:
            job = _get_job(job_id)
        except KeyError:
            return

        job.status = "failed"
        job.error = str(error)
        job.message = "Le téléchargement BitTorrent a échoué."
        _store_job(job)


def search_archive_catalog(query: str = "", limit: int = 5) -> list[dict[str, Any]]:
    parts = ["mediatype:movies", 'format:"Archive BitTorrent"']
    results: list[dict[str, Any]] = []
    needle = query.strip().lower()

    for source in BITTORRENT_TORRENTS:
        if needle and needle not in source["title"].lower() and needle not in source["identifier"].lower():
            continue

        results.append(
            {
                "identifier": source["identifier"],
                "title": source["title"],
                "downloads": 0,
                "format": "application/x-bittorrent",
                "item_url": BITTORRENT_SOURCE_PAGE,
                "metadata_url": BITTORRENT_SOURCE_PAGE,
                "torrent_url": source["torrent_url"],
                "source_label": BITTORRENT_SOURCE_LABEL,
            }
        )

        if len(results) >= limit:
            break

    return results


def resolve_archive_video(identifier: str) -> dict[str, Any]:
    source = _find_movie_source(identifier)
    return {
        "identifier": source["identifier"],
        "file_name": source["file_name"],
        "download_url": source["torrent_url"],
        "size": None,
        "format": "application/x-bittorrent",
        "torrent_url": source["torrent_url"],
        "source_label": BITTORRENT_SOURCE_LABEL,
        "item_url": BITTORRENT_SOURCE_PAGE,
        "metadata_url": BITTORRENT_SOURCE_PAGE,
    }


def download_http_file(url: str, destination_dir: str | os.PathLike[str], file_name: str | None = None) -> dict[str, Any]:
    destination_path = Path(destination_dir)
    destination_path.mkdir(parents=True, exist_ok=True)

    if file_name is None:
        file_name = _safe_filename(Path(url).name or "download")
    else:
        file_name = _safe_filename(file_name)

    target_path = destination_path / file_name

    with urlopen(url, timeout=30) as response, target_path.open("wb") as output_file:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output_file.write(chunk)

    return {
        "file_name": file_name,
        "saved_path": str(target_path),
        "size": target_path.stat().st_size,
    }


def download_torrent_file(torrent_url: str, destination_dir: str | os.PathLike[str]) -> dict[str, Any]:
    _require_libtorrent()

    destination_path = Path(destination_dir)
    destination_path.mkdir(parents=True, exist_ok=True)

    with urlopen(torrent_url, timeout=30) as response:
        torrent_payload = response.read()

    print(f"Téléchargement du torrent depuis {torrent_url} vers {destination_path}")

    torrent_info = lt.torrent_info(lt.bdecode(torrent_payload))
    session = lt.session({"listen_interfaces": "0.0.0.0:6881"})
    handle = session.add_torrent(
        {
            "save_path": str(destination_path),
            "storage_mode": lt.storage_mode_t.storage_mode_sparse,
            "ti": torrent_info,
        }
    )

    while True:
        status = handle.status()
        print(
            f"Progression: {status.progress * 100:.2f}% | "
            f"Taux de téléchargement: {status.download_rate / 1000:.2f} kB/s | "
            f"Taux d'upload: {status.upload_rate / 1000:.2f} kB/s | "
            f"Pairs: {status.num_peers}"
        )
        if status.progress >= 1.0:
            break

        time.sleep(1)

    return {
        "torrent_url": torrent_url,
        "save_path": str(destination_path),
        "name": torrent_info.name(),
        "progress": 1.0,
    }


def get_archive_download_progress(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    return _snapshot_job(job)


def download_archive_video(identifier: str, destination_dir: str | os.PathLike[str]) -> dict[str, Any]:
    resolved = resolve_archive_video(identifier)
    downloaded = download_torrent_file(
        resolved["torrent_url"],
        destination_dir,
    )

    return {
        **resolved,
        **downloaded,
    }