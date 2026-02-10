import configparser
import os

class SettingsManager:
    def __init__(self):
        self.config_dir = os.path.expanduser("~/.config/gamehub")
        self.settings_file = os.path.join(self.config_dir, "configuration.conf")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config = configparser.ConfigParser()
        self._load_settings()

    def _load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                self.config.read(self.settings_file)
            except:
                self.config["Settings"] = {}
        
        if "Settings" not in self.config:
            self.config["Settings"] = {}

    def get(self, key, default=None):
        return self.config["Settings"].get(key, default)

    def set(self, key, value):
        if value is None:
            # ConfigParser doesn't like None, remove the key or set to empty string
            if key in self.config["Settings"]:
                del self.config["Settings"][key]
        else:
            self.config["Settings"][key] = str(value)
        self._save()

    def _save(self):
        with open(self.settings_file, 'w') as f:
            self.config.write(f)
