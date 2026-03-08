import os
import sys
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

CLIENT_TYPE       = os.getenv("CLIENT_TYPE", "qbittorrent")
QB_HOST           = os.getenv("QB_HOST", "http://localhost:8080")
QB_USERNAME       = os.getenv("QB_USERNAME", "admin")
QB_PASSWORD       = os.getenv("QB_PASSWORD", "adminadmin")
TR_HOST           = os.getenv("TR_HOST", "http://localhost:9091")
TR_USERNAME       = os.getenv("TR_USERNAME", "admin")
TR_PASSWORD       = os.getenv("TR_PASSWORD", "admin")
TRACKERS_FILE     = os.getenv("TRACKERS_FILE", "trackers.txt")
TARGET_DOMAINS    = [
    "gopeers.cc",
    "p2p-world.net",
    "p2p-protocol.org",
    "p2pconnect.net",
    "drago-server.org",
    "drago-tracker.cc",
    "joinpeers.org",
    "maxp2p.org",
    "p2p-tracker.net",
    "p2ptracker.cc",
    "yggtracking.org",
    "supertracker.org",
    "yggshare.org",
    "loadpeers.org",
]


# ─── Abstract base ────────────────────────────────────────────────

class TorrentClient(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def get_torrents(self) -> list: ...

    @abstractmethod
    def get_torrent_name(self, torrent) -> str: ...

    @abstractmethod
    def get_tracker_urls(self, torrent) -> list[str]: ...

    @abstractmethod
    def add_trackers(self, torrent, urls: list[str]) -> None: ...

    @abstractmethod
    def remove_tracker(self, torrent, url: str) -> None: ...


# ─── qBittorrent ──────────────────────────────────────────────────

class QBittorrentClient(TorrentClient):
    def __init__(self, host: str, username: str, password: str):
        import qbittorrentapi
        self._client = qbittorrentapi.Client(
            host=host, username=username, password=password,
        )
        self._host = host

    def connect(self) -> None:
        import qbittorrentapi
        try:
            self._client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            print(f"[ERREUR] Connexion échouée : {e}")
            sys.exit(1)
        print(f"[INFO] Connecté à qBittorrent ({self._host})")

    def disconnect(self) -> None:
        self._client.auth_log_out()

    def get_torrents(self) -> list:
        return self._client.torrents_info()

    def get_torrent_name(self, torrent) -> str:
        return torrent.name

    def get_tracker_urls(self, torrent) -> list[str]:
        return [
            t.url for t in torrent.trackers
            if t.url and not t.url.startswith("**")
        ]

    def add_trackers(self, torrent, urls: list[str]) -> None:
        torrent.add_trackers(urls=urls)

    def remove_tracker(self, torrent, url: str) -> None:
        torrent.remove_trackers(urls=[url])


# ─── Transmission ─────────────────────────────────────────────────

class TransmissionClient(TorrentClient):
    def __init__(self, host: str, username: str, password: str):
        from urllib.parse import urlparse
        parsed = urlparse(host)
        self._host = host
        self._kwargs = dict(
            host=parsed.hostname or "localhost",
            port=parsed.port or 9091,
            username=username,
            password=password,
        )

    def connect(self) -> None:
        from transmission_rpc import Client as TrClient
        try:
            self._client = TrClient(**self._kwargs)
        except Exception as e:
            print(f"[ERREUR] Connexion échouée : {e}")
            sys.exit(1)
        print(f"[INFO] Connecté à Transmission ({self._host})")

    def disconnect(self) -> None:
        pass  # transmission-rpc n'a pas de logout explicite

    def get_torrents(self) -> list:
        return self._client.get_torrents()

    def get_torrent_name(self, torrent) -> str:
        return torrent.name

    def get_tracker_urls(self, torrent) -> list[str]:
        return [t.announce for t in torrent.trackers if t.announce]

    def add_trackers(self, torrent, urls: list[str]) -> None:
        for url in urls:
            self._client.change_torrent(torrent.id, tracker_add=[url])

    def remove_tracker(self, torrent, url: str) -> None:
        tracker_id = next(
            (t.id for t in torrent.trackers if t.announce == url), None
        )
        if tracker_id is not None:
            self._client.change_torrent(torrent.id, tracker_remove=[tracker_id])


# ─── Helpers ──────────────────────────────────────────────────────

def build_client() -> TorrentClient:
    if CLIENT_TYPE == "qbittorrent":
        return QBittorrentClient(QB_HOST, QB_USERNAME, QB_PASSWORD)
    if CLIENT_TYPE == "transmission":
        return TransmissionClient(TR_HOST, TR_USERNAME, TR_PASSWORD)
    print(f"[ERREUR] Client inconnu : {CLIENT_TYPE}")
    sys.exit(1)


def load_trackers(filepath: str) -> list[str]:
    if not os.path.exists(filepath):
        print(f"[ERREUR] Fichier introuvable : {filepath}")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        trackers = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

    if not trackers:
        print("[ERREUR] Le fichier de trackers est vide.")
        sys.exit(1)

    print(f"[INFO] {len(trackers)} tracker(s) chargé(s) depuis '{filepath}'")
    return trackers


# ─── Main ─────────────────────────────────────────────────────────

def main():
    new_trackers = load_trackers(TRACKERS_FILE)
    client = build_client()
    client.connect()

    torrents = client.get_torrents()
    print(f"[INFO] {len(torrents)} torrent(s) trouvé(s)\n")

    updated   = 0
    skipped   = 0
    no_target = 0

    for torrent in torrents:
        name = client.get_torrent_name(torrent)
        tracker_urls = client.get_tracker_urls(torrent)

        # Est-ce que ce torrent a un tracker ciblé ?
        if not any(any(domain in url for domain in TARGET_DOMAINS) for url in tracker_urls):
            print(f"[IGNORÉ]  {name} — pas de tracker ciblé")
            no_target += 1
            continue

        # Trackers manquants uniquement
        current_set = set(tracker_urls)
        missing = [t for t in new_trackers if t not in current_set]

        if missing:
            client.add_trackers(torrent, missing)
            print(f"[MODIFIÉ] {name} — {len(missing)} tracker(s) ajouté(s)")

        # Supprime les trackers ciblés
        to_remove = [url for url in tracker_urls if any(domain in url for domain in TARGET_DOMAINS)]
        for url in to_remove:
            client.remove_tracker(torrent, url)

        if not missing and not to_remove:
            print(f"[OK]      {name} — déjà à jour")
            skipped += 1
            continue

        if to_remove:
            print(f"[NETTOYÉ] {name} — {len(to_remove)} tracker(s) ciblé(s) supprimé(s)")

        updated += 1

    client.disconnect()

    print(f"\n--- Résumé ---")
    print(f"  Mis à jour          : {updated}")
    print(f"  Déjà à jour         : {skipped}")
    print(f"  Sans tracker ciblé  : {no_target}")


if __name__ == "__main__":
    main()