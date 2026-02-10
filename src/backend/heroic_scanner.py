import os
import json

class HeroicScanner:
    def __init__(self):
        self.heroic_config_paths = [
            os.path.expanduser("~/.config/heroic"),
            os.path.expanduser("~/.var/app/com.heroicgameslauncher.hgl/config/heroic")
        ]

    def _get_active_config_path(self, subpath):
        for path in self.heroic_config_paths:
            full_path = os.path.join(path, subpath)
            if os.path.exists(full_path):
                return full_path
        return None

    def scan_games(self):
        games = []
        games.extend(self._scan_legendary())
        games.extend(self._scan_gog())
        # games.extend(self._scan_nile()) # Amazon, if needed
        return games

    def _scan_legendary(self):
        # Epic Games (via Legendary)
        installed_path = self._get_active_config_path("legendaryConfig/legendary/installed.json")
        games = []
        if installed_path:
            try:
                with open(installed_path, 'r') as f:
                    data = json.load(f)
                    # Legendary struct: { "AppName": { "title": "Game", ... }, ... }
                    for app_name, details in data.items():
                        title = details.get('title', 'Unknown')
                        games.append({
                            'id': app_name,
                            'name': title,
                            'type': 'heroic',
                            'platform': 'legendary',
                            'artwork': self._find_artwork(app_name, 'legendary', title),
                            # heroic://launch/legendary/AppName
                            'command': f"heroic://launch/legendary/{app_name}",
                            'path': details.get('install_path')
                        })
            except Exception as e:
                print(f"Error scanning Legendary games: {e}")
        return games

    def _scan_gog(self):
        # GOG Games
        installed_path = self._get_active_config_path("gog_store/installed.json")
        games = []
        if installed_path:
            try:
                with open(installed_path, 'r') as f:
                    data = json.load(f)
                    # GOG struct: { "installed": [ { "appName": "123", "title": "Game", ... }, ... ] }
                    # Or sometimes list directly? User output showed: { "installed": [] } 
                    # Let's assume list of objects based on other tools, or dict? 
                    # User output: { "installed": [] } so it's a dict with key "installed" which is a list.
                    installed_list = data.get('installed', [])
                    for game in installed_list:
                        app_id = game.get('appName') # GOG uses ID as appName usually
                        title = game.get('title', 'Unknown')
                        games.append({
                            'id': app_id,
                            'name': title,
                            'type': 'heroic',
                            'platform': 'gog',
                            'artwork': self._find_artwork(app_id, 'gog', title),
                            # heroic://launch/gog/AppID
                            'command': f"heroic://launch/gog/{app_id}",
                            'path': game.get('install_path')
                        })
            except Exception as e:
                print(f"Error scanning GOG games: {e}")
        return games

    def _find_artwork(self, app_id, platform, game_title):
        # Use Steam's artwork by searching for the game on Steam
        # This provides better quality and consistency than Heroic's cache
        return None  # Return None to trigger Steam lookup in main.py
