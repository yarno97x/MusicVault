import spotipy
from spotipy.oauth2 import SpotifyOAuth

class Record:
    def __init__(self, uri: str, rating: int = None):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id='5002b6aef6a84ffe88a7688828b7f99c',
            client_secret='12df0a7c77d143499f7c6cc90cbd1f9f',
            redirect_uri='http://127.0.0.1:8888/callback/',
            scope='user-read-playback-state user-modify-playback-state'))
        
        album = self.sp.album(uri)

        self.name = album['name']
        if "(" in self.name:
            self.name = self.name[:self.name.index("(") - 1]
        self.artist = album['artists'][0]['name']
        self.uri = album['uri']
        self.img_url = album['images'][0]['url']
        self.rated = float(rating) if rating is not None else None

    def __repr__(self):
        return f"{self.name} by {self.artist}"
    
    def __str__(self):
        return f"{self.uri}{"" if self.rated is None else f'/{self.rated}'}"
    
    def __hash__(self):
        return hash(self.uri)
    
    def __eq__(self, other):
        return self.uri == other.uri
    
    def get_uri(self):
        return self.uri
    
    def rate(self, value: float):
        self.rated = float(value) if value is not None else None
