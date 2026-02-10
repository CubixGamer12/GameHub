import os
import re

class SteamScanner:
    def __init__(self):
        self.steam_paths = [
            os.path.expanduser("~/.steam/steam"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.steam/steam")
        ]
        self.libraries = []
        for path in self.steam_paths:
            apps_path = os.path.join(path, "steamapps")
            if os.path.exists(apps_path):
                self.libraries.append(apps_path)
                self._find_extra_libraries(path)

    def _find_extra_libraries(self, steam_path):
        library_vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
        if not os.path.exists(library_vdf):
            return

        with open(library_vdf, 'r') as f:
            content = f.read()
            # Crude regex to find "path" "..."
            paths = re.findall(r'"path"\s+"([^"]+)"', content)
            for path in paths:
                apps_path = os.path.join(path, "steamapps")
                if os.path.exists(apps_path) and apps_path not in self.libraries:
                    self.libraries.append(apps_path)

    def scan_games(self):
        games = []
        seen_ids = set()
        
        # Unwanted items keywords
        unwanted = ["Steam Linux Runtime", "Proton", "Steamworks Common Redistributables", "SteamVR"]

        for lib in self.libraries:
            if not os.path.exists(lib):
                continue
            for file in os.listdir(lib):
                if file.startswith("appmanifest_") and file.endswith(".acf"):
                    game_info = self._parse_acf(os.path.join(lib, file))
                    if game_info:
                        if game_info['id'] in seen_ids:
                            continue
                        
                        # Filter tools and runtimes
                        is_unwanted = any(u.lower() in game_info['name'].lower() for u in unwanted)
                        if is_unwanted:
                            continue

                        game_info['library_path'] = lib
                        if game_info.get('install_dir'):
                            game_info['path'] = os.path.join(lib, "common", game_info['install_dir'])
                        
                        games.append(game_info)
                        seen_ids.add(game_info['id'])
        return games

    def _parse_acf(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                appid = re.search(r'"appid"\s+"(\d+)"', content)
                name = re.search(r'"name"\s+"([^"]+)"', content)
                installdir = re.search(r'"installdir"\s+"([^"]+)"', content)
                
                if appid and name:
                    return {
                        'id': appid.group(1),
                        'name': name.group(1),
                        'install_dir': installdir.group(1) if installdir else "",
                        'type': 'steam',
                        'artwork': f"https://cdn.akamai.steamstatic.com/steam/apps/{appid.group(1)}/library_600x900.jpg"
                    }
        except Exception as e:
            print(f"Error parsing {path}: {e}")
        return None

if __name__ == "__main__":
    scanner = SteamScanner()
    games = scanner.scan_games()
    for g in games:
        print(f"Found: {g['name']} ({g['id']})")
