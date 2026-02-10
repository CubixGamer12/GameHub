import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, GLib
import threading
import os

class SettingsPage(Adw.PreferencesPage):
    def __init__(self, proton_manager, settings_manager):
        super().__init__()
        self.proton_manager = proton_manager
        self.settings_manager = settings_manager
        
        self.set_title("Settings")
        self.set_icon_name("preferences-system-symbolic")

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

        # Row 2: Download Latest
        self.download_row = Adw.ActionRow()
        self.download_row.set_title("Download Latest GE-Proton")
        self.download_row.set_subtitle("Check GitHub for updates")
        group.add(self.download_row)

        self.download_btn = Gtk.Button(label="Check")
        self.download_btn.set_valign(Gtk.Align.CENTER)
        self.download_btn.connect("clicked", self.on_action_clicked)
        self.download_row.add_suffix(self.download_btn)

        # Progress Bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_hexpand(True)
        
        self.progress_box = Gtk.Box()
        self.progress_box.set_visible(False)
        self.progress_box.set_margin_top(12)
        self.progress_box.set_margin_bottom(12)
        self.progress_box.set_margin_start(50)
        self.progress_box.set_margin_end(50)
        self.progress_box.append(self.progress_bar)
        
        group.add(self.progress_box)

        self.check_state = "check" # check, download, done
        self.pending_release = None

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

    def on_action_clicked(self, btn):
        if self.check_state == "check":
            self.download_btn.set_sensitive(False)
            self.download_row.set_subtitle("CheckingGitHub API...")
            threading.Thread(target=self._check_update_thread).start()
        elif self.check_state == "download":
            if self.pending_release:
                tag, url = self.pending_release
                self.start_download(tag, url)

    def _check_update_thread(self):
        tag, url = self.proton_manager.check_latest_release()
        GLib.idle_add(self._on_check_complete, tag, url)

    def _on_check_complete(self, tag, url):
        self.download_btn.set_sensitive(True)
        if tag and url:
            versions = self.proton_manager.get_installed_versions()
            if tag in versions:
                self.download_btn.set_label("Re-install")
                self.download_row.set_subtitle(f"Latest version {tag} is already installed")
                self.download_btn.set_sensitive(True)
                self.pending_release = (tag, url)
                self.check_state = "download"
            else:
                self.download_btn.set_label("Download")
                self.download_row.set_subtitle(f"New version availble: {tag}")
                self.pending_release = (tag, url)
                self.check_state = "download"
        else:
            self.download_btn.set_label("Retry")
            self.download_row.set_subtitle("Error checking for updates.")
            self.check_state = "check"

    def start_download(self, tag, url):
        self.download_btn.set_sensitive(False)
        self.progress_box.set_visible(True)
        
        self.proton_manager.download_and_install(
            url, tag, 
            progress_callback=self.update_progress,
            completion_callback=self.on_download_complete
        )

    def update_progress(self, fraction):
        GLib.idle_add(self.progress_bar.set_fraction, fraction)

    def on_download_complete(self, success, message):
        GLib.idle_add(self._download_finished_ui, success, message)

    def _download_finished_ui(self, success, message):
        self.progress_box.set_visible(False)
        self.download_btn.set_sensitive(True)
        if success:
            self.download_btn.set_label("Installed")
            self.download_row.set_subtitle(message)
            self.check_state = "done"
            self._refresh_versions()
        else:
            self.download_btn.set_label("Retry Download")
            self.download_row.set_subtitle(f"Failed: {message}")
            # Keep state as download to allow retry
