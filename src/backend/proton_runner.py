import os
import subprocess
import json

class ProtonRunner:
    def __init__(self, settings_manager=None):
        self.compat_tools_path = os.path.expanduser("~/.steam/root/compatibilitytools.d")
        self.steam_compat_path = os.path.expanduser("~/.steam/steam")
        self.settings = settings_manager
        
    def _get_proton_path(self):
        # 1. Check settings for custom proton
        if self.settings:
            custom_proton = self.settings.get("custom_proton_path")
            if custom_proton and os.path.exists(custom_proton):
                return os.path.join(custom_proton, "proton")

        # 2. Fallback to system Proton-GE
        return self._find_proton_ge()

    def _find_proton_ge(self):
        if not os.path.exists(self.compat_tools_path):
            return None
        
        # Find the latest Proton-GE
        tools = [d for d in os.listdir(self.compat_tools_path) if os.path.isdir(os.path.join(self.compat_tools_path, d))]
        ge_tools = [t for t in tools if "GE-Proton" in t]
        if not ge_tools:
            return None
        
        ge_tools.sort(reverse=True)
        return os.path.join(self.compat_tools_path, ge_tools[0], "proton")

    def launch_game(self, game_path, steam_id=None, args=None):
        proton_path = self._get_proton_path()
        if not proton_path:
            raise Exception("Proton-GE not found in settings or ~/.steam/root/compatibilitytools.d/")

        env = os.environ.copy()
        
        # If it's a manual game, we need a prefix
        prefix_path = os.path.expanduser(f"~/.local/share/gamehub/prefixes/{steam_id or 'manual_game'}")
        os.makedirs(prefix_path, exist_ok=True)

        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = self.steam_compat_path
        env["STEAM_COMPAT_DATA_PATH"] = prefix_path
        
        cmd = [proton_path, "run", game_path]
        if args:
            # Simple space split for now. 
            # In a real app we might want shlex.split but let's keep it simple.
            import shlex
            cmd.extend(shlex.split(args))
        
        print(f"Launching with Proton: {' '.join(cmd)}")
        # start_new_session=True ensures the process group is killed together
        return subprocess.Popen(cmd, env=env, start_new_session=True)

    def launch_native(self, game_path, args=None):
        """Launch a game directly without Proton"""
        cmd = [game_path]
        if args:
            import shlex
            cmd.extend(shlex.split(args))
            
        print(f"Launching natively: {' '.join(cmd)}")
        return subprocess.Popen(cmd, start_new_session=True)

    def launch_steam_game(self, appid):
        # Steam games are better launched via steam uri, 
        # but the request asked for proton-ge handling.
        # However, steam usually manages its own proton.
        # For simplicity and following user request "using proton-ge", 
        # we'll use steam's protocol if it's a steam game, 
        # or find the exe and run via our ge if manual.
        cmd = ["steam", f"steam://rungameid/{appid}"]
        subprocess.Popen(cmd)

if __name__ == "__main__":
    runner = ProtonRunner()
    print(f"Proton path: {runner.proton_path}")
