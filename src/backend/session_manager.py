import gi
from gi.repository import GObject, GLib
import os
import signal
import subprocess
import psutil
import time

class SessionManager(GObject.Object):
    __gsignals__ = {
        'game-started': (GObject.SignalFlags.RUN_FIRST, None, (object,)), # game dict
        'game-stopped': (GObject.SignalFlags.RUN_FIRST, None, (object,)), # game dict
        'playtime-updated': (GObject.SignalFlags.RUN_FIRST, None, (str, str, int)), # game_type, game_id, seconds
    }

    def __init__(self, runner, settings_manager=None):
        super().__init__()
        self.runner = runner
        self.settings = settings_manager
        self.running_games = {} # game_id -> (game, process, start_time)
        self.time = time
        
        # Start polling
        GLib.timeout_add(1000, self._poll_processes)

    def launch_game(self, game):
        if game['id'] in self.running_games:
            print(f"Game {game['name']} is already running.")
            return

        try:
            if game['type'] == 'manual':
                runner_type = game.get('runner_type', 'proton')
                
                # Resolve arguments
                if game.get('use_global_args', True) and self.settings:
                    args = self.settings.get("global_arguments", "")
                else:
                    args = game.get('arguments', "")
                if runner_type == 'native':
                    process = self.runner.launch_native(game['path'], args=args)
                else:
                    # Resolve specific version if set
                    proton_version = game.get('proton_version')
                    custom_path = None
                    if proton_version:
                        versions = self.runner.get_all_versions()
                        custom_path = versions.get(proton_version)
                    
                    process = self.runner.launch_game(game['path'], game['id'], args=args, custom_proton_path=custom_path)
                
                if process:
                    start_time = self.time.time()
                    self.running_games[game['id']] = (game, process, start_time)
                    self.emit('game-started', game)
            elif game['type'] == 'steam':
                self.runner.launch_steam_game(game['id'])
                # Start looking for the process
                self._start_tracking_latent_game(game)
            elif game['type'] == 'heroic':
                print(f"Launching Heroic game: {game['name']}")
                subprocess.Popen(["xdg-open", game['command']])
                # Start looking for the process
                self._start_tracking_latent_game(game)
        except Exception as e:
            print(f"Failed to launch game: {e}")

    def launch_game_native(self, game):
        """Launch a manual game without Proton prefix"""
        if game['id'] in self.running_games:
            print(f"Game {game['name']} is already running.")
            return

        try:
            args = game.get('arguments')
            process = self.runner.launch_native(game['path'], args=args)
            if process:
                start_time = self.time.time()
                self.running_games[game['id']] = (game, process, start_time)
                self.emit('game-started', game)
        except Exception as e:
            print(f"Failed to launch native game: {e}")

    def stop_game(self, game_id):
        if game_id in self.running_games:
            game, process, _ = self.running_games[game_id]
            print(f"Stopping game {game['name']} ({game_id})...")
            try:
                if hasattr(process, 'terminate'): # psutil.Process
                    # Kill children first
                    try:
                        children = process.children(recursive=True)
                        for child in children:
                            child.terminate()
                    except:
                        pass
                    process.terminate()
                else: # subprocess.Popen
                    # Kill the entire process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except Exception as e:
                print(f"Error stopping game: {e}")

    def is_running(self, game_id):
        return game_id in self.running_games

    def _poll_processes(self):
        stopped = []
        for game_id, (game, process, start_time) in self.running_games.items():
            is_finished = False
            if hasattr(process, 'poll'): # subprocess.Popen
                is_finished = process.poll() is not None
            else: # psutil.Process
                try:
                    is_finished = not process.is_running() or process.status() == psutil.STATUS_ZOMBIE
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    is_finished = True
            
            if is_finished:
                stopped.append((game_id, start_time))
        
        for game_id, start_time in stopped:
            game, _, _ = self.running_games.pop(game_id)
            # Calculate session playtime
            session_seconds = int(self.time.time() - start_time)
            if session_seconds > 0:
                self.emit('playtime-updated', game['type'], game['id'], session_seconds)
            self.emit('game-stopped', game)
            
        # Poll for latent games (discovery)
        self._poll_latent_games()

        return True

    def _start_tracking_latent_game(self, game):
        """Start polling for a process that appeared after launch-via-URI"""
        if not hasattr(self, 'latent_games'):
            self.latent_games = [] # list of (game, start_wait_time)
        self.latent_games.append((game, self.time.time()))
        self.emit('game-started', game)

    def _poll_latent_games(self):
        if not hasattr(self, 'latent_games') or not self.latent_games:
            return

        remaining = []
        for game, wait_start in self.latent_games:
            process = self._find_game_process(game)
            if process:
                print(f"Discovered process for {game['name']}")
                # We don't know exactly when it started, but now is a good guess
                self.running_games[game['id']] = (game, process, self.time.time())
            elif self.time.time() - wait_start < 30: # Wait up to 30s
                remaining.append((game, wait_start))
            else:
                print(f"Gave up looking for process for {game['name']}")
                self.emit('game-stopped', game)
        
        self.latent_games = remaining

    def _find_game_process(self, game):
        """Try to find a running process for a given game appid or command"""
        try:
            for proc in psutil.process_iter(['environ', 'cmdline', 'pid']):
                try:
                    env = proc.info.get('environ') or {}
                    if game['type'] == 'steam':
                        # Steam games usually have SteamAppId in env
                        appid = env.get('SteamAppId')
                        if appid == str(game['id']):
                            return proc
                    elif game['type'] == 'heroic':
                        # Heroic games (legendary/gog)
                        # This is harder. Check if game['command'] or game['name'] is in cmdline
                        cmdline = " ".join(proc.info.get('cmdline') or [])
                        # For Legendary
                        if "legendary" in cmdline and game['id'] in cmdline:
                            return proc
                        # For GOG/Wine (Generic check)
                        if game['name'].lower() in cmdline.lower() and "wine" in cmdline.lower():
                            return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"Error searching for process: {e}")
        return None
