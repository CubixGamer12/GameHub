import sys
import os
import requests
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from backend.steam_scanner import SteamScanner
from backend.proton_runner import ProtonRunner
from backend.config_manager import ConfigManager
from backend.artwork_manager import ArtworkManager
from backend.proton_manager import ProtonManager
from backend.settings_manager import SettingsManager
from backend.session_manager import SessionManager
from backend.heroic_scanner import HeroicScanner
from backend.protondb_manager import ProtonDBManager
import threading
import json
from ui.window import GameHubWindow
from ui.pages.settings import SettingsPage

class GameHubApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.gamehub",
                         flags=gi.repository.Gio.ApplicationFlags.FLAGS_NONE)
        self.settings_manager = SettingsManager()
        self.scanner = SteamScanner()
        self.heroic_scanner = HeroicScanner()
        self.runner = ProtonRunner(self.settings_manager)
        self.config = ConfigManager()
        self.art_manager = ArtworkManager()
        self.proton_manager = ProtonManager()
        self.protondb = ProtonDBManager()
        self.session_manager = SessionManager(self.runner, self.settings_manager)

    def do_activate(self):
        self.win = GameHubWindow(application=self, 
                                 steam_scanner=self.scanner,
                                 config=self.config,
                                 art_manager=self.art_manager,
                                 proton_manager=self.proton_manager,
                                 settings_manager=self.settings_manager,
                                 session_manager=self.session_manager)
        
        self.win.connect("refresh-games", self.refresh_games)
        self.win.connect("add-manual-game", self.add_game)
        self.win.connect("update-manual-game", self.update_manual_game)
        # game-launched handled internally by window via session_manager now
        self.win.connect("open-settings", self.open_settings)
        
        # Connect playtime tracking
        self.session_manager.connect('playtime-updated', self.on_playtime_updated)
        
        self.refresh_games(None)
        self.win.present()

    def open_settings(self, win):
        # Create a new window for settings
        settings_win = Adw.PreferencesWindow(transient_for=self.win, modal=True)
        settings_win.set_title("GameHub Settings")
        
        page = SettingsPage(self.proton_manager, self.settings_manager)
        settings_win.add(page)
        
        # When settings window is closed, refresh filters in the main window
        settings_win.connect("unmap", lambda x: self.win.apply_settings_filters())
        
        settings_win.present()

    def refresh_games(self, win):
        """Scan games in background to avoid freezing UI using parallel processing"""
        import concurrent.futures

        def resolve_game_data(game, sgdb_key):
            # 1. Artwork
            if game['type'] == 'steam':
                override = self.config.get_steam_artwork_override(game['id'])
                game['artwork'] = override if override else self.art_manager.get_artwork_path(game, sgdb_key=sgdb_key)
                game['playtime'] = self.config.get_playtime(str(game['id']), 'steam')
            elif game['type'] == 'manual':
                game['artwork'] = self.art_manager.get_artwork_path(game, sgdb_key=sgdb_key)
                game['playtime'] = self.config.get_playtime(game['id'], 'manual')
            elif game['type'] == 'heroic':
                override = self.config.get_heroic_artwork(game['id'])
                game['artwork'] = override if override else self.art_manager.get_artwork_path(game, sgdb_key=sgdb_key)
                game['playtime'] = self.config.get_playtime(game['id'], 'heroic')
                game['steam_id'] = self.config.get_heroic_steam_id(game['id'])
            
            game['protondb_tier'] = None
            return game

        def do_scan():
            try:
                enable_api = self.settings_manager.get("enable_steam_api", "False").lower() == "true"
                api_key = self.settings_manager.get("steam_api_key", "") if enable_api else None
                sgdb_key = self.settings_manager.get("sgdb_api_key", "").strip() or None
                
                # Initial scan
                steam_games = self.scanner.scan_games(api_key=api_key)
                manual_games = self.config.get_manual_games()
                heroic_games = self.heroic_scanner.scan_games()
                
                all_games = steam_games + manual_games + heroic_games
                
                # Parallel Resolution
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(resolve_game_data, g, sgdb_key) for g in all_games]
                    concurrent.futures.wait(futures)

                # Update UI from main thread
                gi.repository.GLib.idle_add(self.win.update_game_list, steam_games, manual_games, heroic_games)
                
                # Parallel ProtonDB Status
                def fetch_proton_tier(game):
                    game_id = str(game.get('steam_id') or game['id'])
                    tier = self.protondb.get_tier(game_id)
                    if tier:
                        page = None
                        if game['type'] == 'steam': page = self.win.steam_page
                        elif game['type'] == 'manual': page = self.win.manual_page
                        elif game['type'] == 'heroic': page = self.win.heroic_page
                        
                        if page:
                            gi.repository.GLib.idle_add(page.update_protondb_status, str(game['id']), tier)

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    executor.map(fetch_proton_tier, all_games)
                
            except Exception as e:
                print(f"[Main] Refresh error: {e}")

        import threading
        thread = threading.Thread(target=do_scan, daemon=True)
        thread.start()

    def add_game(self, win, name, path, runner, version, use_global, args, art_dict, onlinefix_enabled):
        steam_id = art_dict['value'] if art_dict['type'] == 'steam' else None
        
        # Initial save to get an ID for artwork naming
        game = self.config.save_game(name, path, runner_type=runner, proton_version=version, 
                                     use_global_args=use_global, arguments=args, 
                                     onlinefix_enabled=onlinefix_enabled, steam_id=steam_id)
        game_id = game['id']
        
        artwork_path = None
        if art_dict['type'] == 'file':
            artwork_path = self.art_manager.cache_local_image(art_dict['value'], game_id)
        elif art_dict['type'] == 'steam':
            artwork_path = self.art_manager.download_steam_artwork(art_dict['value'], game_id)
            
        if artwork_path:
            self.config.update_game_artwork(game_id, artwork_path)
            
        self.refresh_games(None)

    def update_manual_game(self, win, game_id, name, path, runner, version, use_global, args, art_dict, onlinefix_enabled):
        steam_id = art_dict['value'] if art_dict['type'] == 'steam' else None
        
        artwork_path = None
        if art_dict['type'] == 'file':
            artwork_path = self.art_manager.cache_local_image(art_dict['value'], game_id)
        elif art_dict['type'] == 'steam':
            artwork_path = self.art_manager.download_steam_artwork(art_dict['value'], game_id)

        self.config.update_game(game_id, 
                                name=name, 
                                path=path, 
                                runner_type=runner, 
                                proton_version=version,
                                use_global_args=use_global,
                                arguments=args, 
                                artwork=artwork_path,
                                onlinefix_enabled=onlinefix_enabled,
                                steam_id=steam_id)
        self.refresh_games(None)

    def launch_game(self, win, game):

        if game['type'] == 'steam':
            self.runner.launch_steam_game(game['id'])
        else:
            self.runner.launch_game(game['path'], game['id'])

    def on_playtime_updated(self, session_manager, game_type, game_id, seconds):
        """Handle playtime update from session manager"""
        self.config.add_playtime(game_id, seconds, game_type)

        self.refresh_games(None)

if __name__ == "__main__":

    app = GameHubApplication()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
