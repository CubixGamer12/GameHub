#!/usr/bin/env python3
import os
import sys
import subprocess
import threading
import shutil
from pathlib import Path

# Modern Installer for GameHub
# Uses Libadwaita for a professional graphical experience

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, Gio, GLib, Gdk
except ImportError:
    print("Modern Installer requires 'python-gobject', 'gtk4', and 'libadwaita'.")
    print("Please install these dependencies manually first.")
    sys.exit(1)

APP_NAME = "GameHub"
DESKTOP_FILENAME = "com.github.gamehub.desktop"
ICON_NAME = "applications-games-symbolic"

# Package Manager Mappings
DISTRO_DEPS = {
    "pacman": {
        "name": "Arch Linux (pacman)",
        "packages": ["python-gobject", "gtk4", "libadwaita", "python-pip", "python-psutil"],
        "cmd": ["sudo", "pacman", "-Syu", "--needed", "--noconfirm"]
    },
    "apt": {
        "name": "Ubuntu/Debian (apt)",
        "packages": ["python3-gi", "libgtk-4-dev", "libadwaita-1-dev", "python3-pip", "python3-psutil"],
        "cmd": ["sudo", "apt", "update", "&&", "sudo", "apt", "install", "-y"]
    },
    "dnf": {
        "name": "Fedora (dnf)",
        "packages": ["python3-gobject", "gtk4", "libadwaita", "python3-pip", "python3-psutil"],
        "cmd": ["sudo", "dnf", "install", "-y"]
    }
}

class GameHubInstaller(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id='com.github.gamehub.Installer',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.project_dir = Path(__file__).resolve().parent
        self.main_py = self.project_dir / "src" / "main.py"
        self.pkg_manager = self.detect_package_manager()

    def detect_package_manager(self):
        for pm in DISTRO_DEPS.keys():
            if shutil.which(pm):
                return pm
        return None

    def apply_custom_css(self):
        css = """
        window {
            background-color: @window_bg_color;
        }
        statuspage {
            margin: 24px;
        }
        .welcome-title {
            font-size: 2.2em;
            font-weight: 800;
            background-image: linear-gradient(135deg, @accent_color, @accent_bg_color);
            color: @accent_color;
        }
        .pill {
            padding: 12px 32px;
            font-weight: bold;
        }
        .install-banner {
            background-color: alpha(@accent_bg_color, 0.1);
            border-radius: 12px;
            padding: 16px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_activate(self):
        # 1. Apply Styles
        self.apply_custom_css()

        # 2. Initialize Window
        self.win = Adw.ApplicationWindow(application=self, title="GameHub Installer")
        self.win.set_default_size(500, 650)

        # 3. Create Stack and Clamp
        self.stack = Adw.ViewStack()
        clamp = Adw.Clamp(maximum_size=1000)
        clamp.set_child(self.stack)
        self.win.set_content(clamp)

        # --- Welcome Page ---
        welcome_page = Adw.StatusPage(
            title="Welcome to GameHub",
            description="A unified, modern game library for Linux.",
            icon_name="applications-games-symbolic"
        )
        start_btn = Gtk.Button(
            label="Begin Installation", 
            halign=Gtk.Align.CENTER, 
            css_classes=["suggested-action", "pill"]
        )
        start_btn.set_margin_top(24)
        start_btn.connect("clicked", lambda x: self.stack.set_visible_child_name("deps"))
        welcome_page.set_child(start_btn)
        self.stack.add_titled(welcome_page, "welcome", "Welcome")

        # --- Dependencies Page ---
        self.deps_page = Adw.StatusPage(
            title="System Dependencies",
            description="Required packages for GameHub to run correctly.",
            icon_name="system-software-install-symbolic"
        )
        pm_name = DISTRO_DEPS[self.pkg_manager]["name"] if self.pkg_manager else "Unknown Distro"
        self.install_deps_btn = Gtk.Button(
            label=f"Install Packages ({pm_name})", 
            halign=Gtk.Align.CENTER, 
            css_classes=["pill"]
        )
        self.install_deps_btn.set_sensitive(self.pkg_manager is not None)
        self.install_deps_btn.set_margin_top(24)
        self.install_deps_btn.connect("clicked", self.on_install_deps)
        self.deps_page.set_child(self.install_deps_btn)
        self.stack.add_titled(self.deps_page, "deps", "Dependencies")

        # --- Setup Page ---
        self.setup_page = Adw.StatusPage(
            title="Finalizing Setup",
            description="Configuring desktop shortcuts and permissions.",
            icon_name="emblem-system-symbolic"
        )
        self.finish_btn = Gtk.Button(
            label="Register Application", 
            halign=Gtk.Align.CENTER, 
            css_classes=["suggested-action", "pill"]
        )
        self.finish_btn.set_margin_top(24)
        self.finish_btn.connect("clicked", self.on_finish_setup)
        self.setup_page.set_child(self.finish_btn)
        self.stack.add_titled(self.setup_page, "setup", "Setup")

        # --- Success Page ---
        self.success_page = Adw.StatusPage(
            title="Installation Complete!",
            description="GameHub has been successfully installed.",
            icon_name="emblem-ok-symbolic"
        )
        launch_btn = Gtk.Button(
            label="Launch GameHub", 
            halign=Gtk.Align.CENTER, 
            css_classes=["suggested-action", "pill"]
        )
        launch_btn.set_margin_top(24)
        launch_btn.connect("clicked", self.on_launch)
        self.success_page.set_child(launch_btn)
        self.stack.add_titled(self.success_page, "success", "Success")

        self.win.present()

    def on_install_deps(self, btn):
        btn.set_sensitive(False)
        self.deps_page.set_description("Installing... check terminal for sudo authentication.")
        
        def run_install():
            try:
                if not self.pkg_manager:
                    GLib.idle_add(lambda: self.deps_page.set_description("Could not detect a supported package manager."))
                    return

                config = DISTRO_DEPS[self.pkg_manager]
                full_cmd = config["cmd"] + config["packages"]
                
                # Special handling for apt (requires shell for &&)
                if self.pkg_manager == "apt":
                    subprocess.run(" ".join(full_cmd), shell=True, check=True)
                else:
                    subprocess.run(full_cmd, check=True)

                GLib.idle_add(self.on_deps_success)
            except Exception as e:
                GLib.idle_add(lambda: self.deps_page.set_description(f"Installation failed: {e}"))
                GLib.idle_add(lambda: btn.set_sensitive(True))

        threading.Thread(target=run_install, daemon=True).start()

    def on_deps_success(self):
        self.deps_page.set_description("All dependencies are now installed.")
        self.install_deps_btn.set_label("Continue")
        self.install_deps_btn.set_sensitive(True)
        self.install_deps_btn.disconnect_by_func(self.on_install_deps)
        self.install_deps_btn.connect("clicked", lambda x: self.stack.set_visible_child_name("setup"))

    def on_finish_setup(self, btn):
        try:
            self.create_desktop_file()
            self.stack.set_visible_child_name("success")
        except Exception as e:
            self.setup_page.set_description(f"Error creating file: {e}")

    def create_desktop_file(self):
        desktop_dir = Path.home() / ".local/share/applications"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        desktop_path = desktop_dir / DESKTOP_FILENAME
        
        content = f"""[Desktop Entry]
Name={APP_NAME}
Comment=Unified game library for Linux
Exec=/usr/bin/env python3 "{self.main_py}"
Icon={ICON_NAME}
Terminal=false
Type=Application
Categories=Game;Utility;
StartupNotify=true
"""
        desktop_path.write_text(content)
        os.chmod(desktop_path, 0o755)

    def on_launch(self, btn):
        subprocess.Popen(["python3", str(self.main_py)])
        self.quit()

if __name__ == "__main__":
    app = GameHubInstaller()
    app.run(sys.argv)
