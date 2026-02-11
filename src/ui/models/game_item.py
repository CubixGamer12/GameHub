from gi.repository import GObject

class GameItem(GObject.Object):
    """GObject wrapper for game data to be used in Gtk.GridView"""
    def __init__(self, game_dict):
        super().__init__()
        self.game = game_dict
        self.id = str(game_dict.get('id', ''))
        self.name = game_dict.get('name', 'Unknown Game')
        self.installed = game_dict.get('installed', True)
        self.artwork = game_dict.get('artwork')
        self.playtime = game_dict.get('playtime', 0)
        self.type = game_dict.get('type', 'manual')
        self._protondb_tier = game_dict.get('protondb_tier')
        self.is_running = False

    def update_status(self, is_running):
        self.is_running = is_running
        self.notify("running")

    def update_protondb_tier(self, tier):
        self._protondb_tier = tier
        self.game['protondb_tier'] = tier
        self.notify("protondb-tier")

    @GObject.Property(type=str, default="")
    def protondb_tier(self):
        return self._protondb_tier or ""

    @GObject.Property(type=str, default="")
    def title(self):
        return self.name

    @GObject.Property(type=bool, default=False)
    def running(self):
        return self.is_running
