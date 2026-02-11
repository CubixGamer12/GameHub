import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Pango, Adw

def on_activate(app):
    win = Gtk.ApplicationWindow(application=app)
    win.set_default_size(400, 400)
    
    flowbox = Gtk.FlowBox()
    flowbox.set_homogeneous(True)
    flowbox.set_halign(Gtk.Align.START)
    flowbox.set_valign(Gtk.Align.START)
    
    # Test items
    names = ["Short", "ARK: Survival Evolved", "Another Short One"]
    
    for name in names:
        child = Gtk.FlowBoxChild()
        child.set_size_request(180, 270)
        
        overlay = Gtk.Overlay()
        overlay.set_size_request(180, 270)
        child.set_child(overlay)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_valign(Gtk.Align.END)
        box.set_size_request(180, -1)
        overlay.add_overlay(box)
        
        label = Gtk.Label(label=name)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(12)
        label.set_hexpand(False)
        box.append(label)
        
        flowbox.append(child)
        
    win.set_child(flowbox)
    win.present()

app = Adw.Application(application_id="com.test.label")
app.connect('activate', on_activate)
# app.run(None) # Can't run GUI tests easily here, but I can check the code logic
