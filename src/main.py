import sys
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
        self.session_manager = SessionManager(self.runner)

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
        
        settings_win.present()

    def refresh_games(self, win):
        steam_games = self.scanner.scan_games()
        manual_games = self.config.get_manual_games()
        heroic_games = self.heroic_scanner.scan_games()
        
        for game in manual_games:
            game['artwork'] = self.art_manager.get_artwork_path(game)
            game['playtime'] = self.config.get_playtime(game['id'], 'manual')
        
        for game in steam_games:
            game['playtime'] = self.config.get_playtime(str(game['id']), 'steam')

        # Apply Heroic artwork overrides and playtime
        for game in heroic_games:
            override = self.config.get_heroic_artwork(game['id'])
            if override:
                game['artwork'] = override
            game['playtime'] = self.config.get_playtime(game['id'], 'heroic')
            
        self.win.update_game_list(steam_games, manual_games, heroic_games)

    def add_game(self, win, name, path, runner, version, args, art_dict):
        # Initial save to get an ID for artwork naming
        game = self.config.save_game(name, path, runner_type=runner, proton_version=version, arguments=args)
        game_id = game['id']
        
        artwork_path = None
        if art_dict['type'] == 'file':
            artwork_path = self.art_manager.cache_local_image(art_dict['value'], game_id)
        elif art_dict['type'] == 'steam':
            artwork_path = self.art_manager.download_steam_artwork(art_dict['value'], game_id)
            
        if artwork_path:
            self.config.update_game_artwork(game_id, artwork_path)
            
        self.refresh_games(None)

    def update_manual_game(self, win, game_id, name, path, runner, version, args, art_dict):
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
                                arguments=args, 
                                artwork=artwork_path)
        self.refresh_games(None)

    def launch_game(self, win, game):
        print(f"Launching {game['name']}...")
        if game['type'] == 'steam':
            self.runner.launch_steam_game(game['id'])
        else:
            self.runner.launch_game(game['path'], game['id'])

    def on_playtime_updated(self, session_manager, game_type, game_id, seconds):
        """Handle playtime update from session manager"""
        self.config.add_playtime(game_id, seconds, game_type)
        print(f"Playtime updated: +{seconds}s for {game_type} game {game_id}")
        self.refresh_games(None)

if __name__ == "__main__":
    print("Starting GameHub application...")
    app = GameHubApplication()
    exit_status = app.run(sys.argv)
    sys.exit(exit_status)
