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
            print("Warning: wrestool not found. Cannot extract icon from EXE.")
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
            print(f"Error extracting icon: {e}")
        
        return None

    def get_artwork_path(self, game):
        # Priority 1: User set artwork (from config)
        if game.get('artwork'):
            return game['artwork']
            
        # Priority 2: Default logic
        if game['type'] == 'steam':
            return self.get_steam_artwork_url(game['id'])
        elif game['type'] == 'manual':
            return self.extract_exe_icon(game['path'], game['id'])
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
            print(f"Error downloading artwork: {e}")
        return None

    def cache_local_image(self, source_path, game_id):
        try:
            ext = os.path.splitext(source_path)[1]
            target_path = os.path.join(self.cache_dir, f"{game_id}{ext}")
            shutil.copy(source_path, target_path)
            return target_path
        except Exception as e:
            print(f"Error caching artwork: {e}")
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
                print("Downloading Steam app list (first time or cache expired)...")
                response = requests.get("http://api.steampowered.com/ISteamApps/GetAppList/v2/")
                if response.status_code == 200:
                    with open(cache_file, 'w') as f:
                        import json
                        json.dump(response.json(), f)
                    print("Steam app list cached successfully")
                else:
                    print(f"Failed to download Steam app list: {response.status_code}")
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
            print(f"Error searching Steam AppID for {game_name}: {e}")
            
        return None
