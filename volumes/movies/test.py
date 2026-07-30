import requests

torrents = []

def rechercher_films_torrent(mots_cles, limite=5):
    # Encodage de la requête de recherche avancée
    url_api = "https://archive.org/advancedsearch.php"
    
    requete = f'{mots_cles} AND mediatype:movies AND format:"Archive BitTorrent"'
    
    parametres = {
        'q': requete,
        'fl[]': ['identifier', 'title', 'downloads'],
        'sort[]': 'downloads desc',
        'rows': limite,
        'output': 'json'
    }
    
    reponse = requests.get(url_api, params=parametres)
    
    if reponse.status_code == 200:
        donnees = reponse.json()
        documents = donnees.get('response', {}).get('docs', [])
        
        print(f"--- Résultats pour '{mots_cles}' ({len(documents)} trouvés) ---\n")
        for doc in documents:
            identifiant = doc.get('identifier')
            titre = doc.get('title')
            telechargements = doc.get('downloads', 0)
            
            # Reconstruction du lien torrent normalisé
            url_torrent = f"https://archive.org/download/{identifiant}/{identifiant}_archive.torrent"
            torrents.append(url_torrent)
            
            print(f"Film : {titre}")
            print(f"ID IA : {identifiant}")
            print(f"Téléchargements : {telechargements}")
            print(f"Lien Torrent : {url_torrent}")
            print("-" * 40)
    else:
        print(f"Erreur lors de la requête : {reponse.status_code}")

# Exemple d'utilisation avec le mot-clé "Sherlock"
rechercher_films_torrent("Sherlock", limite=3)

import time
import requests
import libtorrent as lt

def telecharger_depuis_torrent(url_torrent, dossier_destination="."):
    """
    Télécharge un film à partir d'une URL de fichier .torrent de l'Internet Archive.
    """
    print(f"Récupération du fichier torrent : {url_torrent}")
    
    # 1. Téléchargement du fichier .torrent en mémoire
    reponse = requests.get(url_torrent)
    if reponse.status_code != 200:
        print("Impossible de récupérer le fichier .torrent.")
        return False

    # 2. Initialisation de la session BitTorrent
    session = lt.session({'listen_interfaces': '0.0.0.0:6881'})
    
    # 3. Chargement des données du torrent
    metadonnees = lt.bdecode(reponse.content)
    infos_torrent = lt.torrent_info(metadonnees)
    
    # 4. Configuration des paramètres de téléchargement
    parametres = {
        'save_path': dossier_destination,
        'storage_mode': lt.storage_mode_t.storage_mode_sparse,
        'ti': infos_torrent
    }
    
    # Ajout du torrent à la session
    gestionnaire = session.add_torrent(parametres)
    print(f"Début du téléchargement : {gestionnaire.status().name}")
    
    # 5. Boucle de suivi de la progression
    while not gestionnaire.status().is_seeding:
        statut = gestionnaire.status()
        
        # Calcul du pourcentage et de la vitesse de téléchargement
        progression = statut.progress * 100
        vitesse_dl = statut.download_rate / 1000  # Conversion en kB/s
        pairs = statut.num_peers
        
        # Affichage dynamique sur une seule ligne (\r)
        print(f"\rProgression : {progression:.2f}% | Vitesse : {vitesse_dl:.1f} kB/s | Pairs : {pairs}", end="")
        
        time.sleep(1)
        
    print("\nTéléchargement terminé avec succès !")
    return True

# --- EXEMPLE D'UTILISATION ---
url_exemple = "https://archive.org/download/lost_world/lost_world_archive.torrent"

# Lancement du téléchargement dans le dossier actuel
for torrent in torrents:
    telecharger_depuis_torrent(torrent, dossier_destination=".")