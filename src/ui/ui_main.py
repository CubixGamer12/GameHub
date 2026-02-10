import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Adw, Gio, GObject, Pango

class HoverPreview(Gtk.Box):
    def __init__(self, game, parent_tile):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_css_classes(["hover-preview-content"])
        self.game = game
        
        # Container to force size
        self.set_size_request(140, 200)
        
        overlay = Gtk.Overlay()
        self.append(overlay)
        
        picture = Gtk.Picture()
        picture.set_content_fit(Gtk.ContentFit.COVER)
        if game.get('artwork'):
            file = Gio.File.new_for_uri(game['artwork']) if ":" in game['artwork'] else Gio.File.new_for_path(game['artwork'])
            picture.set_file(file)
        else:
            icon_theme = Gtk.IconTheme.get_for_display(self.get_display())
            icon_name = "application-x-executable" if game['type'] == 'manual' else "steam"
            picture.set_paintable(icon_theme.lookup_icon(icon_name, None, 128, 1, Gtk.TextDirection.NONE, 0))
        
        picture.set_css_classes(["hover-preview-art"])
        overlay.set_child(picture)
        
        # Details overlay
        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        details.set_css_classes(["game-tile-details"])
        
        play_area = Gtk.Box()
        play_area.set_vexpand(True)
        play_area.set_halign(Gtk.Align.CENTER)
        play_area.set_valign(Gtk.Align.CENTER)
        
        play_btn = Gtk.Button()
        play_btn.set_icon_name("media-playback-start-symbolic")
        play_btn.set_css_classes(["circular", "play-button-premium"])
        play_btn.set_tooltip_text(f"Play {game['name']}")
        play_btn.connect("clicked", lambda x: parent_tile.activate())
        play_area.append(play_btn)
        details.append(play_area)
        
        title_label = Gtk.Label(label=game['name'])
        title_label.set_css_classes(["game-tile-title"])
        title_label.set_ellipsize(Pango.EllipsizeMode.END)
        title_label.set_margin_bottom(8)
        details.append(title_label)
        
        overlay.add_overlay(details)

class GameTile(Gtk.FlowBoxChild):
    def __init__(self, game):
        super().__init__()
        self.game = game
        
        self.set_css_classes(["game-tile-container"])
        self.set_size_request(70, 100)
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_hexpand(False)
        self.set_vexpand(False)

        # Force aspect ratio
        aspect = Gtk.AspectFrame.new(0.5, 0.5, 70/100, False)
        self.set_child(aspect)

        self.card = Gtk.Box()
        self.card.set_css_classes(["game-tile-card"])
        aspect.set_child(self.card)

        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.COVER)
        self.picture.set_can_shrink(False)
        self.picture.set_size_request(70, 100)
        self.card.append(self.picture)
        
        if game.get('artwork'):
            file = Gio.File.new_for_uri(game['artwork']) if ":" in game['artwork'] else Gio.File.new_for_path(game['artwork'])
            self.picture.set_file(file)
        else:
            icon_theme = Gtk.IconTheme.get_for_display(self.get_display())
            icon_name = "application-x-executable" if game['type'] == 'manual' else "steam"
            self.picture.set_paintable(icon_theme.lookup_icon(icon_name, None, 128, 1, Gtk.TextDirection.NONE, 0))

        # Native Popover
        self.popover = Gtk.Popover()
        self.popover.set_parent(self)
        self.popover.set_autohide(True)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        self.popover.set_has_arrow(False)
        self.popover.set_css_classes(["premium-popover"])
        
        self.preview_content = HoverPreview(game, self)
        self.popover.set_child(self.preview_content)

        # Motion controller
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self.on_mouse_enter)
        self.add_controller(motion)

    def on_mouse_enter(self, controller, x, y):
        # Only popup if not already visible to avoid flickering
        if not self.popover.get_visible():
            self.popover.popup()
            self.add_css_class("tile-hovered")

    # Removed on_mouse_leave popdown to allow moving mouse into the popover.
    # Gtk.Popover(autohide=True) will handle closing when clicking outside or moving far away.

class GameHubWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("GameHub")
        self.set_default_size(1000, 750)

        self._load_css()
        
        # Global Horizontal Box (Main area + Sidebar)
        self.main_h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_content(self.main_h_box)

        # Left side: Content area
        self.content_v_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_v_box.set_hexpand(True)
        self.content_v_box.set_vexpand(True)
        self.main_h_box.append(self.content_v_box)

        # Header
        header = Adw.HeaderBar()
        self.content_v_box.append(header)

        add_button = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_button.connect("clicked", self.on_add_clicked)
        header.pack_start(add_button)

        refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_button.connect("clicked", self.on_refresh_clicked)
        header.pack_end(refresh_button)

        # Stack for different categories
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        self.content_v_box.append(self.stack)

        # Steam FlowBox
        self.steam_flow = self._create_flow_box()
        scrolled_steam = Gtk.ScrolledWindow()
        scrolled_steam.set_child(self.steam_flow)
        scrolled_steam.set_vexpand(True)
        scrolled_steam.set_hexpand(True)
        scrolled_steam.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.stack.add_titled(scrolled_steam, "steam", "Steam")

        # Manual FlowBox
        self.manual_flow = self._create_flow_box()
        scrolled_manual = Gtk.ScrolledWindow()
        scrolled_manual.set_child(self.manual_flow)
        scrolled_manual.set_vexpand(True)
        scrolled_manual.set_hexpand(True)
        scrolled_manual.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.stack.add_titled(scrolled_manual, "manual", "Manual")

        # Right side: Sidebar (Category Selector)
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar_box.set_css_classes(["sidebar-area"])
        self.sidebar_box.set_size_request(200, -1)
        self.main_h_box.append(self.sidebar_box)

        sidebar_title = Gtk.Label(label="Libraries")
        sidebar_title.set_css_classes(["heading", "sidebar-header"])
        sidebar_title.set_margin_top(18)
        sidebar_title.set_margin_bottom(12)
        self.sidebar_box.append(sidebar_title)

        # Sidebar Switcher
        self.sidebar_nav = Gtk.StackSidebar()
        self.sidebar_nav.set_stack(self.stack)
        self.sidebar_nav.set_vexpand(True)
        self.sidebar_nav.set_css_classes(["sidebar-switcher"])
        self.sidebar_box.append(self.sidebar_nav)

    def _create_flow_box(self):
        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_halign(Gtk.Align.START)
        flow.set_max_children_per_line(20)
        flow.set_min_children_per_line(1)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_column_spacing(12)
        flow.set_row_spacing(12)
        flow.set_margin_top(24)
        flow.set_margin_bottom(24)
        flow.set_margin_start(24)
        flow.set_margin_end(24)
        return flow

    def on_refresh_clicked(self, button):
        self.emit("refresh-games")

    def on_add_clicked(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Windows Executable")
        
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Windows Executables")
        file_filter.add_pattern("*.exe")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)
        dialog.set_filters(filters)

        dialog.open(self, None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.emit("add-manual-game", path)
        except:
            pass

    def update_game_list(self, steam_games, manual_games):
        # Update Steam
        self._clear_flow(self.steam_flow)
        for game in steam_games:
            self.steam_flow.append(self._create_tile(game))

        # Update Manual
        self._clear_flow(self.manual_flow)
        for game in manual_games:
            self.manual_flow.append(self._create_tile(game))

    def _clear_flow(self, flow):
        child = flow.get_first_child()
        while child:
            flow.remove(child)
            child = flow.get_first_child()

    def _create_tile(self, game):
        tile = GameTile(game)
        tile.connect("activate", self.on_game_activated)
        return tile

    def on_game_activated(self, tile):
        self.emit("game-launched", tile.game)

    def _load_css(self):
        css = b"""
        /* Global & Sidebar */
        .sidebar-area {
            background-color: @window_bg_color;
            border-left: 1px solid @borders;
            box-shadow: inset 2px 0 10px rgba(0,0,0,0.1);
        }
        .sidebar-header {
            opacity: 0.5;
            font-size: 0.8em;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-left: 20px;
        }
        .sidebar-switcher button {
            margin: 4px 12px;
            padding: 10px 16px;
            border-radius: 10px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .sidebar-switcher button:hover {
            background-color: alpha(@accent_color, 0.1);
        }

        /* Game Tile System */
        .game-tile-container {
            background: none;
            padding: 0;
            margin: 0;
            border: none;
            transition: all 0.2s ease;
        }

        .game-tile-card {
            border-radius: 8px;
            background: @card_bg_color;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
            transition: opacity 0.2s ease;
        }

        .tile-hovered .game-tile-card {
            opacity: 0.5;
        }

        /* Native Popover Premium Styling */
        popover.premium-popover contents {
            padding: 0;
            background: none;
            box-shadow: none;
            border: none;
        }

        .hover-preview-content {
            border-radius: 12px;
            background: @card_bg_color;
            box-shadow: 0 12px 40px rgba(0,0,0,0.6);
            overflow: hidden;
            margin: -8px; /* Offset popover default padding */
        }

        .hover-preview-art {
            filter: blur(2px) brightness(0.6);
        }

        .game-tile-details {
            color: white;
            padding: 8px;
        }

        .game-tile-title {
            font-size: 12px;
            font-weight: bold;
            margin-top: 10px;
            text-align: center;
        }

        /* Premium Play Button */
        .play-button-premium {
            background: @accent_bg_color;
            color: @accent_fg_color;
            border-radius: 99px;
            padding: 12px;
            transition: all 0.2s ease;
        }
        .play-button-premium:hover {
            background: @accent_bg_color;
            transform: scale(1.1);
        }
        .play-button-premium icon {
            -gtk-icon-size: 24px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

# Register signals
GObject.signal_new("refresh-games", GameHubWindow, GObject.SignalFlags.RUN_FIRST, None, ())
GObject.signal_new("add-manual-game", GameHubWindow, GObject.SignalFlags.RUN_FIRST, None, (str,))
GObject.signal_new("game-launched", GameHubWindow, GObject.SignalFlags.RUN_FIRST, None, (object,))
