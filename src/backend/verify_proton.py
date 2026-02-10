from .proton_manager import ProtonManager
import os

def test_proton_manager():
    pm = ProtonManager()
    
    print("Checking for latest release...")
    tag, url = pm.check_latest_release()
    
    if tag and url:
        print(f"Success! Found tag: {tag}")
        print(f"Download URL: {url}")
    else:
        print("Failed to fetch latest release.")
        
    print(f"Installed versions: {pm.get_installed_versions()}")

if __name__ == "__main__":
    test_proton_manager()
