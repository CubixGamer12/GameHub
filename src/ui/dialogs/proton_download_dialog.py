import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject, GLib
import threading

class ProtonDownloadDialog(Adw.Window):
    def __init__(self, parent_window, proton_manager, on_installed_callback=None):
        super().__init__(transient_for=parent_window, modal=True)
        self.set_title("Download GE-Proton Versions")
        self.set_default_size(500, 600)
        
        self.proton_manager = proton_manager
        self.on_installed_callback = on_installed_callback
        self.installed_versions = self.proton_manager.get_installed_versions()
        
        self.content = Adw.ToolbarView()
        self.set_content(self.content)
        
        header = Adw.HeaderBar()
        self.content.add_top_bar(header)
        
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.set_content(self.box)
        
        self.status_page = Adw.StatusPage()
        self.status_page.set_title("Checking for releases...")
        self.status_page.set_icon_name("system-software-update-symbolic")
        self.box.append(self.status_page)
        
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.set_css_classes(["boxed-list"])
        self.list_box.set_margin_start(12)
        self.list_box.set_margin_end(12)
        self.list_box.set_margin_top(12)
        self.list_box.set_margin_bottom(12)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_child(self.list_box)
        self.scrolled.set_vexpand(True)
        self.scrolled.set_visible(False)
        self.box.append(self.scrolled)
        
        # Bottom bar for progress
        self.footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.footer.set_margin_top(12)
        self.footer.set_margin_bottom(12)
        self.footer.set_margin_start(12)
        self.footer.set_margin_end(12)
        self.footer.set_visible(False)
        self.box.append(self.footer)
        
        self.progress_label = Gtk.Label(label="Downloading...")
        self.footer.append(self.progress_label)
        
        self.progress_bar = Gtk.ProgressBar()
        self.footer.append(self.progress_bar)
        
        threading.Thread(target=self._load_releases, daemon=True).start()

    def _load_releases(self):
        releases = self.proton_manager.get_available_releases()
        GLib.idle_add(self._on_releases_loaded, releases)

    def _on_releases_loaded(self, releases):
        if not releases:
            self.status_page.set_title("Error")
            self.status_page.set_description("Could not fetch releases from GitHub.")
            return

        self.status_page.set_visible(False)
        self.scrolled.set_visible(True)

        for tag, url in releases:
            row = Adw.ActionRow()
            row.set_title(tag)
            
            if tag in self.installed_versions:
                label = Gtk.Label(label="Installed")
                label.set_css_classes(["dim-label"])
                row.add_suffix(label)
                
                reinstall_btn = Gtk.Button(label="Re-install")
                reinstall_btn.set_valign(Gtk.Align.CENTER)
                reinstall_btn.connect("clicked", lambda b, t=tag, u=url: self.on_install_clicked(t, u))
                row.add_suffix(reinstall_btn)
            else:
                install_btn = Gtk.Button(label="Install")
                install_btn.set_valign(Gtk.Align.CENTER)
                install_btn.set_css_classes(["suggested-action"])
                install_btn.connect("clicked", lambda b, t=tag, u=url: self.on_install_clicked(t, u))
                row.add_suffix(install_btn)
                
            self.list_box.append(row)

    def on_install_clicked(self, tag, url):
        self.scrolled.set_sensitive(False)
        self.footer.set_visible(True)
        self.progress_label.set_text(f"Installing {tag}...")
        self.progress_bar.set_fraction(0.0)
        
        self.proton_manager.download_and_install(
            url, tag,
            progress_callback=self._update_progress,
            completion_callback=self._on_install_finished
        )

    def _update_progress(self, fraction):
        GLib.idle_add(self.progress_bar.set_fraction, fraction)

    def _on_install_finished(self, success, message):
        GLib.idle_add(self._on_install_finished_ui, success, message)

    def _on_install_finished_ui(self, success, message):
        self.scrolled.set_sensitive(True)
        self.footer.set_visible(False)
        
        if success:
            self.installed_versions = self.proton_manager.get_installed_versions()
            # Clear and reload list (could be optimized but okay for now)
            while (child := self.list_box.get_first_child()):
                self.list_box.remove(child)
            # Re-fetch releases would be too much, let's just use the cached ones if we had them
            # Actually easiest to just close or refresh.
            if self.on_installed_callback:
                self.on_installed_callback()
            self._load_releases()
        else:
            # Show error toast or dialog? 
            # For now just simple alert
            print(f"Error: {message}")
