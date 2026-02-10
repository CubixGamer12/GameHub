import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject
import os

class AddGameDialog(Adw.Window):
    __gsignals__ = {
        'save-game': (GObject.SignalFlags.RUN_FIRST, None, (str, str, str, str, bool, str, object, bool)), # name, path, runner, version, use_global_args, args, artwork_dict, onlinefix_enabled
    }

    def __init__(self, parent_window, runner, game=None):
        super().__init__(transient_for=parent_window, modal=True)
        self.game = game
        self.runner = runner
        self.set_title("Add Manual Game" if not game else f"Configure {game['name']}")
        self.set_default_size(450, -1)
        
        self.exe_path = game.get('path', '') if game else ""
        self.artwork_data = {"type": "none", "value": None}
        
        # ... (rest of init)
        content = Adw.ToolbarView()
        self.set_content(content)
        
        header = Adw.HeaderBar()
        content.add_top_bar(header)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.set_content(box)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        box.append(clamp)
        
        page = Adw.PreferencesPage()
        clamp.set_child(page)
        
        # Group 1: General Info
        group_general = Adw.PreferencesGroup(title="Basic Information")
        page.add(group_general)
        
        # Game Name
        self.name_row = Adw.EntryRow(title="Game Name")
        if game:
            self.name_row.set_text(game['name'])
        group_general.add(self.name_row)
        
        # Executable
        self.path_row = Adw.ActionRow(title="Executable Path")
        self.path_label = Gtk.Label(label=os.path.basename(self.exe_path) if self.exe_path else "No file selected", ellipsize=3)
        self.path_row.add_suffix(self.path_label)
        
        browse_btn = Gtk.Button(label="Browse...")
        browse_btn.connect("clicked", self.on_browse_exe)
        self.path_row.add_suffix(browse_btn)
        group_general.add(self.path_row)
        
        # Group 2: Configuration
        group_config = Adw.PreferencesGroup(title="Runner Settings")
        page.add(group_config)
        
        # Proton Versions dropdown
        self.runner_row = Adw.ComboRow(title="Runner")
        self.proton_versions = self.runner.get_all_versions()
        self.version_names = sorted(self.proton_versions.keys(), reverse=True)
        
        # Options: 0=Default, 1=Native, 2+=Specific Proton
        display_names = ["Global Default (from Settings)", "Native (Linux/No Proton)"] + self.version_names
        self.runner_model = Gtk.StringList.new(display_names)
        self.runner_row.set_model(self.runner_model)
        
        if game:
            runner_type = game.get('runner_type', 'proton')
            if runner_type == 'native':
                self.runner_row.set_selected(1)
            elif runner_type == 'proton' and game.get('proton_version'):
                version = game.get('proton_version')
                if version in self.version_names:
                    self.runner_row.set_selected(self.version_names.index(version) + 2)
                else:
                    self.runner_row.set_selected(0)
            else:
                self.runner_row.set_selected(0)
        
        group_config.add(self.runner_row)

        # OnlineFix Support
        self.onlinefix_row = Adw.SwitchRow(title="OnlineFix Support")
        self.onlinefix_row.set_subtitle("Enable DLL overrides for online fixes (Steamworks Fix, etc.)")
        onlinefix_enabled = game.get('onlinefix_enabled', False) if game else False
        self.onlinefix_row.set_active(onlinefix_enabled)
        group_config.add(self.onlinefix_row)

        # Launch Arguments Group
        group_args = Adw.PreferencesGroup(title="Launch Arguments")
        page.add(group_args)
        
        # Use Global Arguments Toggle
        self.global_args_row = Adw.SwitchRow(title="Use Global Settings")
        self.global_args_row.set_subtitle("Apply arguments from global application settings")
        use_global = game.get('use_global_args', True) if game else True
        self.global_args_row.set_active(use_global)
        self.global_args_row.connect("notify::active", self.on_global_args_toggled)
        group_args.add(self.global_args_row)
        
        # Custom Launch Arguments
        self.args_row = Adw.EntryRow(title="Custom Arguments")
        if game and game.get('arguments'):
            self.args_row.set_text(game['arguments'])
        self.args_row.set_visible(not use_global)
        group_args.add(self.args_row)
        
        # Group 3: Artwork
        group_art = Adw.PreferencesGroup(title="Artwork")
        page.add(group_art)
        
        self.art_stack = Gtk.Stack()
        self.art_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        stack_switcher = Gtk.StackSwitcher(stack=self.art_stack)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        group_art.add(stack_switcher)
        group_art.add(self.art_stack)
        
        # Art: None
        none_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        none_box.set_margin_top(6)
        none_label = Gtk.Label(label="Default artwork will be used")
        none_label.set_css_classes(["dim-label"])
        none_box.append(none_label)
        self.art_stack.add_titled(none_box, "none", "None")
        
        # Art: Local File
        file_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        file_box.set_margin_top(6)
        self.art_file_label = Gtk.Label(label="No image selected", ellipsize=3)
        file_box.append(self.art_file_label)
        art_file_btn = Gtk.Button(label="Select Image...")
        art_file_btn.connect("clicked", self.on_browse_art)
        file_box.append(art_file_btn)
        self.art_stack.add_titled(file_box, "file", "Local File")
        
        # Art: Steam ID
        steam_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        steam_box.set_margin_top(6)
        self.steam_id_entry = Gtk.Entry(placeholder_text="Enter Steam AppID (e.g. 10)")
        steam_box.append(self.steam_id_entry)
        self.art_stack.add_titled(steam_box, "steam", "Steam ID")
        
        # Footer
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        footer_box.set_margin_top(24)
        footer_box.set_margin_bottom(24)
        footer_box.set_halign(Gtk.Align.CENTER)
        box.append(footer_box)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        footer_box.append(cancel_btn)
        
        self.save_btn = Gtk.Button(label="Add Game" if not game else "Save Changes")
        self.save_btn.set_css_classes(["suggested-action"])
        self.save_btn.connect("clicked", self.on_save_clicked)
        footer_box.append(self.save_btn)

    def on_global_args_toggled(self, row, param):
        self.args_row.set_visible(not row.get_active())

    def on_browse_exe(self, btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Executable")
        
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Windows Executables")
        file_filter.add_pattern("*.exe")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)
        dialog.set_filters(filters)
        
        dialog.open(self, None, self.on_exe_selected)

    def on_exe_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.exe_path = file.get_path()
                self.path_label.set_text(os.path.basename(self.exe_path))
                if not self.name_row.get_text():
                    name = os.path.basename(self.exe_path).replace(".exe", "")
                    self.name_row.set_text(name)
        except:
            pass

    def on_browse_art(self, btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Artwork")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        img_filter = Gtk.FileFilter()
        img_filter.set_name("Images")
        img_filter.add_mime_type("image/*")
        filters.append(img_filter)
        dialog.set_filters(filters)
        
        dialog.open(self, None, self.on_art_selected)

    def on_art_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.artwork_data = {"type": "file", "value": path}
                self.art_file_label.set_text(os.path.basename(path))
        except:
            pass

    def on_save_clicked(self, btn):
        name = self.name_row.get_text().strip()
        if not name or not self.exe_path:
            return
            
        selected_idx = self.runner_row.get_selected()
        runner = "proton"
        version = None
        
        if selected_idx == 0: # Default
            runner = "proton"
            version = None
        elif selected_idx == 1: # Native
            runner = "native"
            version = None
        else: # Specific Proton
            runner = "proton"
            version = self.version_names[selected_idx - 2]
        
        use_global_args = self.global_args_row.get_active()
        arguments = self.args_row.get_text().strip()
        
        art_method = self.art_stack.get_visible_child_name()
        if art_method == "steam":
            steam_id = self.steam_id_entry.get_text().strip()
            if steam_id:
                self.artwork_data = {"type": "steam", "value": steam_id}
            else:
                self.artwork_data = {"type": "none", "value": None}
        elif art_method == "none":
            self.artwork_data = {"type": "none", "value": None}
            
        onlinefix_enabled = self.onlinefix_row.get_active()
            
        self.emit("save-game", name, self.exe_path, runner, version, use_global_args, arguments, self.artwork_data, onlinefix_enabled)
        self.close()
