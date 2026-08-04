"""Helpers minimales pour rechercher et télécharger du contenu légal depuis Internet Archive.

Ce module remplace l'ancien prototype torrent. Il ne lance aucune action à l'import.
"""

from pathlib import Path

from api.services.archive import download_archive_video, search_archive_catalog


def search_top_medias(limit: int = 5):
    return search_archive_catalog(limit=limit)


def rechercher_films(mots_cles: str, limite: int = 5):
    return search_archive_catalog(query=mots_cles, limit=limite)


def telecharger_depuis_identifiant(identifier: str, dossier_destination: str = "./downloads"):
    return download_archive_video(identifier, dossier_destination)


if __name__ == "__main__":
    catalogue = search_top_medias(limit=5)
    for item in catalogue:
        print(f"{item['title']} -> {item['identifier']}")

    if catalogue:
        print("Exemple de téléchargement possible:")
        print(telecharger_depuis_identifiant(catalogue[0]["identifier"], str(Path("./downloads"))))