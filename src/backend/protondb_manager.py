import os
import requests
import json
import time

class ProtonDBManager:
    CACHE_DIR = os.path.expanduser("~/.cache/gamehub")
    CACHE_FILE = os.path.join(CACHE_DIR, "protondb_cache.json")
    API_URL = "https://www.protondb.com/api/v1/reports/summaries/{}.json"

    def __init__(self):
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading ProtonDB cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Error saving ProtonDB cache: {e}")

    def get_tier(self, appid):
        """Fetches the tier for a given Steam appid. Returns tier string or None."""
        if not appid:
            return None

        # Check cache (expire after 7 days)
        if appid in self.cache:
            entry = self.cache[appid]
            if time.time() - entry.get('timestamp', 0) < 604800:
                return entry.get('tier')

        # Fetch from API
        try:
            url = self.API_URL.format(appid)
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                tier = data.get('trendingTier') or data.get('tier')
                if tier:
                    self.cache[appid] = {
                        'tier': tier,
                        'timestamp': time.time()
                    }
                    self._save_cache()
                    return tier
            elif resp.status_code == 404:
                # Cache negative result for 1 day to avoid spamming
                self.cache[appid] = {
                    'tier': 'unknown',
                    'timestamp': time.time() - 518400 # 6 days ago, so it expires in 1 day
                }
                self._save_cache()
        except Exception as e:
            print(f"Error fetching ProtonDB tier for {appid}: {e}")
        
        return None
