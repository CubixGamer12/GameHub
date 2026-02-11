import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, GLib
import threading
import os
from ui.dialogs.proton_download_dialog import ProtonDownloadDialog

class SettingsPage(Adw.PreferencesPage):
    def __init__(self, proton_manager, settings_manager):
        super().__init__()
        self.proton_manager = proton_manager
        self.settings_manager = settings_manager
        
        self.set_title("Settings")
        self.set_icon_name("preferences-system-symbolic")

        # Group: General Settings
        group_general = Adw.PreferencesGroup()
        group_general.set_title("General")
        self.add(group_general)

        # Row: Enable Steam Web API
        self.enable_api_row = Adw.SwitchRow()
        self.enable_api_row.set_title("Enable Steam Web API")
        self.enable_api_row.set_subtitle("Show uninstalled games from your Steam library")
        self.enable_api_row.set_active(self.settings_manager.get("enable_steam_api", "False").lower() == "true")
        self.enable_api_row.connect("notify::active", self.on_enable_api_changed)
        group_general.add(self.enable_api_row)

        # Row: Hide Borked Games
        self.hide_borked_row = Adw.SwitchRow()
        self.hide_borked_row.set_title("Hide Borked Games")
        self.hide_borked_row.set_subtitle("Don't show games marked as 'Borked' on ProtonDB")
        self.hide_borked_row.set_active(self.settings_manager.get("hide_borked", "False").lower() == "true")
        self.hide_borked_row.connect("notify::active", self.on_hide_borked_changed)
        group_general.add(self.hide_borked_row)

        # Row: Global Launch Arguments
        self.args_row = Adw.EntryRow()
        self.args_row.set_title("Global Launch Arguments")
        self.args_row.set_text(self.settings_manager.get("global_arguments", ""))
        self.args_row.connect("notify::text", self.on_args_changed)
        group_general.add(self.args_row)

        # Row: Steam Web API Key
        self.api_key_row = Adw.EntryRow()
        self.api_key_row.set_title("Steam Web API Key")
        self.api_key_row.set_text(self.settings_manager.get("steam_api_key", ""))
        self.api_key_row.connect("notify::text", self.on_api_key_changed)
        group_general.add(self.api_key_row)
        
        # Link to get key
        link_row = Adw.ActionRow()
        link_row.set_title("Get API Key")
        link_btn = Gtk.LinkButton.new_with_label("https://steamcommunity.com/dev/apikey", "Open Steam Dev Page")
        link_btn.set_valign(Gtk.Align.CENTER)
        link_row.add_suffix(link_btn)
        group_general.add(link_row)
        
        # Group: SteamGridDB
        group_sgdb = Adw.PreferencesGroup()
        group_sgdb.set_title("SteamGridDB")
        group_sgdb.set_description("Get high-quality game covers from SteamGridDB.")
        self.add(group_sgdb)
        
        # Row: SteamGridDB API Key
        self.sgdb_key_row = Adw.EntryRow()
        self.sgdb_key_row.set_title("SteamGridDB API Key")
        self.sgdb_key_row.set_text(self.settings_manager.get("sgdb_api_key", ""))
        self.sgdb_key_row.connect("notify::text", self.on_sgdb_key_changed)
        group_sgdb.add(self.sgdb_key_row)
        
        # Link to get key
        sgdb_link_row = Adw.ActionRow()
        sgdb_link_row.set_title("Get API Key")
        sgdb_link_btn = Gtk.LinkButton.new_with_label("https://www.steamgriddb.com/profile/preferences", "Open SteamGridDB Profile")
        sgdb_link_btn.set_valign(Gtk.Align.CENTER)
        sgdb_link_row.add_suffix(sgdb_link_btn)
        group_sgdb.add(sgdb_link_row)

        # Group: Proton Management
        group = Adw.PreferencesGroup()
        group.set_title("Proton Management")
        group.set_description("Manage GE-Proton versions for running Windows games.")
        self.add(group)

        # Row 1: Active Proton Version
        self.version_row = Adw.ComboRow()
        self.version_row.set_title("Active Proton Version")
        self.version_row.set_subtitle("Select which Proton version to use")
        # Connection moved to _refresh_versions to avoid overwriting config during init
        group.add(self.version_row)

        # Row 2: Manage Versions
        self.manage_row = Adw.ActionRow()
        self.manage_row.set_title("Download/Manage GE-Proton")
        self.manage_row.set_subtitle("Install specific versions from GitHub")
        group.add(self.manage_row)

        self.manage_btn = Gtk.Button(label="Open Manager")
        self.manage_btn.set_valign(Gtk.Align.CENTER)
        self.manage_btn.connect("clicked", self.on_manage_clicked)
        self.manage_row.add_suffix(self.manage_btn)

        self._refresh_versions()

    def _refresh_versions(self):
        versions = self.proton_manager.get_installed_versions()
        versions.sort(reverse=True)
        
        # Add system default option
        display_versions = ["System Default"] + versions
        
        model = Gtk.StringList.new(display_versions)
        self.version_row.set_model(model)
        
        # Select current
        current_path = self.settings_manager.get("custom_proton_path")
        if current_path and os.path.basename(current_path) in versions:
            folder_name = os.path.basename(current_path)
            self.version_row.set_selected(versions.index(folder_name) + 1)
        else:
            self.version_row.set_selected(0)
            
        # Reconnect to avoid double signals during refresh
        try: self.version_row.disconnect_by_func(self.on_version_changed)
        except: pass
        self.version_row.connect("notify::selected", self.on_version_changed)

    def on_version_changed(self, row, param):
        selected_idx = row.get_selected()
        if selected_idx == Gtk.INVALID_LIST_POSITION:
            return
            
        if selected_idx == 0:
            self.settings_manager.set("custom_proton_path", None)
        else:
            # item 0 is default
            versions = self.proton_manager.get_installed_versions()
            versions.sort(reverse=True)
            if selected_idx - 1 < len(versions):
                folder_name = versions[selected_idx - 1]
                path = os.path.join(self.proton_manager.INSTALL_DIR, folder_name)
                self.settings_manager.set("custom_proton_path", path)

    def on_args_changed(self, entry, param):
        self.settings_manager.set("global_arguments", entry.get_text())

    def on_args_changed(self, entry, param):
        self.settings_manager.set("global_arguments", entry.get_text())

    def on_api_key_changed(self, entry, param):
        self.settings_manager.set("steam_api_key", entry.get_text())

    def on_sgdb_key_changed(self, entry, param):
        self.settings_manager.set("sgdb_api_key", entry.get_text())

    def on_enable_api_changed(self, row, param):
        self.settings_manager.set("enable_steam_api", str(row.get_active()))

    def on_hide_borked_changed(self, row, param):
        self.settings_manager.set("hide_borked", str(row.get_active()))

    def on_manage_clicked(self, btn):
        dialog = ProtonDownloadDialog(self.get_root(), self.proton_manager, on_installed_callback=self._refresh_versions)
        dialog.present()
