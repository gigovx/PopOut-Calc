import tkinter as tk
import pyautogui
import winreg
import json
import os

def is_light_theme():
    """
    Checks the Windows registry to see if AppsUseLightTheme is active.
    Returns True if the system uses the light theme.
    (Used only if no configuration is set yet.)
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
        return True

class CalculatorApp:
    def __init__(self, root):
        self.root = root
        # Remove window borders and keep always on top.
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Load persistent configuration.
        self.config_file = "calc_config.json"
        self.load_config()  # Loads button_size, side, current_font, theme, x_pos, y_pos.
        
        if not hasattr(self, "button_size"):
            self.button_size = 48
        if not hasattr(self, "side"):
            self.side = "right"
        if not hasattr(self, "current_font"):
            self.current_font = "Arial"
        if not hasattr(self, "theme"):
            self.theme = "light" if is_light_theme() else "dark"
        # x_pos and y_pos may be None.
        
        # Tkinter variables for the context menu.
        self.size_var = tk.IntVar(value=self.button_size)
        self.font_var = tk.StringVar(value=self.current_font)
        self.side_var = tk.StringVar(value=self.side)
        self.theme_var = tk.StringVar(value=self.theme)
        
        self.update_colors()
        
        # Dimension (in pixels) of the permanent bar that remains visible when hidden.
        self.hidden_size = 20
        
        # Screen dimensions.
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Calculator button texts.
        self.btn_texts = [
            ["C", "(", ")", "CE"],
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "=", "+"]
        ]
        
        self.is_expanded = False
        self.set_geometry_parameters()
        self.build_ui()
        self.root.bind("<Button-3>", self.show_settings_menu)
        self.check_hover()
    
    def update_colors(self):
        """Update our color palette according to the current theme."""
        if self.theme == "light":
            self.bg_color = "#ffffff"
            self.btn_color = "#f0f0f0"
            self.fg_color = "#000000"
            self.handle_color = "#d0d0d0"
        else:
            self.bg_color = "#333333"
            self.btn_color = "#555555"
            self.fg_color = "#ffffff"
            self.handle_color = "#444444"
        self.root.configure(bg=self.bg_color)
    
    def load_config(self):
        """Load settings from the JSON config file if it exists."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                self.button_size = config.get("button_size", 48)
                self.side = config.get("side", "right")
                self.current_font = config.get("current_font", "Arial")
                self.theme = config.get("theme", "light")
                self.x_pos = config.get("x_pos", None)
                self.y_pos = config.get("y_pos", None)
            except Exception:
                self.button_size = 48
                self.side = "right"
                self.current_font = "Arial"
                self.theme = "light"
                self.x_pos = None
                self.y_pos = None
        else:
            self.button_size = 48
            self.side = "right"
            self.current_font = "Arial"
            self.theme = "light"
            self.x_pos = None
            self.y_pos = None
    
    def save_config(self):
        """Save current settings (including position) to a JSON file."""
        config = {
            "button_size": self.button_size,
            "side": self.side,
            "current_font": self.current_font,
            "theme": self.theme,
            "x_pos": self.x_pos,
            "y_pos": self.y_pos
        }
        with open(self.config_file, "w") as f:
            json.dump(config, f)
    
    def set_geometry_parameters(self):
        bs = self.button_size
        self.handle_height = bs // 4
        self.copy_height = bs // 2
        self.display_height = bs
        self.buttons_rows = 5
        
        if self.side in ["right", "left"]:
            # For right/left docking, we split the window horizontally:
            # The sliding (calculator) area width and a permanent bar.
            self.calc_width = 4 * bs
            self.total_width = self.calc_width + self.hidden_size
            self.full_height = self.handle_height + self.copy_height + self.display_height + (self.buttons_rows * bs)
            if self.y_pos is None:
                self.y_pos = int((self.screen_height - self.full_height) / 2)
            if self.side == "right":
                self.x_visible = self.screen_width - self.total_width  # fully expanded position
                self.x_hidden = self.screen_width - self.hidden_size    # retracted: only bar visible
            else:  # left docking
                self.x_visible = self.hidden_size
                self.x_hidden = self.calc_width
            self.current_offset = self.x_visible if self.is_expanded else self.x_hidden
            
        elif self.side in ["top", "bottom"]:
            # For top/bottom docking, we split the window vertically:
            self.calc_height = self.handle_height + self.copy_height + self.display_height + (self.buttons_rows * bs)
            self.total_height = self.calc_height + self.hidden_size
            self.full_width = 4 * bs
            if self.x_pos is None:
                self.x_pos = int((self.screen_width - self.full_width) / 2)
            if self.side == "top":
                self.y_visible = self.hidden_size
                self.y_hidden = self.calc_height
            else:
                self.y_visible = self.screen_height - self.total_height
                self.y_hidden = self.screen_height - self.hidden_size
            self.current_offset = self.y_visible if self.is_expanded else self.y_hidden
    
    def update_geometry(self):
        """
        Update window geometry. Also, place (or hide) the permanent bar label
        so that it appears only when the calculator is retracted.
        """
        if self.side in ["right", "left"]:
            self.root.geometry(f"{self.total_width}x{self.full_height}+{self.current_offset}+{self.y_pos}")
            if self.side == "right":
                if self.current_offset == self.x_hidden:
                    # Place the permanent bar in the rightmost area.
                    self.sideLabel.place(x=self.calc_width, y=0, width=self.hidden_size, height=self.full_height)
                else:
                    self.sideLabel.place_forget()
            else:
                if self.current_offset == self.x_hidden:
                    self.sideLabel.place(x=0, y=0, width=self.hidden_size, height=self.full_height)
                else:
                    self.sideLabel.place_forget()
        elif self.side in ["top", "bottom"]:
            self.root.geometry(f"{self.full_width}x{self.total_height}+{self.x_pos}+{self.current_offset}")
            if self.side == "top":
                if self.current_offset == self.y_hidden:
                    self.sideLabel.place(x=0, y=self.calc_height, width=self.full_width, height=self.hidden_size)
                else:
                    self.sideLabel.place_forget()
            else:
                if self.current_offset == self.y_hidden:
                    self.sideLabel.place(x=0, y=0, width=self.full_width, height=self.hidden_size)
                else:
                    self.sideLabel.place_forget()
    
    def build_ui(self):
        bs = self.button_size
        # Create the permanent bar label with vertical text.
        self.sideLabel = tk.Label(
            self.root,
            text="C\nA\nL\nC",
            font=(self.current_font, 10),
            bg=self.bg_color,
            fg=self.fg_color
        )
        
        if self.side in ["right", "left"]:
            sliding_x = 0 if self.side == "right" else self.hidden_size
            self.drag_handle = tk.Frame(self.root, bg=self.handle_color, height=self.handle_height, cursor="fleur")
            self.drag_handle.place(x=0, y=0, width=self.total_width, height=self.handle_height)
            self.drag_handle.bind("<ButtonPress-1>", self.start_move)
            self.drag_handle.bind("<B1-Motion>", self.do_move)
            copy_font_size = max(bs // 3 - 2, 8)
            self.copy_button = tk.Button(
                self.root, text="Copy", bg=self.btn_color, fg=self.fg_color,
                font=(self.current_font, copy_font_size),
                bd=0, relief="flat", activebackground=self.bg_color,
                command=self.copy_to_clipboard
            )
            self.copy_button.place(x=sliding_x, y=self.handle_height, width=self.calc_width // 2, height=self.copy_height)
            self.paste_button = tk.Button(
                self.root, text="Paste", bg=self.btn_color, fg=self.fg_color,
                font=(self.current_font, copy_font_size),
                bd=0, relief="flat", activebackground=self.bg_color,
                command=self.paste_from_clipboard
            )
            self.paste_button.place(x=sliding_x + self.calc_width // 2, y=self.handle_height, width=self.calc_width // 2, height=self.copy_height)
            output_y = self.handle_height + self.copy_height
            self.display = tk.Entry(
                self.root,
                font=(self.current_font, max(bs // 2 - 2, 8)),
                bd=0, relief="flat",
                bg=self.bg_color, fg=self.fg_color, justify="right",
                state="readonly"
            )
            self.display.place(x=sliding_x, y=output_y, width=self.calc_width, height=self.display_height)
            self.expression = ""
            grid_top = output_y + self.display_height
            self.buttons = []
            for i, row in enumerate(self.btn_texts):
                button_row = []
                for j, char in enumerate(row):
                    btn = tk.Button(
                        self.root, text=char, bg=self.btn_color, fg=self.fg_color,
                        font=(self.current_font, bs // 3),
                        bd=0, relief="flat", activebackground=self.bg_color,
                        command=lambda ch=char: self.on_button_click(ch)
                    )
                    x_pos = sliding_x + j * bs
                    y_pos = grid_top + i * bs
                    btn.place(x=x_pos, y=y_pos, width=bs, height=bs)
                    button_row.append(btn)
                self.buttons.append(button_row)
                
        elif self.side in ["top", "bottom"]:
            sliding_y = 0 if self.side == "top" else self.hidden_size
            self.drag_handle = tk.Frame(self.root, bg=self.handle_color, height=self.handle_height, cursor="fleur")
            self.drag_handle.place(x=0, y=sliding_y, width=self.full_width, height=self.handle_height)
            self.drag_handle.bind("<ButtonPress-1>", self.start_move)
            self.drag_handle.bind("<B1-Motion>", self.do_move)
            copy_font_size = max(bs // 3 - 2, 8)
            self.copy_button = tk.Button(
                self.root, text="Copy", bg=self.btn_color, fg=self.fg_color,
                font=(self.current_font, copy_font_size),
                bd=0, relief="flat", activebackground=self.bg_color,
                command=self.copy_to_clipboard
            )
            self.copy_button.place(x=0, y=sliding_y+self.handle_height, width=self.full_width//2, height=self.copy_height)
            self.paste_button = tk.Button(
                self.root, text="Paste", bg=self.btn_color, fg=self.fg_color,
                font=(self.current_font, copy_font_size),
                bd=0, relief="flat", activebackground=self.bg_color,
                command=self.paste_from_clipboard
            )
            self.paste_button.place(x=self.full_width//2, y=sliding_y+self.handle_height, width=self.full_width//2, height=self.copy_height)
            output_y = sliding_y+self.handle_height+self.copy_height
            self.display = tk.Entry(
                self.root,
                font=(self.current_font, max(bs//2 - 2, 8)),
                bd=0, relief="flat",
                bg=self.bg_color, fg=self.fg_color, justify="right",
                state="readonly"
            )
            self.display.place(x=0, y=output_y, width=self.full_width, height=self.display_height)
            self.expression = ""
            grid_top = output_y + self.display_height
            self.buttons = []
            for i, row in enumerate(self.btn_texts):
                button_row = []
                for j, char in enumerate(row):
                    btn = tk.Button(
                        self.root, text=char, bg=self.btn_color, fg=self.fg_color,
                        font=(self.current_font, bs//3),
                        bd=0, relief="flat", activebackground=self.bg_color,
                        command=lambda ch=char: self.on_button_click(ch)
                    )
                    x_pos = j * bs
                    y_pos = grid_top + i * bs
                    btn.place(x=x_pos, y=y_pos, width=bs, height=bs)
                    button_row.append(btn)
                self.buttons.append(button_row)
        self.update_geometry()
    
    def rebuild_ui(self):
        self.set_geometry_parameters()
        self.update_colors()
        for widget in self.root.winfo_children():
            widget.destroy()
        self.build_ui()
    
    def copy_to_clipboard(self):
        text = self.display.get()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
    
    def paste_from_clipboard(self):
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
        if self.side in ["right", "left"]:
            self.drag_start_y = event.y_root
            self.initial_y = self.y_pos
        elif self.side in ["top", "bottom"]:
            self.drag_start_x = event.x_root
            self.initial_x = self.x_pos
    
    def do_move(self, event):
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
        self.save_config()
    
    def on_button_click(self, char):
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
        mouse_x, mouse_y = pyautogui.position()
        if self.side in ["right", "left"]:
            if self.is_expanded:
                full_left = self.x_visible if self.side=="right" else 0
                full_right = self.screen_width if self.side=="right" else self.total_width
                full_top = self.y_pos
                full_bottom = self.y_pos + self.full_height
                if not (full_left <= mouse_x <= full_right and full_top <= mouse_y <= full_bottom):
                    self.slide_out()
                    self.is_expanded = False
            else:
                if self.side == "right":
                    bar_left = self.screen_width - self.hidden_size
                    bar_right = self.screen_width
                else:
                    bar_left = 0
                    bar_right = self.hidden_size
                bar_top = self.y_pos
                bar_bottom = self.y_pos + self.full_height
                if (bar_left <= mouse_x <= bar_right and bar_top <= mouse_y <= bar_bottom):
                    self.slide_in()
                    self.is_expanded = True
        elif self.side in ["top", "bottom"]:
            if self.is_expanded:
                full_left = self.x_pos
                full_right = self.x_pos + self.full_width
                full_top = self.y_visible
                full_bottom = self.y_visible + self.total_height
                if not (full_left <= mouse_x <= full_right and full_top <= mouse_y <= full_bottom):
                    self.slide_out()
                    self.is_expanded = False
            else:
                if self.side == "top":
                    bar_top = self.calc_height
                    bar_bottom = self.calc_height + self.hidden_size
                else:
                    bar_top = self.screen_height - self.hidden_size
                    bar_bottom = self.screen_height
                bar_left = self.x_pos
                bar_right = self.x_pos + self.full_width
                if (bar_left <= mouse_x <= bar_right and bar_top <= mouse_y <= bar_bottom):
                    self.slide_in()
                    self.is_expanded = True
        self.root.after(100, self.check_hover)
    
    def slide_in(self):
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
    
    def update_theme(self, new_theme):
        self.theme = new_theme
        self.theme_var.set(new_theme)
        self.update_colors()
        self.rebuild_ui()
        self.save_config()
    
    def update_size(self, new_size):
        self.button_size = new_size
        self.size_var.set(new_size)
        self.rebuild_ui()
        self.save_config()
    
    def update_side(self, new_side):
        self.side = new_side
        self.side_var.set(new_side)
        self.rebuild_ui()
        self.save_config()
    
    def update_font(self, new_font):
        self.current_font = new_font
        self.font_var.set(new_font)
        self.rebuild_ui()
        self.save_config()
    
    def show_settings_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        size_menu = tk.Menu(menu, tearoff=0)
        for size in [48, 64, 128, 256]:
            size_menu.add_radiobutton(label=f"{size}x{size}", variable=self.size_var,
                                      value=size, command=lambda s=size: self.update_size(s))
        menu.add_cascade(label="Change Size", menu=size_menu)
        font_menu = tk.Menu(menu, tearoff=0)
        for font in ["Arial", "Tahoma", "Calibri", "Verdana", "Segoe UI"]:
            font_menu.add_radiobutton(label=font, variable=self.font_var, value=font,
                                      command=lambda f=font: self.update_font(f))
        menu.add_cascade(label="Change Font", menu=font_menu)
        side_menu = tk.Menu(menu, tearoff=0)
        for dock in ["left", "right", "top", "bottom"]:
            side_menu.add_radiobutton(label=dock.capitalize(), variable=self.side_var, value=dock,
                                      command=lambda d=dock: self.update_side(d))
        menu.add_cascade(label="Change Side", menu=side_menu)
        theme_menu = tk.Menu(menu, tearoff=0)
        for th in ["light", "dark"]:
            theme_menu.add_radiobutton(label=th.capitalize(), variable=self.theme_var, value=th,
                                       command=lambda t=th: self.update_theme(t))
        menu.add_cascade(label="Change Theme", menu=theme_menu)
        menu.add_command(label="Exit", command=self.root.destroy)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

if __name__ == "__main__":
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()
