import json
import os
import time

class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/gamehub")
        self.config_file = os.path.join(self.config_dir, "games.json")
        self.heroic_artwork_file = os.path.join(self.config_dir, "heroic_artwork.json")
        os.makedirs(self.config_dir, exist_ok=True)
        
        # self.data will hold {'games': [], 'hidden_games': []}
        self.data = self._load_config()
        self.games = self.data['games'] # Reference for backward compatibility in some places
        
        self.heroic_artwork = self._load_heroic_artwork()
        self.steam_metadata_file = os.path.join(self.config_dir, "steam_metadata.json")
        self.steam_metadata = self._load_steam_metadata()
        
        self.steam_playtime_file = os.path.join(self.config_dir, "steam_playtime.json")
        self.heroic_playtime_file = os.path.join(self.config_dir, "heroic_playtime.json")
        self.steam_playtime = self._load_playtime(self.steam_playtime_file)
        self.heroic_playtime = self._load_playtime(self.heroic_playtime_file)

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        # Old format, migrate to new dict format
                        return {'games': content, 'hidden_games': []}
                    return content
            except:
                return {'games': [], 'hidden_games': []}
        return {'games': [], 'hidden_games': []}

    def _save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def save_game(self, name, exe_path, runner_type='proton', proton_version=None, use_global_args=True, arguments=None, artwork=None, onlinefix_enabled=False, steam_id=None):
        game_id = str(int(time.time()))
        game = {
            'id': game_id,
            'name': name,
            'path': exe_path,
            'type': 'manual',
            'runner_type': runner_type,
            'proton_version': proton_version,
            'use_global_args': use_global_args,
            'arguments': arguments,
            'artwork': artwork,
            'onlinefix_enabled': onlinefix_enabled,
            'steam_id': steam_id,
            'playtime': 0  # Total seconds played
        }
        self.games.append(game)
        self._save_config()
        return game

    def get_manual_games(self):
        return self.games

    def delete_game(self, game_id):
        self.data['games'] = [g for g in self.data['games'] if g['id'] != game_id]
        self.games = self.data['games']
        self._save_config()

    def update_game(self, game_id, name=None, path=None, runner_type=None, proton_version=None, use_global_args=None, arguments=None, artwork=None, onlinefix_enabled=None, steam_id=None):
        for game in self.games:
            if game['id'] == game_id:
                if name is not None: game['name'] = name
                if path is not None: game['path'] = path
                if runner_type is not None: game['runner_type'] = runner_type
                if proton_version is not None: game['proton_version'] = proton_version
                if use_global_args is not None: game['use_global_args'] = use_global_args
                if arguments is not None: game['arguments'] = arguments
                if artwork is not None: game['artwork'] = artwork
                if onlinefix_enabled is not None: game['onlinefix_enabled'] = onlinefix_enabled
                if steam_id is not None: game['steam_id'] = steam_id
                break
        self._save_config()

    def update_game_artwork(self, game_id, artwork_path):
        for game in self.games:
            if game['id'] == game_id:
                game['artwork'] = artwork_path
                break
        self._save_config()

    def _load_heroic_artwork(self):
        if os.path.exists(self.heroic_artwork_file):
            try:
                with open(self.heroic_artwork_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _load_playtime(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def get_heroic_artwork(self, game_id):
        metadata = self.heroic_artwork.get(game_id)
        if isinstance(metadata, dict):
            return metadata.get('artwork')
        return metadata # Backward compatibility for old simple string paths

    def get_heroic_steam_id(self, game_id):
        metadata = self.heroic_artwork.get(game_id)
        if isinstance(metadata, dict):
            return metadata.get('steam_id')
        return None

    def update_heroic_metadata(self, game_id, artwork_path=None, steam_id=None):
        if game_id not in self.heroic_artwork or not isinstance(self.heroic_artwork[game_id], dict):
            # Migrate to dict if it was a string or missing
            current_art = self.heroic_artwork.get(game_id)
            self.heroic_artwork[game_id] = {'artwork': current_art, 'steam_id': None}
            
        if artwork_path:
            self.heroic_artwork[game_id]['artwork'] = artwork_path
        if steam_id:
            self.heroic_artwork[game_id]['steam_id'] = steam_id
            
        with open(self.heroic_artwork_file, 'w') as f:
            json.dump(self.heroic_artwork, f, indent=4)

    def _load_steam_metadata(self):
        if os.path.exists(self.steam_metadata_file):
            try:
                with open(self.steam_metadata_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def get_steam_artwork_override(self, game_id):
        metadata = self.steam_metadata.get(str(game_id))
        if isinstance(metadata, dict):
            return metadata.get('artwork')
        return None

    def update_steam_metadata(self, game_id, artwork_path=None, steam_id=None):
        game_id = str(game_id)
        if game_id not in self.steam_metadata:
            self.steam_metadata[game_id] = {}
            
        if artwork_path:
            self.steam_metadata[game_id]['artwork'] = artwork_path
        if steam_id:
            self.steam_metadata[game_id]['steam_id'] = steam_id
            
        with open(self.steam_metadata_file, 'w') as f:
            json.dump(self.steam_metadata, f, indent=4)

    def get_playtime(self, game_id, game_type='manual'):
        """Get total playtime in seconds for a game"""
        if game_type == 'manual':
            for game in self.games:
                if game['id'] == game_id:
                    return game.get('playtime', 0)
        elif game_type == 'steam':
            return self.steam_playtime.get(game_id, 0)
        elif game_type == 'heroic':
            return self.heroic_playtime.get(game_id, 0)
        return 0

    def add_playtime(self, game_id, seconds, game_type='manual'):
        """Add session playtime to game's total"""
        if game_type == 'manual':
            for game in self.games:
                if game['id'] == game_id:
                    current = game.get('playtime', 0)
                    game['playtime'] = current + seconds
                    break
            self._save_config()
        elif game_type == 'steam':
            current = self.steam_playtime.get(game_id, 0)
            self.steam_playtime[game_id] = current + seconds
            with open(self.steam_playtime_file, 'w') as f:
                json.dump(self.steam_playtime, f, indent=4)
        elif game_type == 'heroic':
            current = self.heroic_playtime.get(game_id, 0)
            self.heroic_playtime[game_id] = current + seconds
            with open(self.heroic_playtime_file, 'w') as f:
                json.dump(self.heroic_playtime, f, indent=4)
