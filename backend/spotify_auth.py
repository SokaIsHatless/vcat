import os
import webbrowser
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

SCOPES = "user-modify-playback-state user-read-playback-state"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
CACHE_PATH = "spotify_token.json"


def get_spotify_token():
    auth_manager = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_path=CACHE_PATH,
        open_browser=False,
    )
    token_info = auth_manager.get_cached_token()
    if not token_info:
        auth_url = auth_manager.get_authorize_url()
        print(f"Opening browser for Spotify authorization...")
        webbrowser.open(auth_url)
        response_url = input("Paste the redirect URL here: ").strip()
        code = auth_manager.parse_response_code(response_url)
        token_info = auth_manager.get_access_token(code, as_dict=True, check_cache=False)
    elif auth_manager.is_token_expired(token_info):
        token_info = auth_manager.refresh_access_token(token_info["refresh_token"])
    return token_info["access_token"]


if __name__ == "__main__":
    token = get_spotify_token()
    print(f"Access token: {token[:40]}...")
    print("Spotify auth successful!")
