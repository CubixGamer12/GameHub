import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject, GLib
import threading

class ProtonDownloadDialog(Adw.Window):
    def __init__(self, parent_window, proton_manager, on_installed_callback=None):
        super().__init__(transient_for=parent_window, modal=True)
        self.set_title("Download Proton Versions")
        self.set_default_size(500, 650)
        
        self.proton_manager = proton_manager
        self.on_installed_callback = on_installed_callback
        self.installed_versions = self.proton_manager.get_installed_versions()
        
        self.content = Adw.ToolbarView()
        self.set_content(self.content)
        
        header = Adw.HeaderBar()
        self.content.add_top_bar(header)
        
        # View Switcher in Title
        self.view_stack = Adw.ViewStack()
        header.set_title_widget(Adw.ViewSwitcher(stack=self.view_stack))
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content.set_content(self.main_box)
        
        # GE Page
        self.ge_list = self._create_source_page("ge", "GE-Proton")
        # CachyOS Page
        self.cachy_list = self._create_source_page("cachyos", "Proton-CachyOS")
        
        self.main_box.append(self.view_stack)
        
        # Bottom bar for progress
        self.footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.footer.set_margin_start(12)
        self.footer.set_margin_end(12)
        self.footer.set_margin_top(12)
        self.footer.set_margin_bottom(12)
        self.footer.set_visible(False)
        self.main_box.append(self.footer)
        
        self.progress_label = Gtk.Label(label="Downloading...")
        self.footer.append(self.progress_label)
        
        self.progress_bar = Gtk.ProgressBar()
        self.footer.append(self.progress_bar)
        
        # Initial Loads
        threading.Thread(target=self._load_source, args=("ge", self.ge_list), daemon=True).start()
        threading.Thread(target=self._load_source, args=("cachyos", self.cachy_list), daemon=True).start()

    def _create_source_page(self, name, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        status_page = Adw.StatusPage()
        status_page.set_title(f"Checking {title} releases...")
        status_page.set_icon_name("system-software-update-symbolic")
        box.append(status_page)
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.set_css_classes(["boxed-list"])
        list_box.set_margin_start(12)
        list_box.set_margin_end(12)
        list_box.set_margin_top(12)
        list_box.set_margin_bottom(12)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(list_box)
        scrolled.set_vexpand(True)
        scrolled.set_visible(False)
        box.append(scrolled)
        
        page = self.view_stack.add_titled(box, name, title)
        page.set_icon_name("package-x-generic-symbolic")
        
        return {"list": list_box, "status": status_page, "scrolled": scrolled}

    def _load_source(self, source_name, ui_dict):
        releases = self.proton_manager.get_available_releases(source_name)
        GLib.idle_add(self._on_releases_loaded, releases, ui_dict)

    def _on_releases_loaded(self, releases, ui_dict):
        if not releases:
            ui_dict["status"].set_title("Error")
            ui_dict["status"].set_description("Could not fetch releases from GitHub.")
            return

        ui_dict["status"].set_visible(False)
        ui_dict["scrolled"].set_visible(True)

        # Clear existing
        while (child := ui_dict["list"].get_first_child()):
            ui_dict["list"].remove(child)

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
                
            ui_dict["list"].append(row)

    def on_install_clicked(self, tag, url):
        self.view_stack.set_sensitive(False)
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
        self.view_stack.set_sensitive(True)
        self.footer.set_visible(False)
        
        if success:
            self.installed_versions = self.proton_manager.get_installed_versions()
            if self.on_installed_callback:
                self.on_installed_callback()
            
            # Refresh both lists to update "Installed" labels
            self._load_source("ge", self.ge_list)
            self._load_source("cachyos", self.cachy_list)
        else:
            # Simple error dialog
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Installation Failed",
                body=str(message)
            )
            dialog.add_response("ok", "OK")
            dialog.present()
