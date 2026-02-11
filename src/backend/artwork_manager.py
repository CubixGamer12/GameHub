import os
import subprocess
import shutil

class ArtworkManager:
    def __init__(self):
        self.cache_dir = os.path.expanduser("~/.cache/gamehub/artworks")
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_steam_artwork_url(self, appid):
        # Steam library cover URL
        return f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/library_600x900.jpg"

    def extract_exe_icon(self, exe_path, game_id):
        target_path = os.path.join(self.cache_dir, f"{game_id}.png")
        if os.path.exists(target_path):
            return target_path

        # Check if wrestool is available
        if not shutil.which("wrestool"):
            pass
            return None

        try:
            # Extract the largest icon
            # 1. Extract icons to a temporary ico file
            ico_path = os.path.join(self.cache_dir, f"{game_id}.ico")
            subprocess.run(["wrestool", "-x", "-t", "14", exe_path, "-o", ico_path], check=True)
            
            # 2. Convert ico to png using icotool (part of icoutils)
            if shutil.which("icotool"):
                subprocess.run(["icotool", "-x", "-o", target_path, ico_path], check=True)
                # icotool -x might create multiple files like {game_id}_1_48x48.png
                # We'll try to find the biggest one or just use the first output
                # For simplicity, we just use the first one it produces
                output_files = [f for f in os.listdir(self.cache_dir) if f.startswith(f"{game_id}_") and f.endswith(".png")]
                if output_files:
                    output_files.sort(key=lambda x: os.path.getsize(os.path.join(self.cache_dir, x)), reverse=True)
                    final_path = os.path.join(self.cache_dir, output_files[0])
                    shutil.move(final_path, target_path)
                    # Cleanup others
                    for f in output_files[1:]:
                        os.remove(os.path.join(self.cache_dir, f))
                
                if os.path.exists(ico_path):
                    os.remove(ico_path)
                return target_path
        except Exception as e:
            pass
        
        return None

    def get_sgdb_artwork(self, game_id, api_key, platform="steam"):
        """Fetch artwork (grid) from SteamGridDB API"""
        if not api_key:
            return None
            
        # For non-steam, game_id might not be appid. 
        # But for now we support Steam lookups as seen in API v2
        endpoint = f"https://www.steamgriddb.com/api/v2/grids/{platform}/{game_id}"
        
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            # Optional filters: dimensions, styles
            params = {"styles": "standard,alternate,blurred,white_logo,material,no_logo"}
            
            response = requests.get(endpoint, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    # Grids are usually sorted by score/upvotes
                    # We take the first one that has a valid URL
                    for grid in data['data']:
                        url = grid.get('url')
                        if url:
                            return url
            else:
                print(f"[ArtworkManager] SGDB API error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[ArtworkManager] SGDB Exception: {e}")
            
        return None

    def get_artwork_path(self, game, sgdb_key=None):
        # Priority 1: User set artwork (from config)
        if game.get('artwork'):
            return game['artwork']
            
        # Priority 2: SteamWebAPI/SteamGridDB logic
        if game['type'] == 'steam':
            # Try SGDB if key provided
            if sgdb_key:
                sgdb_url = self.get_sgdb_artwork(game['id'], sgdb_key, platform="steam")
                if sgdb_url:
                    return sgdb_url
            return self.get_steam_artwork_url(game['id'])
            
        elif game['type'] == 'manual':
            # Try SGDB for manual games if we have a steam_id
            steam_id = game.get('steam_id')
            if steam_id and sgdb_key:
                sgdb_url = self.get_sgdb_artwork(steam_id, sgdb_key, platform="steam")
                if sgdb_url:
                    return sgdb_url
            return self.extract_exe_icon(game['path'], game['id'])
            
        elif game['type'] == 'heroic':
             # Heroic games usually have a steam_id mapped if we searched for it
             steam_id = game.get('steam_id')
             if steam_id and sgdb_key:
                 sgdb_url = self.get_sgdb_artwork(steam_id, sgdb_key, platform="steam")
                 if sgdb_url:
                     return sgdb_url
        
        return None

    def download_steam_artwork(self, app_id, game_id):
        try:
            url = self.get_steam_artwork_url(app_id)
            import requests
            response = requests.get(url)
            if response.status_code == 200:
                target_path = os.path.join(self.cache_dir, f"{game_id}.jpg")
                with open(target_path, 'wb') as f:
                    f.write(response.content)
                return target_path
        except Exception as e:
            pass
        return None

    def cache_local_image(self, source_path, game_id):
        try:
            ext = os.path.splitext(source_path)[1]
            target_path = os.path.join(self.cache_dir, f"{game_id}{ext}")
            shutil.copy(source_path, target_path)
            return target_path
        except Exception as e:
            pass
            return None

    def search_steam_appid(self, game_name):
        """Search for a Steam AppID by game name using Steam's GetAppList API"""
        try:
            import requests
            # Cache the app list to avoid repeated downloads
            cache_file = os.path.join(self.cache_dir, "steam_applist.json")
            
            # Refresh cache if older than 7 days or doesn't exist
            import time
            should_refresh = True
            if os.path.exists(cache_file):
                age_days = (time.time() - os.path.getmtime(cache_file)) / 86400
                if age_days < 7:
                    should_refresh = False
            
            if should_refresh:

                response = requests.get("http://api.steampowered.com/ISteamApps/GetAppList/v2/")
                if response.status_code == 200:
                    with open(cache_file, 'w') as f:
                        import json
                        json.dump(response.json(), f)
                else:
                    return None
            
            # Search the cached list (only if file exists now)
            if not os.path.exists(cache_file):
                return None
                
            with open(cache_file, 'r') as f:
                import json
                data = json.load(f)
                
            apps = data.get('applist', {}).get('apps', [])
            
            # Normalize search term
            search_term = game_name.lower().strip()
            
            # Try exact match first
            for app in apps:
                if app['name'].lower() == search_term:
                    return str(app['appid'])
            
            # Try partial match (contains)
            for app in apps:
                if search_term in app['name'].lower():
                    return str(app['appid'])
                    
        except Exception as e:
            pass
            
        return None
