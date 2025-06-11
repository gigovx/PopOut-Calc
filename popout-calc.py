import tkinter as tk
import pyautogui
import winreg
import json
import os

def is_light_theme():
    """
    Checks the Windows registry to see if AppsUseLightTheme is active.
    Returns True if the system uses the light theme.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return bool(value)
    except Exception:
        return True  # default to light theme if an error occurs

class CalculatorApp:
    def __init__(self, root):
        self.root = root
        # Remove window borders and keep the window always on top.
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Set theme colors.
        if is_light_theme():
            self.bg_color = "#ffffff"    # window background
            self.btn_color = "#f0f0f0"     # button background
            self.fg_color = "#000000"      # text color
            self.handle_color = "#d0d0d0"  # slightly darker for the drag handle
        else:
            self.bg_color = "#333333"
            self.btn_color = "#555555"
            self.fg_color = "#ffffff"
            self.handle_color = "#444444"

        self.root.configure(bg=self.bg_color)

        # Set a path to the configuration file.
        self.config_file = "calc_config.json"
        # Load persistent settings if available.
        self.load_config()

        # Default settings if nothing was loaded.
        if not hasattr(self, "button_size"):
            self.button_size = 48   # Options: 48, 64, 128, or 256 pixels.
        if not hasattr(self, "side"):
            self.side = "right"     # Options: "right", "left", "top", "bottom"
        if not hasattr(self, "current_font"):
            self.current_font = "Arial"   # Default font

        # Create Tkinter variables for radiobutton menus.
        self.size_var = tk.IntVar(value=self.button_size)
        self.font_var = tk.StringVar(value=self.current_font)
        self.side_var = tk.StringVar(value=self.side)

        self.hidden_size = 20  # The sliver that remains visible when hidden.

        # Get screen dimensions.
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Calculator button texts; grid is 5 rows x 4 columns.
        self.btn_texts = [
            ["C", "(", ")", "CE"],
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "=", "+"]
        ]

        # Calculate window geometry based on current settings.
        self.set_geometry_parameters()

        # Build the UI: handle, copy/paste row, output display, then button grid.
        self.build_ui()

        # Bind right-click to show the settings menu.
        self.root.bind("<Button-3>", self.show_settings_menu)

        # Start checking for mouse hover for auto-slide.
        self.is_expanded = False
        self.check_hover()

    def load_config(self):
        """Load settings from the configuration file, if it exists."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                self.button_size = config.get("button_size", 48)
                self.side = config.get("side", "right")
                self.current_font = config.get("current_font", "Arial")
            except Exception:
                self.button_size = 48
                self.side = "right"
                self.current_font = "Arial"

    def save_config(self):
        """Save the current settings to a configuration file."""
        config = {
            "button_size": self.button_size,
            "side": self.side,
            "current_font": self.current_font
        }
        with open(self.config_file, "w") as f:
            json.dump(config, f)

    def set_geometry_parameters(self):
        """
        Calculate geometry parameters based on side and button size.
        New layout:
          - full_width is 4 * button_size.
          - full_height = handle_height + copy/paste row height + output display height + (5 rows * button_size)
        """
        self.handle_height = self.button_size // 4
        self.copy_height = self.button_size // 2  # Height for copy/paste row.
        self.display_height = self.button_size      # Output display height.
        self.buttons_rows = 5

        self.full_width = 4 * self.button_size
        self.full_height = (
            self.handle_height +
            self.copy_height +
            self.display_height +
            (self.buttons_rows * self.button_size)
        )

        if self.side in ["right", "left"]:
            self.y_pos = int((self.screen_height - self.full_height) / 2)
            if self.side == "right":
                self.x_visible = self.screen_width - self.full_width
                self.x_hidden = self.screen_width - self.hidden_size
            elif self.side == "left":
                self.x_visible = 0
                self.x_hidden = -self.full_width + self.hidden_size
            self.current_offset = self.x_hidden
        elif self.side in ["top", "bottom"]:
            self.x_pos = int((self.screen_width - self.full_width) / 2)
            if self.side == "top":
                self.y_visible = 0
                self.y_hidden = -self.full_height + self.hidden_size
            elif self.side == "bottom":
                self.y_visible = self.screen_height - self.full_height
                self.y_hidden = self.screen_height - self.hidden_size
            self.current_offset = self.y_hidden

    def update_geometry(self):
        """Update window geometry based on side and current offset."""
        if self.side in ["right", "left"]:
            self.root.geometry(f"{self.full_width}x{self.full_height}+{self.current_offset}+{self.y_pos}")
        elif self.side in ["top", "bottom"]:
            self.root.geometry(f"{self.full_width}x{self.full_height}+{self.x_pos}+{self.current_offset}")

    def build_ui(self):
        """Create UI elements for the calculator with Copy/Paste row above the output."""
        # Draggable Handle (top row).
        self.drag_handle = tk.Frame(
            self.root, bg=self.handle_color, height=self.handle_height, cursor="fleur"
        )
        self.drag_handle.place(x=0, y=0, width=self.full_width, height=self.handle_height)
        self.drag_handle.bind("<ButtonPress-1>", self.start_move)
        self.drag_handle.bind("<B1-Motion>", self.do_move)

        # Copy/Paste Row (immediately below handle).
        copy_font_size = self.button_size // 5 
        self.copy_button = tk.Button(
            self.root, text="Copy", bg=self.btn_color, fg=self.fg_color,
            font=(self.current_font, copy_font_size),
            bd=0, relief="flat", activebackground=self.bg_color,
            command=self.copy_to_clipboard
        )
        self.copy_button.place(x=0, y=self.handle_height,
                               width=self.full_width // 2, height=self.copy_height)

        self.paste_button = tk.Button(
            self.root, text="Paste", bg=self.btn_color, fg=self.fg_color,
            font=(self.current_font, copy_font_size),
            bd=0, relief="flat", activebackground=self.bg_color,
            command=self.paste_from_clipboard
        )
        self.paste_button.place(x=self.full_width // 2, y=self.handle_height,
                                width=self.full_width // 2, height=self.copy_height)

        # Output Display (below copy/paste row).
        output_y = self.handle_height + self.copy_height
        self.display = tk.Entry(
            self.root,
            font=(self.current_font, max(self.button_size // 2 - 2, 8)),
            bd=0, relief="flat",
            bg=self.bg_color, fg=self.fg_color, justify="right",
            state="readonly"
        )
        self.display.place(x=0, y=output_y, width=self.full_width, height=self.display_height)
        self.expression = ""

        # Calculator Button Grid (5 rows x 4 columns) placed below the output.
        grid_top = output_y + self.display_height
        self.buttons = []
        for i, row in enumerate(self.btn_texts):
            button_row = []
            for j, char in enumerate(row):
                btn = tk.Button(
                    self.root, text=char, bg=self.btn_color, fg=self.fg_color,
                    font=(self.current_font, self.button_size // 4),
                    bd=0, relief="flat", activebackground=self.bg_color,
                    command=lambda ch=char: self.on_button_click(ch)
                )
                x_pos = j * self.button_size
                y_pos = grid_top + i * self.button_size
                btn.place(x=x_pos, y=y_pos, width=self.button_size, height=self.button_size)
                button_row.append(btn)
            self.buttons.append(button_row)

        self.update_geometry()

    def rebuild_ui(self):
        """
        Recalculate geometry and reposition/update all UI elements
        (handle, copy/paste row, display, and button grid)
        after a settings change.
        """
        self.set_geometry_parameters()

        self.drag_handle.place(x=0, y=0, width=self.full_width, height=self.handle_height)

        copy_font_size = self.button_size // 5
        self.copy_button.place(x=0, y=self.handle_height,
                               width=self.full_width // 2, height=self.copy_height)
        self.copy_button.config(font=(self.current_font, copy_font_size))

        self.paste_button.place(x=self.full_width // 2, y=self.handle_height,
                                width=self.full_width // 2, height=self.copy_height)
        self.paste_button.config(font=(self.current_font, copy_font_size))

        output_y = self.handle_height + self.copy_height
        self.display.place(x=0, y=output_y, width=self.full_width, height=self.display_height)
        self.display.config(font=(self.current_font, max(self.button_size // 2 - 2, 8)))

        grid_top = output_y + self.display_height
        for i, row in enumerate(self.buttons):
            for j, btn in enumerate(row):
                x_pos = j * self.button_size
                y_pos = grid_top + i * self.button_size
                btn.place(x=x_pos, y=y_pos, width=self.button_size, height=self.button_size)
                btn.config(font=(self.current_font, self.button_size // 4))

        self.update_geometry()

    def copy_to_clipboard(self):
        """Copy the contents of the display to the clipboard."""
        text = self.display.get()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def paste_from_clipboard(self):
        """
        Attempt to get text from the clipboard.
        If it represents a numeric value (allowing for a decimal point),
        append it to the calculator's current expression.
        """
        try:
            clip = self.root.clipboard_get().strip()
            try:
                float(clip)
                self.expression += clip
                self.display.config(state="normal")
                self.display.delete(0, tk.END)
                self.display.insert(tk.END, self.expression)
                self.display.config(state="readonly")
            except ValueError:
                pass
        except tk.TclError:
            pass

    def start_move(self, event):
        """Store initial position for dragging the calculator along the edge."""
        if self.side in ["right", "left"]:
            self.drag_start_y = event.y_root
            self.initial_y = self.y_pos
        elif self.side in ["top", "bottom"]:
            self.drag_start_x = event.x_root
            self.initial_x = self.x_pos

    def do_move(self, event):
        """Drag to reposition the calculator along the respective axis."""
        if self.side in ["right", "left"]:
            delta = event.y_root - self.drag_start_y
            new_y = self.initial_y + delta
            if new_y < 0:
                new_y = 0
            elif new_y + self.full_height > self.screen_height:
                new_y = self.screen_height - self.full_height
            self.y_pos = new_y
        elif self.side in ["top", "bottom"]:
            delta = event.x_root - self.drag_start_x
            new_x = self.initial_x + delta
            if new_x < 0:
                new_x = 0
            elif new_x + self.full_width > self.screen_width:
                new_x = self.screen_width - self.full_width
            self.x_pos = new_x
        self.update_geometry()

    def on_button_click(self, char):
        """Handle calculator button clicks: clear, evaluate, or append."""
        if char in ['C', 'CE']:
            self.expression = ""
            self.display.config(state="normal")
            self.display.delete(0, tk.END)
            self.display.config(state="readonly")
        elif char == "=":
            try:
                result = eval(self.expression)
                self.expression = str(result)
            except Exception:
                self.expression = "Error"
            self.display.config(state="normal")
            self.display.delete(0, tk.END)
            self.display.insert(tk.END, self.expression)
            self.display.config(state="readonly")
        else:
            self.expression += str(char)
            self.display.config(state="normal")
            self.display.delete(0, tk.END)
            self.display.insert(tk.END, self.expression)
            self.display.config(state="readonly")

    def check_hover(self):
        """
        Monitor the mouse position using PyAutoGUI.
        Instead of using a fixed distance from the screen edge, this function
        checks if the mouse pointer is over the visible part of the calculator.
        """
        mouse_x, mouse_y = pyautogui.position()
        
        # For each side, we determine the visible rectangle when hidden.
        if self.side == "right":
            # When docked on the right, the hidden state window is at:
            # x = self.screen_width - self.hidden_size (visible bar)
            # and its y is self.y_pos with height self.full_height.
            if (mouse_x >= self.screen_width - self.hidden_size and 
                self.y_pos <= mouse_y <= self.y_pos + self.full_height):
                if not self.is_expanded:
                    self.slide_in()
                    self.is_expanded = True
            else:
                if self.is_expanded:
                    self.slide_out()
                    self.is_expanded = False

        elif self.side == "left":
            # When docked on the left, the visible part covers x: 0 to self.hidden_size.
            if (mouse_x <= self.hidden_size and 
                self.y_pos <= mouse_y <= self.y_pos + self.full_height):
                if not self.is_expanded:
                    self.slide_in()
                    self.is_expanded = True
            else:
                if self.is_expanded:
                    self.slide_out()
                    self.is_expanded = False

        elif self.side == "top":
            # When docked at the top, the visible part covers y: 0 to self.hidden_size.
            if (mouse_y <= self.hidden_size and 
                self.x_pos <= mouse_x <= self.x_pos + self.full_width):
                if not self.is_expanded:
                    self.slide_in()
                    self.is_expanded = True
            else:
                if self.is_expanded:
                    self.slide_out()
                    self.is_expanded = False

        elif self.side == "bottom":
            # When docked at the bottom, the visible part covers y: screen_height - self.hidden_size to screen_height.
            if (mouse_y >= self.screen_height - self.hidden_size and 
                self.x_pos <= mouse_x <= self.x_pos + self.full_width):
                if not self.is_expanded:
                    self.slide_in()
                    self.is_expanded = True
            else:
                if self.is_expanded:
                    self.slide_out()
                    self.is_expanded = False

        self.root.after(100, self.check_hover)

    def slide_in(self):
        """Slides the calculator into full view based on its current side."""
        step = 10
        if self.side == "right":
            if self.current_offset > self.x_visible:
                self.current_offset = max(self.current_offset - step, self.x_visible)
                self.update_geometry()
                self.root.after(10, self.slide_in)
        elif self.side == "left":
            if self.current_offset < self.x_visible:
                self.current_offset = min(self.current_offset + step, self.x_visible)
                self.update_geometry()
                self.root.after(10, self.slide_in)
        elif self.side == "top":
            if self.current_offset < self.y_visible:
                self.current_offset = min(self.current_offset + step, self.y_visible)
                self.update_geometry()
                self.root.after(10, self.slide_in)
        elif self.side == "bottom":
            if self.current_offset > self.y_visible:
                self.current_offset = max(self.current_offset - step, self.y_visible)
                self.update_geometry()
                self.root.after(10, self.slide_in)

    def slide_out(self):
        """Slides the calculator out so that only a small sliver remains visible."""
        step = 10
        if self.side == "right":
            if self.current_offset < self.x_hidden:
                self.current_offset = min(self.current_offset + step, self.x_hidden)
                self.update_geometry()
                self.root.after(10, self.slide_out)
        elif self.side == "left":
            if self.current_offset > self.x_hidden:
                self.current_offset = max(self.current_offset - step, self.x_hidden)
                self.update_geometry()
                self.root.after(10, self.slide_out)
        elif self.side == "top":
            if self.current_offset > self.y_hidden:
                self.current_offset = max(self.current_offset - step, self.y_hidden)
                self.update_geometry()
                self.root.after(10, self.slide_out)
        elif self.side == "bottom":
            if self.current_offset < self.y_hidden:
                self.current_offset = min(self.current_offset + step, self.y_hidden)
                self.update_geometry()
                self.root.after(10, self.slide_out)

    def show_settings_menu(self, event):
        """Displays a right-click settings menu with tick marks for the current settings."""
        menu = tk.Menu(self.root, tearoff=0)

        # Change Size submenu with radiobuttons.
        size_menu = tk.Menu(menu, tearoff=0)
        size_menu.add_radiobutton(label="48x48", variable=self.size_var, value=48,
                                  command=lambda: self.update_size(48))
        size_menu.add_radiobutton(label="64x64", variable=self.size_var, value=64,
                                  command=lambda: self.update_size(64))
        size_menu.add_radiobutton(label="128x128", variable=self.size_var, value=128,
                                  command=lambda: self.update_size(128))
        size_menu.add_radiobutton(label="256x256", variable=self.size_var, value=256,
                                  command=lambda: self.update_size(256))
        menu.add_cascade(label="Change Size", menu=size_menu)

        # Change Font submenu with radiobuttons.
        font_menu = tk.Menu(menu, tearoff=0)
        for font in ["Arial", "Tahoma", "Calibri", "Verdana", "Segoe UI"]:
            font_menu.add_radiobutton(label=font, variable=self.font_var, value=font,
                                      command=lambda f=font: self.update_font(f))
        menu.add_cascade(label="Change Font", menu=font_menu)

        # Change Side submenu with radiobuttons.
        side_menu = tk.Menu(menu, tearoff=0)
        side_menu.add_radiobutton(label="Left", variable=self.side_var, value="left",
                                  command=lambda: self.update_side("left"))
        side_menu.add_radiobutton(label="Right", variable=self.side_var, value="right",
                                  command=lambda: self.update_side("right"))
        side_menu.add_radiobutton(label="Top", variable=self.side_var, value="top",
                                  command=lambda: self.update_side("top"))
        side_menu.add_radiobutton(label="Bottom", variable=self.side_var, value="bottom",
                                  command=lambda: self.update_side("bottom"))
        menu.add_cascade(label="Change Side", menu=side_menu)

        # Exit option.
        menu.add_command(label="Exit", command=self.root.destroy)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def update_size(self, new_size):
        """Update button size, rebuild the UI, update variable, and save settings."""
        self.button_size = new_size
        self.size_var.set(new_size)
        self.rebuild_ui()
        self.save_config()

    def update_side(self, new_side):
        """Update the side, rebuild the UI, update variable, and save settings."""
        self.side = new_side
        self.side_var.set(new_side)
        self.rebuild_ui()
        self.save_config()

    def update_font(self, new_font):
        """Update the font, rebuild the UI so the font scales, update variable, and save settings."""
        self.current_font = new_font
        self.font_var.set(new_font)
        self.rebuild_ui()
        self.save_config()

if __name__ == "__main__":
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()
