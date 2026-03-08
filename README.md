# YGG to U2P

<sub>(⭐ Si ce projet vous a été utile, pensez à lui laisser une star !)</sub>

Script Python pour remplacer automatiquement les trackers ciblés par une liste de trackers publics sur vos torrents, compatible **qBittorrent** et **Transmission**.

## Pourquoi ce projet

Ce projet a été créé dans le contexte de la migration post-hack de l'écosystème Ygg, afin d'aider à maintenir les torrents disponibles via des trackers publics.

L'idée : ajouter une liste de trackers publics à vos torrents et supprimer les anciens trackers ciblés pour réduire la dépendance à un tracker unique.

## Ce que fait le script

Le script :

1. Charge une liste de trackers depuis `trackers.txt`
2. Se connecte à l'API de votre client torrent (qBittorrent ou Transmission)
3. Parcourt tous les torrents
4. Ne traite **que** les torrents qui possèdent déjà un tracker d'un des domaines ciblés
5. Ajoute uniquement les trackers manquants (pas de doublons)
6. Supprime les trackers correspondant aux domaines ciblés
7. Affiche un résumé final

## Clients supportés

| Client | Bibliothèque | Variable `CLIENT_TYPE` |
|---|---|---|
| qBittorrent | `qbittorrent-api` | `qbittorrent` (par défaut) |
| Transmission | `transmission-rpc` | `transmission` |

## Prérequis

- Python 3.10+
- qBittorrent avec l'interface Web activée **ou** Transmission avec accès RPC
- Accès API (hôte, login, mot de passe)

## Installation

1. Cloner / copier le projet
2. Installer les dépendances :

```bash
pip install -r requirements.txt
```

Le fichier `requirements.txt` contient :

- `qbittorrent-api`
- `transmission-rpc`
- `python-dotenv`

## Configuration

Le script lit des variables d'environnement (via `.env` si présent).

Créer un fichier `.env` à la racine :

```env
CLIENT_TYPE=qbittorrent

# qBittorrent
QB_HOST=http://localhost:8080
QB_USERNAME=admin
QB_PASSWORD=adminadmin

# Transmission
TR_HOST=http://localhost:9091
TR_USERNAME=admin
TR_PASSWORD=admin

TRACKERS_FILE=trackers.txt
```

### Variables disponibles

| Variable | Description | Par défaut |
|---|---|---|
| `CLIENT_TYPE` | Client torrent à utiliser (`qbittorrent` ou `transmission`) | `qbittorrent` |
| `QB_HOST` | URL de l'interface Web qBittorrent | `http://localhost:8080` |
| `QB_USERNAME` | Utilisateur qBittorrent | `admin` |
| `QB_PASSWORD` | Mot de passe qBittorrent | `adminadmin` |
| `TR_HOST` | URL de l'interface RPC Transmission | `http://localhost:9091` |
| `TR_USERNAME` | Utilisateur Transmission | `admin` |
| `TR_PASSWORD` | Mot de passe Transmission | `admin` |
| `TRACKERS_FILE` | Chemin du fichier de trackers | `trackers.txt` |

Si une variable est absente, le script utilise les valeurs par défaut.

## Liste de trackers

La liste des trackers publics se trouve dans `trackers.txt`.

Règles de lecture :

- lignes vides ignorées
- lignes commençant par `#` ignorées

## Exécution

```bash
python main.py
```

Sortie attendue :

- connexion au client torrent
- nombre de torrents trouvés
- statut par torrent (`[MODIFIÉ]`, `[NETTOYÉ]`, `[OK]`, `[IGNORÉ]`)
- résumé final

## Important

Le filtrage des torrents est actuellement basé sur les domaines :

- `p2p-world.net`
- `p2p-protocol.org`
- `p2pconnect.net`
- `drago-server.org`
- `drago-tracker.cc`
- `joinpeers.org`
- `maxp2p.org`
- `p2p-tracker.net`
- `p2ptracker.cc`
- `yggtracking.org`
- `supertracker.org`
- `yggshare.org`
- `loadpeers.org`

Ces domaines sont définis en dur dans `main.py` via `TARGET_DOMAINS`.

Si vous voulez cibler d'autres domaines/anciens trackers, modifiez cette liste.

## Dépannage rapide

- **Erreur de connexion** : vérifier les variables d'hôte, utilisateur et mot de passe de votre client, et l'activation de l'API (WebUI pour qBittorrent, RPC pour Transmission).
- **Client inconnu** : vérifier que `CLIENT_TYPE` vaut `qbittorrent` ou `transmission`.
- **Fichier trackers introuvable** : vérifier `TRACKERS_FILE` et l'emplacement de `trackers.txt`.
- **Aucun tracker ajouté** : possible si les torrents ne contiennent aucun des domaines ciblés, ou s'ils sont déjà à jour.
