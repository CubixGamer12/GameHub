import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject
from ui.pages.library import LibraryPage
from ui.dialogs.artwork_dialog import ArtworkDialog
from ui.dialogs.add_game_dialog import AddGameDialog
import os
import subprocess
import shutil

class GameHubWindow(Adw.ApplicationWindow):
    __gsignals__ = {
        'refresh-games': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'add-manual-game': (GObject.SignalFlags.RUN_FIRST, None, (str, str, str, str, bool, str, object, bool)), # name, path, runner, version, use_global_args, args, artwork_dict, onlinefix_enabled
        'update-manual-game': (GObject.SignalFlags.RUN_FIRST, None, (str, str, str, str, str, bool, str, object, bool)), # id, name, path, runner, version, use_global_args, args, artwork_dict, onlinefix_enabled
        'game-launched': (GObject.SignalFlags.RUN_FIRST, None, (object,)),
        'open-settings': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, application, steam_scanner, config, art_manager, proton_manager, settings_manager, session_manager):
        super().__init__(application=application)
        self.set_title("GameHub")
        self.set_default_size(1000, 750)

        self.steam_scanner = steam_scanner
        self.config = config
        self.art_manager = art_manager
        self.proton_manager = proton_manager
        self.settings_manager = settings_manager
        self.session_manager = session_manager
        
        # Connect Session Signals
        self.session_manager.connect('game-started', self.on_game_started)
        self.session_manager.connect('game-stopped', self.on_game_stopped)

        # Main Content Overlay (for Toasts)
        self.overlay = Adw.ToastOverlay()
        self.set_content(self.overlay)

        # Main Layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.overlay.set_child(self.main_box)

        # Header Bar
        self.header_bar = Adw.HeaderBar()
        self.main_box.append(self.header_bar)

        # Header Buttons
        self.add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        self.add_btn.set_tooltip_text("Add Manual Game")
        self.add_btn.connect("clicked", self.on_add_clicked)
        self.header_bar.pack_start(self.add_btn)

        self.refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.refresh_btn.set_tooltip_text("Refresh Library")
        self.refresh_btn.connect("clicked", self.on_refresh_clicked)
        self.header_bar.pack_end(self.refresh_btn)

        # Settings Button
        self.settings_btn = Gtk.Button.new_from_icon_name("preferences-system-symbolic")
        self.settings_btn.set_tooltip_text("Settings")
        self.settings_btn.connect("clicked", self.on_settings_clicked)
        self.header_bar.pack_end(self.settings_btn)

        # Stack for tabs
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_box.append(self.stack)

        # Steam Page
        self.steam_page = LibraryPage()
        self.steam_page.connect('game-launched', self.on_game_launched_sub)
        self.steam_page.connect('menu-action', self.on_menu_action)
        self.stack.add_titled(self.steam_page, "steam", "Steam")

        # Manual Page
        self.manual_page = LibraryPage()
        self.manual_page.connect('game-launched', self.on_game_launched_sub)
        self.manual_page.connect('menu-action', self.on_menu_action)
        self.stack.add_titled(self.manual_page, "manual", "Manual")
        
        # Heroic Page
        self.heroic_page = LibraryPage()
        self.heroic_page.connect('game-launched', self.on_game_launched_sub)
        self.heroic_page.connect('menu-action', self.on_menu_action)
        self.stack.add_titled(self.heroic_page, "heroic", "Heroic")
        
        # Settings Page (Not in stack, usually separate window or modal)
        # But AdwPreferencesWindow requires a window. 
        # Let's simple show it as a separate window when clicked.

        # Stack Switcher
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.header_bar.set_title_widget(self.stack_switcher)

        self._load_css()

    def update_game_list(self, steam_games, manual_games, heroic_games):
        self.steam_page.set_games(steam_games)
        self.manual_page.set_games(manual_games)
        self.heroic_page.set_games(heroic_games)

    def on_refresh_clicked(self, btn):
        self.emit("refresh-games")

    def on_settings_clicked(self, btn):
        self.emit("open-settings")


    def on_add_clicked(self, btn):
        dialog = AddGameDialog(self, self.session_manager.runner)
        dialog.connect("save-game", self.on_add_game_dialog_finished)
        dialog.present()

    def on_add_game_dialog_finished(self, dialog, name, path, runner, version, use_global, args, art_dict, onlinefix_enabled):
        self.emit("add-manual-game", name, path, runner, version, use_global, args, art_dict, onlinefix_enabled)

    def _show_edit_dialog(self, game):
        dialog = AddGameDialog(self, self.session_manager.runner, game=game)
        dialog.connect("save-game", lambda d, n, p, r, v, ug, a, art, of: self.on_edit_dialog_finished(d, game['id'], n, p, r, v, ug, a, art, of))
        dialog.present()

    def on_edit_dialog_finished(self, dialog, game_id, name, path, runner, version, use_global, args, art_dict, onlinefix_enabled):
        self.emit("update-manual-game", game_id, name, path, runner, version, use_global, args, art_dict, onlinefix_enabled)

    def on_game_launched_sub(self, page, game, is_stop_request):
        if is_stop_request:
            self.session_manager.stop_game(game['id'])
        else:
            self.session_manager.launch_game(game)

            # Notification
            toast = Adw.Toast.new(f"Starting {game['name']}...")
            toast.set_timeout(3)
            self.overlay.add_toast(toast)

    def on_game_started(self, session, game):
        # Update UI in pages
        if game['type'] == 'manual':
            self.manual_page.update_game_status(game['id'], True)
        elif game['type'] == 'steam':
            self.steam_page.update_game_status(game['id'], True)
            
    def on_game_stopped(self, session, game):
        if game['type'] == 'manual':
            self.manual_page.update_game_status(game['id'], False)
        elif game['type'] == 'steam':
            self.steam_page.update_game_status(game['id'], False)

    def on_menu_action(self, page, game, action):
        print(f"DEBUG: Menu action '{action}' triggered for game: {game['name']} (ID: {game['id']})")
        
        if action == "delete":
            self._confirm_delete(game)
            
        elif action == "edit_artwork":
            self._show_artwork_dialog(game)

        elif action == "edit_settings":
            self._show_edit_dialog(game)

        elif action == "open_game_folder":
            path = game.get('path')
            print(f"DEBUG: Opening game folder. Path in game object: {path}")
            if path:
                if os.path.isdir(path):
                    folder = path
                else:
                    folder = os.path.dirname(path)
                
                if os.path.exists(folder):
                    self.overlay.add_toast(Adw.Toast.new(f"Opening {game['name']} folder..."))
                    self._open_folder(folder)
                else:
                    print(f"ERROR: Folder does not exist: {folder}")
                    self.overlay.add_toast(Adw.Toast.new(f"Error: Folder not found"))
            else:
                print(f"ERROR: No path found for game {game['name']}")
                self.overlay.add_toast(Adw.Toast.new(f"No installation path found"))

        elif action == "open_prefix_folder":
            prefix_path = os.path.expanduser(f"~/.local/share/gamehub/prefixes/{game['id']}")
            print(f"DEBUG: Opening prefix folder: {prefix_path}")
            if os.path.exists(prefix_path):
                self.overlay.add_toast(Adw.Toast.new(f"Opening prefix folder..."))
                self._open_folder(prefix_path)
            else:
                print(f"ERROR: Prefix folder does not exist: {prefix_path}")
                self.overlay.add_toast(Adw.Toast.new(f"Prefix folder not created yet"))

        elif action == "run_without_proton":
            self.overlay.add_toast(Adw.Toast.new(f"Launching {game['name']} natively..."))
            self.session_manager.launch_game_native(game)

    def _open_folder(self, folder):
        """Robustly open a folder in the graphical file manager, avoiding terminals"""
        if not os.path.exists(folder):
            print(f"CRITICAL: Folder does not exist: {folder}")
            return

        folder = os.path.abspath(folder)
        file_obj = Gio.File.new_for_path(folder)
        uri = file_obj.get_uri()
        print(f"DEBUG: Attempting to open folder in GUI: {folder}")

        # Method 1: D-Bus (The most reliable way to trigger a graphical file manager)
        try:
            # org.freedesktop.FileManager1 is supported by Nautilus, Dolphin, Thunar, etc.
            subprocess.Popen([
                "dbus-send", "--session", "--dest=org.freedesktop.FileManager1",
                "--type=method_call", "/org/freedesktop/FileManager1",
                "org.freedesktop.FileManager1.ShowFolders",
                f"array:string:{uri}", "string: "
            ])
            print("SUCCESS: Triggered via D-Bus org.freedesktop.FileManager1")
            return
        except Exception as e:
            print(f"INFO: D-Bus trigger failed: {e}")

        # Method 2: DE-specific explicit calls (Bypass mime-type messiness)
        session = os.environ.get('DESKTOP_SESSION', '').lower()
        xdg_current = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
        
        if 'kde' in session or 'plasma' in xdg_current:
            if shutil.which("dolphin"):
                subprocess.Popen(["dolphin", folder])
                print("SUCCESS: Explicitly opened via dolphin")
                return
        elif 'gnome' in session or 'gnome' in xdg_current:
            if shutil.which("nautilus"):
                subprocess.Popen(["nautilus", folder])
                print("SUCCESS: Explicitly opened via nautilus")
                return

        # Method 3: Gtk.FileLauncher (Only as fallback now)
        try:
            from gi.repository import Gtk as Gtk4
            if hasattr(Gtk4, 'FileLauncher'):
                launcher = Gtk4.FileLauncher.new(file_obj)
                launcher.launch(self, None, None)
                print(f"INFO: Attempted via Gtk.FileLauncher")
                return
        except Exception:
            pass

        # Method 4: xdg-open
        try:
            subprocess.Popen(["xdg-open", folder])
            print(f"INFO: Attempted via xdg-open")
            return
        except Exception:
            pass

        # Method 5: Last resort list
        for fm in ["dolphin", "nautilus", "thunar", "pcmanfm", "caja", "nemo"]:
            if shutil.which(fm):
                try:
                    subprocess.Popen([fm, folder])
                    print(f"SUCCESS: Opened via explicit fallback {fm}")
                    return
                except Exception:
                    continue


    def _confirm_delete(self, game):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Game?",
            body=f"Are you sure you want to remove '{game['name']}' from your library?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        def response_cb(dialog, response):
            if response == "delete":
                app = self.get_application()
                app.config.delete_game(game['id'])
                self.emit("refresh-games")
        
        dialog.connect("response", response_cb)
        dialog.present()

    def _show_artwork_dialog(self, game):
        dialog = ArtworkDialog(self)
        
        def on_artwork_selected(dlg, type, value):
            app = self.get_application()
            if type == "file":
                # Cache and update
                new_path = app.art_manager.cache_local_image(value, game['id'])
                if new_path:
                    if game['type'] == 'heroic':
                        app.config.update_heroic_artwork(game['id'], new_path)
                    else:
                        app.config.update_game_artwork(game['id'], new_path)
            elif type == "steam":
                # Download and update (or just use URL for Steam artwork)
                if game['type'] == 'heroic':
                    # For Heroic, just store the Steam CDN URL directly
                    steam_url = app.art_manager.get_steam_artwork_url(value)
                    app.config.update_heroic_artwork(game['id'], steam_url)
                else:
                    new_path = app.art_manager.download_steam_artwork(value, game['id'])
                    if new_path:
                        app.config.update_game_artwork(game['id'], new_path)
            
            self.emit("refresh-games")

        dialog.connect("artwork-selected", on_artwork_selected)
        dialog.present()

    def _load_css(self):
        css = b"""
        .game-card {
            background-color: @card_bg_color;
            border-radius: 12px;
            margin: 0;
            padding: 0;
            transition: transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        .game-card:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 15px alpha(black, 0.3);
        }
        .game-card picture {
            border-radius: 12px;
        }
        .game-card-overlay {
            background: linear-gradient(to top, rgba(0,0,0,0.9), rgba(0,0,0,0));
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
            padding: 12px;
        }
        .game-card-title {
            color: white;
            font-weight: bold;
            text-shadow: 0 1px 2px black;
        }
        .game-card-playtime {
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.85rem;
        }
        .play-button {
            background-color: @accent_bg_color;
            color: @accent_fg_color;
            border-radius: 9999px;
            padding: 16px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        }
        .play-button:hover {
            transform: scale(1.1);
        }
        .play-box {
            opacity: 0;
            transition: opacity 0.2s ease-in-out;
        }
        .game-card:hover .play-box {
            opacity: 1;
        }
        .play-box.running {
            opacity: 1;
        }
        .status-badge {
            background-color: @error_bg_color;
            color: @error_fg_color;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.75rem;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
