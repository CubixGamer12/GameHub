import json
import os
import time

class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/gamehub")
        self.config_file = os.path.join(self.config_dir, "games.json")
        self.heroic_artwork_file = os.path.join(self.config_dir, "heroic_artwork.json")
        os.makedirs(self.config_dir, exist_ok=True)
        self.games = self._load_config()
        self.heroic_artwork = self._load_heroic_artwork()
        self.steam_playtime_file = os.path.join(self.config_dir, "steam_playtime.json")
        self.heroic_playtime_file = os.path.join(self.config_dir, "heroic_playtime.json")
        self.steam_playtime = self._load_playtime(self.steam_playtime_file)
        self.heroic_playtime = self._load_playtime(self.heroic_playtime_file)

    def _load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_game(self, name, exe_path, runner_type='proton', proton_version=None, use_global_args=True, arguments=None, artwork=None, onlinefix_enabled=False):
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
            'playtime': 0  # Total seconds played
        }
        self.games.append(game)
        with open(self.config_file, 'w') as f:
            json.dump(self.games, f, indent=4)
        return game

    def get_manual_games(self):
        return self.games

    def delete_game(self, game_id):
        self.games = [g for g in self.games if g['id'] != game_id]
        with open(self.config_file, 'w') as f:
            json.dump(self.games, f, indent=4)

    def update_game(self, game_id, name=None, path=None, runner_type=None, proton_version=None, use_global_args=None, arguments=None, artwork=None, onlinefix_enabled=None):
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
                break
        with open(self.config_file, 'w') as f:
            json.dump(self.games, f, indent=4)

    def update_game_artwork(self, game_id, artwork_path):
        for game in self.games:
            if game['id'] == game_id:
                game['artwork'] = artwork_path
                break
        with open(self.config_file, 'w') as f:
            json.dump(self.games, f, indent=4)

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
        return self.heroic_artwork.get(game_id)

    def update_heroic_artwork(self, game_id, artwork_path):
        self.heroic_artwork[game_id] = artwork_path
        with open(self.heroic_artwork_file, 'w') as f:
            json.dump(self.heroic_artwork, f, indent=4)

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
            with open(self.config_file, 'w') as f:
                json.dump(self.games, f, indent=4)
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
