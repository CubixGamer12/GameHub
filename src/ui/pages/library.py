import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject
from ui.models.game_item import GameItem
from ui.widgets.game_card import GameCard
from gi.repository import Gio

class LibraryPage(Adw.Bin):
    __gsignals__ = {
        'game-launched': (GObject.SignalFlags.RUN_FIRST, None, (object, bool)),
        'menu-action': (GObject.SignalFlags.RUN_FIRST, None, (object, str))
    }

    def __init__(self):
        super().__init__()

        # Main Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.main_box)

        # Header with Search
        self.header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.header.add_css_class("library-header")
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search library...")
        self.search_entry.set_hexpand(True)
        self.search_entry.add_css_class("library-search")
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.header.append(self.search_entry)
        
        self.main_box.append(self.header)

        # Scrolled Window
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_hexpand(True)
        self.main_box.append(self.scrolled)

        # Filtering state
        self.search_query = ""
        self.show_uninstalled = False
        self.hide_borked = False

        # Store for games
        self.store = Gio.ListStore(item_type=GameItem)
        
        # Filter Model
        self.filter = Gtk.CustomFilter()
        self.filter.set_filter_func(self._filter_func)
        
        self.filter_model = Gtk.FilterListModel(model=self.store, filter=self.filter)

        # GridView
        self.grid = Gtk.GridView()
        self.grid.set_valign(Gtk.Align.START)
        self.grid.set_halign(Gtk.Align.START)
        self.grid.set_max_columns(20)
        self.grid.set_min_columns(1)
        self.grid.set_enable_rubberband(False)
        
        # Factory
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)
        self.grid.set_factory(factory)

        # Selection Model (Use filter_model)
        self.selection = Gtk.NoSelection(model=self.filter_model)
        self.grid.set_model(self.selection)
        
        self.grid.set_margin_top(20)
        self.grid.set_margin_bottom(20)
        self.grid.set_margin_start(20)
        self.grid.set_margin_end(20)
        
        self.scrolled.set_child(self.grid)

    def _on_search_changed(self, entry):
        self.search_query = entry.get_text().lower()
        self.filter.changed(Gtk.FilterChange.DIFFERENT)

    def set_show_uninstalled(self, show):
        self.show_uninstalled = show
        self.filter.changed(Gtk.FilterChange.DIFFERENT)

    def set_hide_borked(self, hide):
        self.hide_borked = hide
        self.filter.changed(Gtk.FilterChange.DIFFERENT)

    def _filter_func(self, item):
        # 1. Search Query
        if self.search_query and self.search_query not in item.title.lower():
            return False
            
        # 2. Uninstalled Games
        if not self.show_uninstalled and not item.game.get('installed', True):
            return False
            
        # 3. Borked Games
        if self.hide_borked and item.protondb_tier == "borked":
            return False
            
        return True

    def _on_factory_setup(self, factory, list_item):
        card = GameCard()
        card.connect('play-clicked', self.on_play_clicked)
        card.connect('menu-action', lambda c, g, a: self.emit('menu-action', g, a))
        list_item.set_child(card)

    def _on_factory_bind(self, factory, list_item):
        card = list_item.get_child()
        item = list_item.get_item()
        card.bind(item)

    def set_games(self, games):
        # Clear existing
        self.store.remove_all()

        # Create items
        items = []
        for game in games:
            items.append(GameItem(game))
            
        # Add all at once using splice for performance
        if items:
            self.store.splice(0, 0, items)

    def on_play_clicked(self, card, game, is_stop_request):
        self.emit('game-launched', game, is_stop_request)

    def update_game_status(self, game_id, is_running):
        for i in range(self.store.get_n_items()):
            item = self.store.get_item(i)
            if item.id == str(game_id):
                item.update_status(is_running)
                break

    def update_protondb_status(self, game_id, tier):
        for i in range(self.store.get_n_items()):
            item = self.store.get_item(i)
            if str(item.id) == str(game_id):
                item.update_protondb_tier(tier)
                break
        return False
