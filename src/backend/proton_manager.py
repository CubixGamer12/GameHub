import os
import requests
import tarfile
import threading
import shutil
import json

class ProtonManager:
    SOURCES = {
        "ge": "GloriousEggroll/proton-ge-custom",
        "cachyos": "CachyOS/proton-cachyos"
    }
    INSTALL_DIR = os.path.expanduser("~/.local/share/gamehub/proton")

    def __init__(self):
        os.makedirs(self.INSTALL_DIR, exist_ok=True)

    def get_available_releases(self, source="ge"):
        """Fetches a list of all available releases for a specific source."""
        repo = self.SOURCES.get(source, self.SOURCES["ge"])
        url = f"https://api.github.com/repos/{repo}/releases"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                releases = []
                for release in resp.json():
                    tag_name = release.get("tag_name")
                    assets = release.get("assets", [])
                    download_url = None
                    for asset in assets:
                        if asset["name"].endswith(".tar.gz") or asset["name"].endswith(".tar.xz"):
                            download_url = asset["browser_download_url"]
                            break
                    if tag_name and download_url:
                        releases.append((tag_name, download_url))
                return releases
        except Exception as e:
            print(f"Error fetching {source} releases: {e}")
        return []

    def get_installed_versions(self):
        """Returns a list of installed Proton versions folder names."""
        if not os.path.exists(self.INSTALL_DIR):
            return []
        return [d for d in os.listdir(self.INSTALL_DIR) 
                if os.path.isdir(os.path.join(self.INSTALL_DIR, d)) and ("Proton" in d or "proton" in d.lower())]

    def check_latest_release(self, source="ge"):
        """Fetches the latest release tag name and download URL for a source."""
        repo = self.SOURCES.get(source, self.SOURCES["ge"])
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                tag_name = data.get("tag_name")
                assets = data.get("assets", [])
                download_url = None
                
                for asset in assets:
                    if asset["name"].endswith(".tar.gz"):
                        download_url = asset["browser_download_url"]
                        break
                
                return tag_name, download_url
        except Exception as e:
            print(f"Error checking {source} release: {e}")
        return None, None

    def download_and_install(self, download_url, version_tag, progress_callback=None, completion_callback=None):
        """
        Downloads and installs Proton-GE in a background thread.
        progress_callback: function(float) -> None (0.0 to 1.0)
        completion_callback: function(bool, str) -> None (success, message)
        """
        def _download():
            try:
                extension = ".tar.gz" if download_url.endswith(".tar.gz") else ".tar.xz"
                temp_file = os.path.join(self.INSTALL_DIR, f"{version_tag}{extension}")
                
                # Download
                print(f"Downloading {version_tag} from {download_url}")
                with requests.get(download_url, stream=True) as r:
                    r.raise_for_status()
                    total_length = r.headers.get('content-length')
                    
                    if total_length is None: # no content length header
                        with open(temp_file, 'wb') as f:
                            f.write(r.content)
                        if progress_callback:
                            progress_callback(0.5)
                    else:
                        dl = 0
                        total_length = int(total_length)
                        with open(temp_file, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    dl += len(chunk)
                                    f.write(chunk)
                                    if progress_callback:
                                        progress_callback(dl / total_length)

                # Extract
                print(f"Extracting {temp_file}...")
                mode = "r:gz" if temp_file.endswith(".tar.gz") else "r:xz"
                with tarfile.open(temp_file, mode) as tar:
                    tar.extractall(path=self.INSTALL_DIR)
                
                # Cleanup
                os.remove(temp_file)
                
                if completion_callback:
                    completion_callback(True, f"Successfully installed {version_tag}")
                    
            except Exception as e:
                print(f"Installation failed: {e}")
                if completion_callback:
                    completion_callback(False, str(e))

        thread = threading.Thread(target=_download)
        thread.start()

