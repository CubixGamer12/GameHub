import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject
from ui.widgets.game_card import GameCard

class LibraryPage(Adw.Bin):
    __gsignals__ = {
        'game-launched': (GObject.SignalFlags.RUN_FIRST, None, (object, bool)),
        'menu-action': (GObject.SignalFlags.RUN_FIRST, None, (object, str))
    }

    def __init__(self):
        super().__init__()

        # Scrolled Window
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_hexpand(True)
        self.set_child(self.scrolled)

        # FlowBox
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(30)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_activate_on_single_click(False) # Important: Allow child buttons to get clicks
        self.flowbox.set_column_spacing(20)
        self.flowbox.set_row_spacing(20)
        self.flowbox.set_margin_top(20)
        self.flowbox.set_margin_bottom(20)
        self.flowbox.set_margin_start(20)
        self.flowbox.set_margin_end(20)
        
        self.scrolled.set_child(self.flowbox)

    def set_games(self, games):
        # Clear existing
        child = self.flowbox.get_first_child()
        while child:
            self.flowbox.remove(child)
            child = self.flowbox.get_first_child()

        # Add new
        for game in games:
            card = GameCard(game)
            card.connect('play-clicked', self.on_play_clicked)
            card.connect('menu-action', lambda c, g, a: self.emit('menu-action', g, a))
            self.flowbox.append(card)

    def on_play_clicked(self, card, game, is_stop_request):
        self.emit('game-launched', game, is_stop_request)

    def update_game_status(self, game_id, is_running):
        # Iterate over children to find the card
        child = self.flowbox.get_first_child()
        while child:
            card = child
            if card.game['id'] == game_id:
                card.set_status(is_running)
                break
            child = child.get_next_sibling()

    def update_protondb_status(self, game_id, tier):
        child = self.flowbox.get_first_child()
        while child:
            card = child
            if str(card.game['id']) == str(game_id):
                card.set_protondb_tier(tier)
                break
            child = child.get_next_sibling()
        return False
