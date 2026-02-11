import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GObject, Pango
import subprocess

class GameCard(Gtk.Box):
    __gsignals__ = {
        'play-clicked': (GObject.SignalFlags.RUN_FIRST, None, (object, bool)), # game, is_stop_request
        'menu-action': (GObject.SignalFlags.RUN_FIRST, None, (object, str)) # game, action_name
    }

    def __init__(self, item=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.item = item
        self.game = item.game if item else None
        
        self.installed = self.game.get('installed', True) if self.game else True
        self.set_css_classes(["game-card"])
        if not self.installed:
            self.add_css_class("uninstalled")
        
        # Enforce fixed size and portrait aspect ratio
        self.set_size_request(198, 297)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.set_hexpand(False)
        self.set_vexpand(False)
        self.set_overflow(Gtk.Overflow.HIDDEN)
        self.set_focusable(True)
 
        # Main Overlay
        self.overlay = Gtk.Overlay()
        self.overlay.set_hexpand(False)
        self.overlay.set_halign(Gtk.Align.CENTER)
        self.overlay.set_size_request(198, 297)
        self.append(self.overlay)
        
        # Aspect Frame for Artwork
        self.aspect_frame = Gtk.AspectFrame(xalign=0.5, yalign=0.5, ratio=0.66, obey_child=False)
        self.aspect_frame.set_hexpand(False)
        self.aspect_frame.set_size_request(198, 297)
        self.overlay.set_child(self.aspect_frame)

        # Background Image (Artwork)
        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.COVER)
        self.picture.set_hexpand(False)
        self.aspect_frame.set_child(self.picture)

        # Load Artwork
        # Delayed to bind()

        # Hover Overlay (Title at bottom)
        self.hover_overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.hover_overlay.set_css_classes(["game-card-overlay"])
        self.hover_overlay.set_valign(Gtk.Align.END)
        self.hover_overlay.set_hexpand(False)
        self.hover_overlay.set_halign(Gtk.Align.CENTER)
        self.hover_overlay.set_size_request(198, -1)
        self.hover_overlay.set_can_target(False)
        self.overlay.add_overlay(self.hover_overlay)

        # Title
        self.title_label = Gtk.Label(label="")
        self.title_label.set_css_classes(["game-card-title"])
        self.title_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.title_label.set_max_width_chars(15) 
        self.title_label.set_xalign(0.5)
        self.title_label.set_hexpand(True)
        self.title_label.set_wrap(False)
        self.hover_overlay.append(self.title_label)
        
        # Playtime Label
        self.playtime_label = Gtk.Label()
        self.playtime_label.set_css_classes(["game-card-playtime"])
        self.playtime_label.set_xalign(0.5)
        self.playtime_label.set_hexpand(True)
        self.playtime_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.playtime_label.set_max_width_chars(15)
        self.hover_overlay.append(self.playtime_label)

        # Play Button (Centered) with Revealer
        self.center_box = Gtk.Box()
        self.center_box.set_halign(Gtk.Align.CENTER)
        self.center_box.set_valign(Gtk.Align.CENTER)
        self.center_box.set_hexpand(False)
        self.center_box.set_css_classes(["play-box"])
        
        self.play_btn = Gtk.Button()
        self.play_btn.set_icon_name("media-playback-start-symbolic")
        self.play_btn.set_css_classes(["circular", "play-button"])
        
        self.play_btn.connect("clicked", self.on_play_clicked)
        self.center_box.append(self.play_btn)
        
        self.play_revealer = Gtk.Revealer()
        self.play_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.play_revealer.set_child(self.center_box)
        self.play_revealer.set_reveal_child(False)
        self.play_revealer.set_hexpand(False)
        self.overlay.add_overlay(self.play_revealer)
        
        # Status Label (Top Right Badge)
        self.status_box = Gtk.Box()
        self.status_box.set_halign(Gtk.Align.END)
        self.status_box.set_valign(Gtk.Align.START)
        self.status_box.set_margin_top(8)
        self.status_box.set_margin_end(8)
        
        self.status_label = Gtk.Label(label="Running")
        self.status_label.set_css_classes(["status-badge"])
        self.status_box.append(self.status_label)
        
        self.status_revealer = Gtk.Revealer()
        self.status_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.status_revealer.set_child(self.status_box)
        self.status_revealer.set_reveal_child(False)
        self.status_revealer.set_valign(Gtk.Align.START)
        self.status_revealer.set_hexpand(False)
        self.status_revealer.set_can_target(False)
        self.overlay.add_overlay(self.status_revealer)

        # ProtonDB Badge (Top Left)
        self.protondb_box = Gtk.Box()
        self.protondb_box.set_halign(Gtk.Align.START)
        self.protondb_box.set_valign(Gtk.Align.START)
        self.protondb_box.set_hexpand(False)
        self.protondb_box.set_margin_top(8)
        self.protondb_box.set_margin_start(8)
        
        self.protondb_label = Gtk.Label()
        self.protondb_label.set_css_classes(["protondb-badge"])
        self.protondb_box.append(self.protondb_label)
        
        self.protondb_revealer = Gtk.Revealer()
        self.protondb_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.protondb_revealer.set_child(self.protondb_box)
        self.protondb_revealer.set_reveal_child(False)
        self.protondb_revealer.set_halign(Gtk.Align.START)
        self.protondb_revealer.set_valign(Gtk.Align.START)
        self.protondb_revealer.set_hexpand(False)
        self.protondb_revealer.set_can_target(False)
        self.overlay.add_overlay(self.protondb_revealer)

        # Controllers
        # Hover controller
        hover_controller = Gtk.EventControllerMotion()
        hover_controller.connect("enter", self.on_enter)
        hover_controller.connect("leave", self.on_leave)
        self.add_controller(hover_controller)

        # Right click gesture
        gesture = Gtk.GestureClick()
        gesture.set_button(3) # Right click
        gesture.connect("pressed", self.on_right_click)
        self.add_controller(gesture)

        self.is_running = False

        if self.item:
            self.bind(self.item)

    def bind(self, item):
        # Disconnect old signals if any
        if hasattr(self, "_notify_protondb_id") and self.item:
            self.item.disconnect(self._notify_protondb_id)
        if hasattr(self, "_notify_running_id") and self.item:
            self.item.disconnect(self._notify_running_id)

        self.item = item
        self.game = item.game
        self.installed = self.game.get('installed', True)
        self.set_title(self.game['name'])
        self._load_artwork()
        self._update_playtime_label(self.game.get('playtime', 0))
        self.set_status(item.is_running)
        
        # Connect signals for live updates
        self._notify_protondb_id = item.connect("notify::protondb-tier", lambda *args: self.set_protondb_tier(item.protondb_tier))
        self._notify_running_id = item.connect("notify::running", lambda *args: self.set_status(item.is_running))
        
        self.set_protondb_tier(item.protondb_tier)
        
        # Update uninstalled class
        if not self.installed:
            self.add_css_class("uninstalled")
        else:
            self.remove_css_class("uninstalled")
            
        # Update button icon
        if self.installed:
            self.play_btn.set_icon_name("media-playback-start-symbolic")
            self.play_btn.remove_css_class("install-button")
            self.play_btn.add_css_class("play-button")
        else:
            self.play_btn.set_icon_name("folder-download-symbolic")
            self.play_btn.remove_css_class("play-button")
            self.play_btn.add_css_class("install-button")

    def set_status(self, running):
        self.is_running = running
        if running:
            self.play_btn.set_icon_name("media-playback-stop-symbolic")
            self.play_btn.remove_css_class("play-button")
            self.play_btn.add_css_class("stop-button")
            self.status_revealer.set_reveal_child(True)
            self.center_box.add_css_class("running")
            self.hover_overlay.set_opacity(1.0)
        else:
            if self.installed:
                self.play_btn.set_icon_name("media-playback-start-symbolic")
                self.play_btn.remove_css_class("stop-button")
                self.play_btn.add_css_class("play-button")
            self.status_revealer.set_reveal_child(False)
            self.center_box.remove_css_class("running")
            self.hover_overlay.set_opacity(0.8)

    def on_right_click(self, gesture, n_press, x, y):

        
        popover = Gtk.Popover()
        popover.set_parent(self) # Attach to self
        popover.set_has_arrow(False)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_spacing(6)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(6)
        box.set_margin_end(6)
        popover.set_child(box)
        
        btn_art = Gtk.Button(label="Edit Artwork")
        btn_art.set_has_frame(False)
        btn_art.connect("clicked", lambda x: (self.emit("menu-action", self.game, "edit_artwork"), popover.popdown()))
        box.append(btn_art)

        # Open Game Folder (Available for everything)
        btn_folder = Gtk.Button(label="Open Game Folder")
        btn_folder.set_has_frame(False)
        btn_folder.connect("clicked", lambda x: (self.emit("menu-action", self.game, "open_game_folder"), popover.popdown()))
        box.append(btn_folder)
        
        if self.game['type'] == 'manual':
            # Edit Settings
            btn_edit = Gtk.Button(label="Configure")
            btn_edit.set_has_frame(False)
            btn_edit.connect("clicked", lambda x: (self.emit("menu-action", self.game, "edit_settings"), popover.popdown()))
            box.append(btn_edit)

            # Open Prefix Folder
            btn_prefix = Gtk.Button(label="Open Prefix Folder")
            btn_prefix.set_has_frame(False)
            btn_prefix.connect("clicked", lambda x: (self.emit("menu-action", self.game, "open_prefix_folder"), popover.popdown()))
            box.append(btn_prefix)

            # Run without Proton
            btn_native = Gtk.Button(label="Run without Proton")
            btn_native.set_has_frame(False)
            btn_native.connect("clicked", lambda x: (self.emit("menu-action", self.game, "run_without_proton"), popover.popdown()))
            box.append(btn_native)

            # Separator
            box.append(Gtk.Separator())

            btn_del = Gtk.Button(label="Delete")
            btn_del.set_has_frame(False)
            btn_del.get_style_context().add_class("destructive-action")
            btn_del.connect("clicked", lambda x: (self.emit("menu-action", self.game, "delete"), popover.popdown()))
            box.append(btn_del)

        # Convert local coordinates to be relative to the popover's parent
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.popup()

    def _load_artwork(self):
        if not self.game:
            return
        artwork_path = self.game.get('artwork')
        if artwork_path:
            if "://" in artwork_path:
                f = Gio.File.new_for_uri(artwork_path)
            else:
                f = Gio.File.new_for_path(artwork_path)
            self.picture.set_file(f)
        else:
            # Fallback icon
            icon_name = "applications-games-symbolic" if self.game['type'] == 'manual' else "steam"
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            if icon_theme.has_icon(icon_name):
                self.picture.set_paintable(icon_theme.lookup_icon(icon_name, None, 128, 1, Gtk.TextDirection.NONE, 0))

    def on_enter(self, controller, x, y):
        self.play_revealer.set_reveal_child(True)
        self.hover_overlay.set_opacity(1.0)

    def on_leave(self, controller):
        self.play_revealer.set_reveal_child(False)
        self.hover_overlay.set_opacity(0.8)

    def on_play_clicked(self, btn):
        if not self.installed:
            # Trigger Steam install
            subprocess.run(["xdg-open", f"steam://install/{self.game['id']}"])
            return

        if self.is_running:
            self.emit('play-clicked', self.game, True) # True = stop request
        else:
            self.emit('play-clicked', self.game, False) # False = start request

    def set_title(self, name):
        self.game['name'] = name
        self.title_label.set_text(name)

    def set_protondb_tier(self, tier):
        """Update the ProtonDB tier badge"""
        if not tier or tier == "unknown":
            self.protondb_revealer.set_reveal_child(False)
            return

        self.protondb_label.set_text(tier.capitalize())
        
        # Remove old specific classes
        for cls in ["platinum", "gold", "silver", "bronze", "borked"]:
            self.protondb_label.remove_css_class(cls)
            
        self.protondb_label.add_css_class(tier.lower())
        self.protondb_revealer.set_reveal_child(True)

    def _update_playtime_label(self, seconds):
        """Format and update playtime label"""
        hours = seconds / 3600
        if hours >= 1:
            self.playtime_label.set_text(f"{hours:.1f} hours played")
        else:
            minutes = seconds / 60
            self.playtime_label.set_text(f"{int(minutes)} minutes played")
