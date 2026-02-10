    def _update_playtime_label(self, seconds):
        """Format and update playtime label"""
        if seconds == 0:
            self.playtime_label.set_text("")
            return
            
        hours = seconds / 3600
        if hours >= 1:
            self.playtime_label.set_text(f"{hours:.1f} hours played")
        else:
            minutes = seconds / 60
            self.playtime_label.set_text(f"{int(minutes)} minutes played")
