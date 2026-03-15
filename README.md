# YGG to U2P

<sub>(⭐ Si ce projet vous a été utile, pensez à lui laisser une star !)</sub>

Script Python pour remplacer automatiquement les trackers ciblés par une liste de trackers publics sur vos torrents, compatible **qBittorrent**, **Transmission** et **rTorrent**.

## Pourquoi ce projet

Ce projet a été créé dans le contexte de la migration post-hack de l'écosystème Ygg, afin d'aider à maintenir les torrents disponibles via des trackers publics.

L'idée : ajouter une liste de trackers publics à vos torrents et supprimer les anciens trackers ciblés pour réduire la dépendance à un tracker unique.

## Ce que fait le script

Le script :

1. Charge une liste de trackers depuis `trackers.txt`
2. Se connecte à l'API de votre client torrent (qBittorrent, Transmission ou rTorrent)
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
| rTorrent | `rtorrent-rpc` | `rtorrent` |

## Prérequis

- Python 3.10+
- qBittorrent avec l'interface Web activée **ou** Transmission avec accès RPC **ou** rTorrent avec XML-RPC (SCGI socket unix, socket TCP, HTTP /RPC2)
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
- `rtorrent-rpc`
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

# rTorrent
# Exemples:
#   scgi tcp     -> scgi://127.0.0.1:5000
#   socket unix  -> scgi:///dev/shm/rtorrent.sock
#   nginx /RPC2  -> http://localhost:5000/RPC2
RT_ADDRESS=scgi://127.0.0.1:5000
RT_TIMEOUT=5.0
RT_USERNAME=
RT_PASSWORD=
RT_RETRY_ATTEMPTS=6
RT_RETRY_DELAY=1.0

TRACKERS_FILE=trackers.txt
```

### Variables disponibles

| Variable | Description | Par défaut |
|---|---|---|
| `CLIENT_TYPE` | Client torrent à utiliser (`qbittorrent`, `transmission` ou `rtorrent`) | `qbittorrent` |
| `QB_HOST` | URL de l'interface Web qBittorrent | `http://localhost:8080` |
| `QB_USERNAME` | Utilisateur qBittorrent | `admin` |
| `QB_PASSWORD` | Mot de passe qBittorrent | `adminadmin` |
| `TR_HOST` | URL de l'interface RPC Transmission | `http://localhost:9091` |
| `TR_USERNAME` | Utilisateur Transmission | `admin` |
| `TR_PASSWORD` | Mot de passe Transmission | `admin` |
| `RT_ADDRESS` | Adresse rtorrent-rpc (`scgi://...`, `scgi:///...sock`, `http(s)://.../RPC2`) | `scgi://127.0.0.1:5000` |
| `RT_TIMEOUT` | Timeout réseau rtorrent-rpc (secondes) | `5.0` |
| `RT_USERNAME` | Utilisateur HTTP Basic optionnel pour `RT_ADDRESS` en `http(s)` | vide |
| `RT_PASSWORD` | Mot de passe HTTP Basic optionnel pour `RT_ADDRESS` en `http(s)` | vide |
| `RT_RETRY_ATTEMPTS` | Nombre de tentatives en cas d'erreur HTTP transitoire rTorrent (`429/500/502/503/504`) | `6` |
| `RT_RETRY_DELAY` | Délai initial entre retries rTorrent (secondes, backoff exponentiel) | `1.0` |
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
- **Client inconnu** : vérifier que `CLIENT_TYPE` vaut `qbittorrent`, `transmission` ou `rtorrent`.
- **rTorrent /RPC2** : utiliser une URL complète dans `RT_ADDRESS` (ex: `http://127.0.0.1:5000/RPC2`). La librairie supporte HTTP(S) et utilise `/RPC2` par défaut si aucun chemin n'est fourni.
- **rTorrent auth_basic nginx** : privilégier `RT_USERNAME` + `RT_PASSWORD` avec une `RT_ADDRESS` sans credentials (ex: `http://127.0.0.1:5000/RPC2`) pour éviter les problèmes d'encodage des caractères spéciaux.
- **rTorrent suppression tracker** : si de retry apparaissent ils sont probablement dû à un ulimit trop faible par défaut à 1024. Exemple avec docker compose pour augmenter la limite:
```yaml
    ulimits:
      nofile:
        soft: 8192
        hard: 8192
```
- **Fichier trackers introuvable** : vérifier `TRACKERS_FILE` et l'emplacement de `trackers.txt`.
- **Aucun tracker ajouté** : possible si les torrents ne contiennent aucun des domaines ciblés, ou s'ils sont déjà à jour.
