import os
import sys
import base64
import time
from urllib.parse import quote, urlsplit, urlunsplit
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
RT_ADDRESS        = os.getenv("RT_ADDRESS", "scgi://127.0.0.1:5000")
RT_TIMEOUT        = float(os.getenv("RT_TIMEOUT", "5.0"))
RT_USERNAME       = os.getenv("RT_USERNAME", "")
RT_PASSWORD       = os.getenv("RT_PASSWORD", "")
RT_RETRY_ATTEMPTS = max(1, int(os.getenv("RT_RETRY_ATTEMPTS", "6")))
RT_RETRY_DELAY    = max(0.0, float(os.getenv("RT_RETRY_DELAY", "1.0")))
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


# ─── rTorrent ────────────────────────────────────────────────────

class RTorrentClient(TorrentClient):
    def __init__(self, address: str, timeout: float):
        from rtorrent_rpc import RTorrent  # type: ignore[import-not-found]
        self._client = RTorrent(address=address, timeout=timeout)
        self._address = redact_auth_in_address(address)
        configure_rtorrent_http_basic_auth(self._client, address)

    def connect(self) -> None:
        try:
            # Trigger one lightweight call to validate connectivity.
            self._client.system_list_methods()
        except Exception as e:
            print(f"[ERREUR] Connexion échouée : {e}")
            sys.exit(1)
        print(f"[INFO] Connecté à rTorrent ({self._address})")

    def disconnect(self) -> None:
        pass  # rtorrent-rpc n'a pas de logout explicite

    def get_torrents(self) -> list:
        # Keep hashes as torrent handles to avoid extra object wrappers.
        return self._client.download_list()

    def get_torrent_name(self, torrent) -> str:
        return self._client.d.name(torrent)

    def get_tracker_urls(self, torrent) -> list[str]:
        trackers = self._client.t.multicall(torrent, "", "t.url=")
        return [t[0] for t in trackers if t and t[0]]

    def add_trackers(self, torrent, urls: list[str]) -> None:
        for url in urls:
            self._client.d_add_tracker(torrent, url)

    def remove_tracker(self, torrent, url: str) -> None:
        # rTorrent XML-RPC does not expose hard tracker deletion reliably,
        # so we disable matching trackers instead.
        trackers = self._client.t.multicall(torrent, "", "t.is_enabled=", "t.url=")
        for idx, tracker in enumerate(trackers):
            if len(tracker) >= 2 and tracker[1] == url and tracker[0]:
                self._client.t_disable_tracker(torrent, idx)


# ─── Helpers ──────────────────────────────────────────────────────

def build_client() -> TorrentClient:
    if CLIENT_TYPE == "qbittorrent":
        return QBittorrentClient(QB_HOST, QB_USERNAME, QB_PASSWORD)
    if CLIENT_TYPE == "transmission":
        return TransmissionClient(TR_HOST, TR_USERNAME, TR_PASSWORD)
    if CLIENT_TYPE == "rtorrent":
        return RTorrentClient(RT_ADDRESS, RT_TIMEOUT)
    print(f"[ERREUR] Client inconnu : {CLIENT_TYPE}")
    sys.exit(1)


def with_http_basic_auth(address: str) -> str:
    parsed = urlsplit(address)
    if parsed.scheme not in {"http", "https"}:
        return address

    if parsed.username or not RT_USERNAME:
        return address

    auth = quote(RT_USERNAME, safe="")
    if RT_PASSWORD:
        auth = f"{auth}:{quote(RT_PASSWORD, safe='')}"

    netloc = f"{auth}@{parsed.hostname or ''}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def configure_rtorrent_http_basic_auth(client, address: str) -> None:
    parsed = urlsplit(address)
    if parsed.scheme not in {"http", "https"} or not RT_USERNAME:
        return

    transport = getattr(client, "_transport", None)
    pool = getattr(transport, "_pool", None)
    if transport is None or pool is None:
        return

    path = parsed.path or "/RPC2"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    token = base64.b64encode(f"{RT_USERNAME}:{RT_PASSWORD}".encode("utf-8")).decode("ascii")

    def request_with_basic_auth(body: bytes, content_type: str | None = None) -> bytes:
        transient_status = {429, 500, 502, 503, 504}

        for attempt in range(1, RT_RETRY_ATTEMPTS + 1):
            headers = {"authorization": f"Basic {token}"}
            if content_type:
                headers["content-type"] = content_type

            try:
                res = pool.request(
                    method="POST",
                    url=path,
                    body=body,
                    redirect=False,
                    headers=headers,
                )
            except Exception as e:
                if attempt == RT_RETRY_ATTEMPTS:
                    raise RuntimeError(f"échec après {attempt} tentative(s): {e}") from e

                delay = RT_RETRY_DELAY * (2 ** (attempt - 1))
                print(f"[RETRY] rTorrent requête échouée ({e}) — tentative {attempt}/{RT_RETRY_ATTEMPTS}, pause {delay:.1f}s")
                time.sleep(delay)
                continue

            res_body = res.data
            if res.status in (200, 204):
                return res_body

            if res.status in transient_status and attempt < RT_RETRY_ATTEMPTS:
                delay = RT_RETRY_DELAY * (2 ** (attempt - 1))
                print(f"[RETRY] rTorrent HTTP {res.status} — tentative {attempt}/{RT_RETRY_ATTEMPTS}, pause {delay:.1f}s")
                time.sleep(delay)
                continue

            raise RuntimeError(f"unexpected response status code {res.status} {res_body!r}")

        raise RuntimeError("rTorrent: échec de requête après retries")

    transport.request = request_with_basic_auth


def redact_auth_in_address(address: str) -> str:
    parsed = urlsplit(address)
    if not parsed.username:
        return address

    # Keep username visible for diagnostics while hiding secret.
    username = parsed.username
    host = parsed.hostname or ""
    netloc = f"{username}:***@{host}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


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