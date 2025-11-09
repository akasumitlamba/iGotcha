import tkinter as tk
from tkinter import ttk, messagebox
import threading
import random
import pyautogui
import sys
import os
# --- Ensure custom taskbar icon on Windows ---
if sys.platform == "win32":
    import ctypes
    myappid = 'igotcha.app'  # arbitrary string — used as Windows AppUserModelID
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


class MouseMover:
    def __init__(self):
        self.running = False
        self.interval = 120
        self.thread = None
        self.stop_event = threading.Event()

    def start(self, interval):
        self.interval = interval
        if not self.running:
            self.running = True
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()

    def run(self):
        screen_width, screen_height = pyautogui.size()
        x_min = int(screen_width * 0.25)
        x_max = int(screen_width * 0.75)
        y_min = int(screen_height * 0.25)
        y_max = int(screen_height * 0.75)

        while self.running:
            try:
                if self.stop_event.wait(self.interval):
                    break
                target_x = random.randint(x_min, x_max)
                target_y = random.randint(y_min, y_max)
                curr_x, curr_y = pyautogui.position()
                dx, dy = target_x - curr_x, target_y - curr_y
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist > 150:
                    scale = 150 / dist
                    target_x = int(curr_x + dx * scale)
                    target_y = int(curr_y + dy * scale)
                duration = random.uniform(0.6, 1.2)
                pyautogui.moveTo(target_x, target_y, duration=duration)
            except Exception as e:
                messagebox.showerror("MouseMover Error", f"Error in mouse movement: {e}")
                self.stop()
                break


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("iGotcha - Stay Active 🖱️")
        self.root.geometry("360x250")
        self.root.resizable(False, False)

        icon_path = self._find_icon_path()
        if icon_path:
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.mover = MouseMover()
        self._set_theme()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

    def _find_icon_path(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        icon_path = os.path.join(base_path, "igotcha.ico")
        return icon_path if os.path.exists(icon_path) else None

    def _set_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e2f")
        style.configure("TLabel", background="#1e1e2f", foreground="white", font=("Segoe UI", 10))
        style.configure("TButton", background="#0078D7", foreground="white",
                        font=("Segoe UI", 10, "bold"), padding=8)
        style.map("TButton", background=[("active", "#005a9e")])
        style.configure("TSpinbox", fieldbackground="#2d2d44", foreground="white")

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True, fill="both")

        ttk.Label(frame, text="💤 Move Interval (seconds):").pack(pady=10)
        self.interval_var = tk.IntVar(value=120)
        self.interval_spin = ttk.Spinbox(
            frame, from_=10, to=3600, textvariable=self.interval_var, width=10, justify="center"
        )
        self.interval_spin.pack(pady=5)
        self.interval_spin.bind("<FocusOut>", self._validate_interval)

        self.toggle_btn = ttk.Button(frame, text="▶️ Start", command=self.toggle)
        self.toggle_btn.pack(pady=15, ipadx=8, ipady=4)

        self.status_label = ttk.Label(frame, text="Status: Idle")
        self.status_label.pack(pady=10)

        ttk.Button(frame, text="❌ Exit iGotcha", command=self.exit_app).pack(pady=10, ipadx=6)

    def _validate_interval(self, event=None):
        try:
            val = self.interval_var.get()
            if val < 10:
                self.interval_var.set(10)
                messagebox.showinfo("Info", "Minimum interval is 10 seconds.")
        except Exception:
            self.interval_var.set(10)
            messagebox.showerror("Error", "Interval must be an integer.")

    def toggle(self):
        interval = self.interval_var.get()
        self._validate_interval()
        if not self.mover.running:
            self.mover.start(interval)
            self.toggle_btn.config(text="⏹ Stop")
            self.status_label.config(text=f"Status: Running every {interval}s")
        else:
            self.mover.stop()
            self.toggle_btn.config(text="▶️ Start")
            self.status_label.config(text="Status: Stopped")

    def exit_app(self):
        self.mover.stop()
        if self.mover.thread and self.mover.thread.is_alive():
            self.mover.thread.join(timeout=1.0)
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
