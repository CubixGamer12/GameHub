import os
import subprocess
import json

class ProtonRunner:
    def __init__(self, settings_manager=None):
        self.steam_tools_path = os.path.expanduser("~/.steam/root/compatibilitytools.d")
        self.internal_tools_path = os.path.expanduser("~/.local/share/gamehub/proton")
        self.steam_compat_path = os.path.expanduser("~/.steam/steam")
        self.settings = settings_manager

    def get_all_versions(self):
        """Returns a dict of {version_name: executable_path}"""
        versions = {}
        
        # Scan Steam tools
        if os.path.exists(self.steam_tools_path):
            for d in os.listdir(self.steam_tools_path):
                path = os.path.join(self.steam_tools_path, d, "proton")
                if os.path.exists(path):
                    versions[d] = path
                    
        # Scan Internal tools
        if os.path.exists(self.internal_tools_path):
            for d in os.listdir(self.internal_tools_path):
                path = os.path.join(self.internal_tools_path, d, "proton")
                if os.path.exists(path):
                    versions[d] = path
                    
        return versions

    def _get_proton_path(self):
        # 1. Check settings for custom proton
        if self.settings:
            custom_proton = self.settings.get("custom_proton_path")
            if custom_proton and os.path.exists(custom_proton):
                # Check if it's already the exe or a folder
                if os.path.basename(custom_proton) == "proton":
                    return custom_proton
                return os.path.join(custom_proton, "proton")

        # 2. Fallback to latest found
        return self._find_latest_proton()

    def _find_latest_proton(self):
        versions = self.get_all_versions()
        if not versions:
            return None
        
        # Sort by version names (latest first)
        sorted_names = sorted(versions.keys(), reverse=True)
        return versions[sorted_names[0]]

    def launch_game(self, game_path, steam_id=None, args=None, custom_proton_path=None, onlinefix_enabled=False):
        proton_path = custom_proton_path or self._get_proton_path()
        if not proton_path:
            raise Exception("No Proton-GE versions found. Please install one in Settings.")

        env = os.environ.copy()
        
        # If it's a manual game, we need a prefix
        prefix_path = os.path.expanduser(f"~/.local/share/gamehub/prefixes/{steam_id or 'manual_game'}")
        os.makedirs(prefix_path, exist_ok=True)

        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = self.steam_compat_path
        env["STEAM_COMPAT_DATA_PATH"] = prefix_path

        if onlinefix_enabled:
            # Common DLL overrides for OnlineFix/Steamworks Fix
            overrides = "OnlineFix64=n;SteamOverlay64=n;winmm=n,b;dnet=n;steam_api64=n;winhttp=n,b;version=n,b"
            if "WINEDLLOVERRIDES" in env:
                env["WINEDLLOVERRIDES"] = f"{env['WINEDLLOVERRIDES']};{overrides}"
            else:
                env["WINEDLLOVERRIDES"] = overrides
            print(f"OnlineFix enabled. Applying DLL overrides: {overrides}")
        
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
        # Use xdg-open to handle steam:// protocol. 
        # This works correctly for both native and flatpak steam installations.
        cmd = ["xdg-open", f"steam://rungameid/{appid}"]
        subprocess.Popen(cmd)

if __name__ == "__main__":
    runner = ProtonRunner()
    print(f"Proton path: {runner.proton_path}")
