import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject

class ArtworkDialog(Adw.Window):
    __gsignals__ = {
        'artwork-selected': (GObject.SignalFlags.RUN_FIRST, None, (str, str)), # type (file/steam), value
    }

    def __init__(self, parent_window):
        super().__init__(transient_for=parent_window, modal=True)
        self.set_title("Change Artwork")
        self.set_default_size(400, 300)
        
        # Main Content
        content = Adw.ToolbarView()
        self.set_content(content)
        
        # Header
        header = Adw.HeaderBar(show_end_title_buttons=True)
        content.add_top_bar(header)
        
        # Body
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_spacing(24)
        content.set_content(box)
        
        # View Switcher (File / Steam)
        stack = Gtk.Stack()
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        box.append(stack_switcher)
        box.append(stack)
        
        # Page 1: File
        file_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        file_page.set_spacing(12)
        
        file_desc = Gtk.Label(label="Select an image file from your computer")
        file_page.append(file_desc)
        
        file_btn = Gtk.Button(label="Choose File...")
        file_btn.connect("clicked", self.on_file_clicked)
        file_page.append(file_btn)
        
        stack.add_titled(file_page, "file", "Local File")
        
        # Page 2: Steam
        steam_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        steam_page.set_spacing(12)
        
        steam_desc = Gtk.Label(label="Enter Steam AppID")
        steam_page.append(steam_desc)
        
        self.steam_entry = Gtk.Entry()
        self.steam_entry.set_placeholder_text("e.g. 105600")
        steam_page.append(self.steam_entry)
        
        steam_btn = Gtk.Button(label="Download from Steam")
        steam_btn.set_css_classes(["suggested-action"])
        steam_btn.connect("clicked", self.on_steam_clicked)
        steam_page.append(steam_btn)
        
        stack.add_titled(steam_page, "steam", "Steam ID")

    def on_file_clicked(self, btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Artwork")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filter_img = Gtk.FileFilter()
        filter_img.set_name("Images")
        filter_img.add_mime_type("image/*")
        filters.append(filter_img)
        dialog.set_filters(filters)
        
        dialog.open(self, None, self.on_file_selected)

    def on_file_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.emit("artwork-selected", "file", file.get_path())
                self.close()
        except:
            pass

    def on_steam_clicked(self, btn):
        text = self.steam_entry.get_text()
        if text.isdigit():
            self.emit("artwork-selected", "steam", text)
            self.close()
