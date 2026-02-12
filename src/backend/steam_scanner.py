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

    def scan_games(self, api_key=None):
        games = []
        seen_ids = set()
        
        # Unwanted items keywords
        unwanted = ["Steam Linux Runtime", "Proton", "Steamworks Common Redistributables", "SteamVR"]

        # 1. Scan installed games (ACF files)
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
                        
                        game_info['installed'] = True
                        games.append(game_info)
                        seen_ids.add(game_info['id'])

        # 2. Fetch uninstalled games from API if key provided
        if api_key and api_key.strip():
            api_key = api_key.strip()
            steam_id = self.get_steam_id()
            if steam_id:
                print(f"[SteamScanner] Found SteamID: {steam_id}. Fetching games from API...")
                api_games = self.get_owned_games(api_key, steam_id)
                print(f"[SteamScanner] API returned {len(api_games)} games.")
                for g in api_games:
                    if g['id'] not in seen_ids:
                        # Filter unwanted
                        is_unwanted = any(u.lower() in g['name'].lower() for u in unwanted)
                        if is_unwanted:
                            continue
                        games.append(g)
                        seen_ids.add(g['id'])
            else:
                print("[SteamScanner] Could not find SteamID in loginusers.vdf")
        else:
            if api_key is not None:
                print("[SteamScanner] API Key is empty or missing in settings.")
        
        return games

    def get_steam_id(self):
        """
        Attempts to find the logged-in Steam ID from loginusers.vdf
        Looks for the user with "MostRecent" "1"
        """
        paths = [
            os.path.expanduser("~/.steam/steam/config/loginusers.vdf"),
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/.steam/steam/config/loginusers.vdf"),
            os.path.expanduser("~/.local/share/Steam/config/loginusers.vdf")
        ]
        
        for path in paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Find all user blocks
                        # A block starts with "7656119..." and ends with }
                        # We use a non-greedy match for the content between { and }
                        users = re.findall(r'"(\d{17})"\s*{(.+?)}', content, re.DOTALL)
                        
                        for steam_id, user_data in users:
                            if re.search(r'"MostRecent"\s+"1"', user_data, re.IGNORECASE):
                                return steam_id
                                
                        # If no MostRecent, take the first one found
                        if users:
                            return users[0][0]
                except Exception as e:
                    print(f"Error parsing loginusers.vdf at {path}: {e}")
                    pass
        return None

    def get_owned_games(self, api_key, steam_id):
        """
        Fetches owned games from Steam Web API
        """
        if not api_key or not steam_id:
            print("[SteamScanner] Missing API Key or SteamID")
            return []
            
        url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={steam_id}&format=json&include_appinfo=1&include_played_free_games=1"
        
        try:
            import requests
            print(f"[SteamScanner] Requesting: {url.replace(api_key, 'HIDDEN')}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                games = []
                if 'response' in data and 'games' in data['response']:
                    for item in data['response']['games']:
                        games.append({
                            'id': str(item.get('appid')),
                            'name': item.get('name', f"App {item.get('appid')}"),
                            'type': 'steam',
                            'installed': False,
                            'artwork': f"https://cdn.akamai.steamstatic.com/steam/apps/{item.get('appid')}/library_600x900.jpg",
                            'playtime': item.get('playtime_forever', 0) * 60  # Minutes to seconds
                        })
                else:
                    print(f"[SteamScanner] API response format unexpected or empty: {data}")
                return games
            else:
                print(f"[SteamScanner] API returned error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[SteamScanner] Exception during API call: {e}")
            pass
        return []

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
                        'installed': True,
                        'artwork': f"https://cdn.akamai.steamstatic.com/steam/apps/{appid.group(1)}/library_600x900.jpg"
                    }
        except Exception as e:
            pass
        return None

if __name__ == "__main__":
    scanner = SteamScanner()
    games = scanner.scan_games()
    for g in games:
        print(f"Found: {g['name']} ({g['id']})")
