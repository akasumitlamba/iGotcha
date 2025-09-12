import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import pyautogui
import sys
import os

class MouseMover:
    def __init__(self):
        self.running = False
        self.interval = 120
        self.thread = None
        self.stop_event = threading.Event()

    def start(self, interval):
        if not self.running:
            self.interval = interval
            self.running = True
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        self.stop_event.set()

    def run(self):
        screen_width, screen_height = pyautogui.size()
        # central 50% bounds
        x_min = int(screen_width * 0.25)
        x_max = int(screen_width * 0.75)
        y_min = int(screen_height * 0.25)
        y_max = int(screen_height * 0.75)

        while self.running:
            try:
                # Use wait() instead of sleep() so we can be interrupted
                if self.stop_event.wait(self.interval):
                    break  # Stop was requested
                
                if not self.running:
                    break

                # pick random safe target inside 50% zone
                target_x = random.randint(x_min, x_max)
                target_y = random.randint(y_min, y_max)

                # get current position
                curr_x, curr_y = pyautogui.position()

                # limit movement to ~150 px
                dx = target_x - curr_x
                dy = target_y - curr_y
                dist = (dx**2 + dy**2) ** 0.5
                if dist > 150:
                    scale = 150 / dist
                    target_x = int(curr_x + dx * scale)
                    target_y = int(curr_y + dy * scale)

                # clamp strictly to 50% zone
                target_x = max(x_min, min(x_max, target_x))
                target_y = max(y_min, min(y_max, target_y))

                # smooth human-like movement
                duration = random.uniform(0.6, 1.2)
                pyautogui.moveTo(target_x, target_y, duration=duration)

            except Exception as e:
                print("Error in mouse movement:", e)
                continue


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("iGotcha - Stay Active")
        self.root.geometry("320x200")
        self.root.resizable(False, False)

        # --- ICON FIX ---
        if getattr(sys, 'frozen', False):  # Running from PyInstaller bundle
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        icon_path = os.path.join(base_path, "igotcha.ico")

        try:
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print("Could not set icon:", e)

        # Mouse mover logic
        self.mover = MouseMover()

        # Styling
        style = ttk.Style()
        style.configure("TButton", padding=6, font=("Segoe UI", 10))
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10))

        # Interval Input
        ttk.Label(root, text="Move Interval (seconds):").pack(pady=10)
        self.interval_var = tk.IntVar(value=120)
        self.interval_spin = ttk.Spinbox(
            root, from_=10, to=3600, textvariable=self.interval_var, width=10
        )
        self.interval_spin.pack(pady=5)

        # Start/Stop button
        self.toggle_btn = ttk.Button(root, text="Start", command=self.toggle)
        self.toggle_btn.pack(pady=15)

        # Status
        self.status_label = ttk.Label(root, text="Status: Idle")
        self.status_label.pack(pady=10)

        # Exit button
        exit_btn = ttk.Button(root, text="Exit iGotcha", command=self.exit_app)
        exit_btn.pack(pady=5)

        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

    def toggle(self):
        if not self.mover.running:
            interval = self.interval_var.get()
            if interval < 10:
                messagebox.showwarning("Invalid", "Interval must be at least 10 seconds.")
                return
            self.mover.start(interval)
            self.toggle_btn.config(text="Stop")
            self.status_label.config(text=f"Status: Running every {interval}s")
        else:
            self.mover.stop()
            self.toggle_btn.config(text="Start")
            self.status_label.config(text="Status: Stopped")

    def exit_app(self):
        self.mover.stop()
        # Give the thread a moment to stop gracefully
        if self.mover.thread and self.mover.thread.is_alive():
            self.mover.thread.join(timeout=1.0)
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
