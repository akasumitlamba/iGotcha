"""
iGotcha - Stay Active
Periodically moves the mouse within the inner 75% of the screen
to keep the user session alive.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import random
import pyautogui
import sys
import os
import time
import math
from datetime import datetime

# ── Windows AppUserModelID (custom taskbar grouping/icon) ──────────────────
if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "igotcha.stayactive.1.0"
    )

pyautogui.FAILSAFE = False   # prevent corner-crash when app moves mouse

# ── Colour palette ─────────────────────────────────────────────────────────
BG       = "#0b0b18"
CARD     = "#111124"
CARD2    = "#161630"
BORDER   = "#1f1f42"
ACCENT   = "#5b8df8"
TEXT     = "#ddddf5"
MUTED    = "#555575"
DIM      = "#8888aa"
GREEN    = "#34d280"
GREEN_D  = "#27b36a"
RED      = "#f05555"
RED_D    = "#cc3c3c"
CYAN     = "#38e8d8"

# ── Font shortcuts ──────────────────────────────────────────────────────────
F_HEAD  = ("Segoe UI",  22, "bold")
F_SUB   = ("Segoe UI",  9)
F_LABEL = ("Segoe UI",  8,  "bold")
F_BODY  = ("Segoe UI",  10)
F_BTN   = ("Segoe UI",  11, "bold")
F_MONO  = ("Consolas",  40, "bold")
F_STAT  = ("Consolas",  20, "bold")
F_TICK  = ("Segoe UI",  8)


# ──────────────────────────────────────────────────────────────────────────────
def _fmt_s(s: int) -> str:
    """Format seconds as '45s', '2m', '3m 30s'."""
    if s < 60:
        return f"{s}s"
    m, sec = divmod(s, 60)
    return f"{m}m {sec:02d}s" if sec else f"{m}m"


class MouseMover:
    """
    Background thread that periodically nudges the mouse within the inner 75%
    of the screen (12.5 % margin on every edge).
    """

    def __init__(self):
        self.running        = False
        self.interval_lo    = 120       # lower bound (seconds)
        self.interval_hi    = 120       # upper bound (seconds)
        self.thread         = None
        self.stop_event     = threading.Event()
        self.move_count     = 0
        self.last_move_time: str | None = None
        self.next_move_at:  float | None = None
        self._on_move       = None      # UI callback (called from worker thread)

    # -- public API -----------------------------------------------------------

    def set_callback(self, cb):
        self._on_move = cb

    def start(self, lo: int, hi: int):
        """Start moving. If lo == hi the interval is fixed; otherwise random each cycle."""
        if self.running:
            return
        self.interval_lo    = lo
        self.interval_hi    = hi
        self.move_count     = 0
        self.last_move_time = None
        self.running        = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running       = False
        self.next_move_at  = None
        self.stop_event.set()

    def seconds_remaining(self) -> float | None:
        if self.next_move_at is None or not self.running:
            return None
        return max(0.0, self.next_move_at - time.monotonic())

    # -- worker ---------------------------------------------------------------

    def _run(self):
        sw, sh = pyautogui.size()
        # Inner 75 % — exclude 12.5 % on each side
        x_min = int(sw * 0.125);  x_max = int(sw * 0.875)
        y_min = int(sh * 0.125);  y_max = int(sh * 0.875)
        MAX_STEP = 220   # maximum pixels per single move

        while self.running:
            # Pick a fresh random wait each cycle
            wait = random.randint(self.interval_lo, self.interval_hi)
            self.next_move_at = time.monotonic() + wait
            if self.stop_event.wait(wait):
                break
            if not self.running:
                break

            try:
                cx, cy  = pyautogui.position()
                tx      = random.randint(x_min, x_max)
                ty      = random.randint(y_min, y_max)

                # Cap displacement so the movement looks human / subtle
                dx, dy  = tx - cx, ty - cy
                dist    = (dx * dx + dy * dy) ** 0.5
                if dist > MAX_STEP:
                    scale = MAX_STEP / dist
                    tx    = int(cx + dx * scale)
                    ty    = int(cy + dy * scale)

                # Hard-clamp to safe zone
                tx = max(x_min, min(x_max, tx))
                ty = max(y_min, min(y_max, ty))

                dur = random.uniform(0.45, 0.95)
                pyautogui.moveTo(tx, ty, duration=dur, tween=pyautogui.easeInOutQuad)

                self.move_count    += 1
                self.last_move_time = datetime.now().strftime("%H:%M:%S")

                if self._on_move:
                    self._on_move()

            except Exception:
                self.running = False
                self.stop_event.set()
                break


# ──────────────────────────────────────────────────────────────────────────────
def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, fill, outline=""):
    """Draw a proper rounded rectangle using arcs + rectangles (no smooth-polygon distortion)."""
    r = min(r, (x2 - x1) // 2, (y2 - y1) // 2)
    # Three fill rectangles (cross shape)
    canvas.create_rectangle(x1 + r, y1,     x2 - r, y2,     fill=fill, outline="")
    canvas.create_rectangle(x1,     y1 + r, x2,     y2 - r, fill=fill, outline="")
    # Four corner arcs (each arc covers a 90-degree quadrant)
    canvas.create_arc(x1,     y1,     x1+2*r, y1+2*r, start= 90, extent=90, fill=fill, outline="")
    canvas.create_arc(x2-2*r, y1,     x2,     y1+2*r, start=  0, extent=90, fill=fill, outline="")
    canvas.create_arc(x2-2*r, y2-2*r, x2,     y2,     start=270, extent=90, fill=fill, outline="")
    canvas.create_arc(x1,     y2-2*r, x1+2*r, y2,     start=180, extent=90, fill=fill, outline="")


class RoundedButton(tk.Canvas):
    """A flat, rounded-corner button drawn on a Canvas."""

    def __init__(self, parent, text, command, bg_col, fg_col,
                 hover_col, radius=10, font=F_BTN, **kwargs):
        super().__init__(parent, bg=parent["bg"],
                         highlightthickness=0, cursor="hand2", **kwargs)
        self._text     = text
        self._command  = command
        self._bg_col   = bg_col
        self._hover    = hover_col
        self._fg_col   = fg_col
        self._radius   = radius
        self._font     = font
        self._active   = False

        self.bind("<Configure>",        self._draw)
        self.bind("<Enter>",            self._on_enter)
        self.bind("<Leave>",            self._on_leave)
        self.bind("<ButtonRelease-1>",  self._on_release)

    def configure_btn(self, text=None, bg_col=None, hover_col=None):
        if text      is not None: self._text    = text
        if bg_col    is not None: self._bg_col  = bg_col
        if hover_col is not None: self._hover   = hover_col
        self._draw()

    def _draw(self, *_):
        self.delete("all")
        w = self.winfo_width();  h = self.winfo_height()
        if w < 2 or h < 2:
            return
        c = self._hover if self._active else self._bg_col
        _draw_rounded_rect(self, 0, 0, w, h, self._radius, c)
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=self._fg_col, font=self._font, anchor="center")

    def _on_enter(self, *_):  self._active = True;  self._draw()
    def _on_leave(self, *_):  self._active = False; self._draw()

    def _on_release(self, e):
        if (0 <= e.x <= self.winfo_width() and
                0 <= e.y <= self.winfo_height()):
            self._command()


class CustomSlider(tk.Canvas):
    """
    A Canvas-based horizontal slider with:
    • A filled progress track (BORDER → ACCENT)
    • A prominent circular knob with a glow ring and white centre dot
    • Proper disabled/enabled state
    """
    _TRACK_H  = 4    # track thickness in px
    _KNOB_R   = 9    # knob radius in px
    _PAD      = 14   # horizontal padding so knob never clips the edge

    def __init__(self, parent, from_, to, variable, command=None, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, **kwargs)
        self._from     = from_
        self._to       = to
        self._var      = variable
        self._command  = command
        self._disabled = False

        self.bind("<Configure>",       self._draw)
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<B1-Motion>",       self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._var.trace_add("write", lambda *_: self.after_idle(self._draw))

    # -- geometry helpers ------------------------------------------------------

    def _val_to_x(self, val, w):
        ratio = (val - self._from) / (self._to - self._from)
        return self._PAD + ratio * (w - 2 * self._PAD)

    def _x_to_val(self, x, w):
        ratio = (x - self._PAD) / (w - 2 * self._PAD)
        ratio = max(0.0, min(1.0, ratio))
        return int(self._from + ratio * (self._to - self._from))

    # -- drawing ---------------------------------------------------------------

    def _draw_track_segment(self, x1, x2, cy, color):
        """Draw a thick line with rounded caps."""
        r = self._TRACK_H // 2
        if x2 > x1:
            self.create_rectangle(x1, cy - r, x2, cy + r, fill=color, outline="")
        # left cap
        self.create_oval(x1 - r, cy - r, x1 + r, cy + r, fill=color, outline="")
        # right cap
        self.create_oval(x2 - r, cy - r, x2 + r, cy + r, fill=color, outline="")

    def _draw(self, *_):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 4 or h < 4:
            return

        cy  = h // 2
        val = self._var.get()
        kx  = self._val_to_x(val, w)
        kr  = self._KNOB_R

        knob_col  = MUTED if self._disabled else ACCENT
        inner_col = "#8888aa" if self._disabled else "white"

        # Track — empty portion (right of knob)
        self._draw_track_segment(self._PAD, w - self._PAD, cy, BORDER)
        # Track — filled portion (left of knob)
        if kx > self._PAD:
            self._draw_track_segment(self._PAD, kx, cy, knob_col)

        # Glow ring (soft outer halo)
        glow_r = kr + 4
        self.create_oval(
            kx - glow_r, cy - glow_r, kx + glow_r, cy + glow_r,
            fill="#1a1a3a", outline=""
        )
        # Knob body
        self.create_oval(
            kx - kr, cy - kr, kx + kr, cy + kr,
            fill=knob_col, outline=BG, width=2
        )
        # White centre dot
        ir = 3
        self.create_oval(
            kx - ir, cy - ir, kx + ir, cy + ir,
            fill=inner_col, outline=""
        )

    # -- interaction -----------------------------------------------------------

    def _on_press(self, e):
        if not self._disabled:
            self._update(e.x)

    def _on_drag(self, e):
        if not self._disabled:
            self._update(e.x)

    def _on_release(self, e):
        if not self._disabled:
            self._update(e.x)

    def _update(self, x):
        w   = self.winfo_width()
        val = self._x_to_val(x, w)
        self._var.set(val)
        if self._command:
            self._command(str(val))
        self._draw()

    def set_disabled(self, disabled: bool):
        self._disabled = disabled
        self.config(cursor="arrow" if disabled else "hand2")
        self._draw()


# ──────────────────────────────────────────────────────────────────────────────
class App:

    _PULSE_FRAMES = [GREEN, "#47e898", "#55f0a5", "#47e898", GREEN,
                     GREEN_D, GREEN, "#47e898", GREEN]
    _FIXED_GEOMETRY = "390x610"
    _RANDOM_GEOMETRY = "390x695"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("iGotcha")
        self.root.configure(bg=BG)
        self.root.geometry(self._FIXED_GEOMETRY)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        self._setup_icon()
        self.mover = MouseMover()
        self.mover.set_callback(self._on_mouse_moved)
        self._pulse_idx = 0
        self._session_start: float | None = None

        self._build_ui()
        self._tick()

    # ── icon ──────────────────────────────────────────────────────────────────

    def _setup_icon(self):
        base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.abspath(".")
        ico  = os.path.join(base, "igotcha.ico")
        if os.path.exists(ico):
            try:
                self.root.iconbitmap(ico)
            except Exception:
                pass

    # ── UI build ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        PX = 22   # horizontal padding

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=PX, pady=(22, 10))

        tk.Label(hdr, text="iGotcha", bg=BG, fg=TEXT, font=F_HEAD).pack(side="left")
        tk.Label(hdr, text="  stay active", bg=BG, fg=MUTED, font=F_SUB).pack(
            side="left", pady=(9, 0))

        # ── Status strip ────────────────────────────────────────────────────
        self._status_strip(PX)

        # ── Countdown ───────────────────────────────────────────────────────
        self._countdown_block()

        # ── Stats row ───────────────────────────────────────────────────────
        self._stats_card(PX)

        # ── Interval slider ─────────────────────────────────────────────────
        self._interval_block(PX)

        # ── Buttons ──────────────────────────────────────────────────────────
        self._buttons_block(PX)

        # ── Footer ───────────────────────────────────────────────────────────
        tk.Label(self.root, text="moves within inner 75% of screen",
                 bg=BG, fg=MUTED, font=("Segoe UI", 7)).pack(pady=(6, 14))

    # -- sections --------------------------------------------------------------

    def _status_strip(self, px):
        card = tk.Frame(self.root, bg=CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=px, pady=(0, 6))

        inner = tk.Frame(card, bg=CARD)
        inner.pack(fill="x", padx=14, pady=10)

        self._dot_cv = tk.Canvas(inner, width=12, height=12, bg=CARD,
                                 highlightthickness=0)
        self._dot_cv.pack(side="left")
        self._dot   = self._dot_cv.create_oval(1, 1, 11, 11, fill=MUTED, outline="")

        self._status_lbl = tk.Label(inner, text="IDLE", bg=CARD, fg=MUTED,
                                    font=("Segoe UI", 10, "bold"))
        self._status_lbl.pack(side="left", padx=(10, 0))

        self._session_lbl = tk.Label(inner, text="", bg=CARD, fg=DIM, font=F_SUB)
        self._session_lbl.pack(side="right")

    def _countdown_block(self):
        f = tk.Frame(self.root, bg=BG)
        f.pack(pady=(6, 2))

        tk.Label(f, text="NEXT MOVE IN", bg=BG, fg=MUTED, font=F_LABEL).pack()
        self._cd_lbl = tk.Label(f, text="--:--", bg=BG, fg=TEXT, font=F_MONO)
        self._cd_lbl.pack()

    def _stats_card(self, px):
        card = tk.Frame(self.root, bg=CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", padx=px, pady=8)

        # -- left: moves made --
        lf = tk.Frame(card, bg=CARD)
        lf.pack(side="left", expand=True, fill="x", padx=14, pady=12)
        tk.Label(lf, text="MOVES MADE", bg=CARD, fg=MUTED, font=F_LABEL).pack(anchor="w")
        self._moves_lbl = tk.Label(lf, text="0", bg=CARD, fg=TEXT, font=F_STAT)
        self._moves_lbl.pack(anchor="w")

        # divider
        tk.Frame(card, bg=BORDER, width=1).pack(side="left", fill="y", pady=6)

        # -- right: last move --
        rf = tk.Frame(card, bg=CARD)
        rf.pack(side="left", expand=True, fill="x", padx=14, pady=12)
        tk.Label(rf, text="LAST MOVE", bg=CARD, fg=MUTED, font=F_LABEL).pack(anchor="w")
        self._last_lbl = tk.Label(rf, text="--:--:--", bg=CARD, fg=TEXT, font=F_STAT)
        self._last_lbl.pack(anchor="w")

    def _interval_block(self, px):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="x", padx=px, pady=(6, 4))

        # ── Header: "INTERVAL" label + Fixed / Random pill toggle ────────────
        hrow = tk.Frame(outer, bg=BG)
        hrow.pack(fill="x", pady=(0, 8))
        tk.Label(hrow, text="INTERVAL", bg=BG, fg=MUTED, font=F_LABEL).pack(side="left")

        pill = tk.Frame(hrow, bg=BORDER, padx=1, pady=1)
        pill.pack(side="right")
        self._seg_fixed = tk.Label(
            pill, text="  Fixed  ", bg=ACCENT, fg="white",
            font=("Segoe UI", 8, "bold"), cursor="hand2", padx=4, pady=2)
        self._seg_fixed.pack(side="left")
        self._seg_rand = tk.Label(
            pill, text="  Random  ", bg=CARD2, fg=MUTED,
            font=("Segoe UI", 8, "bold"), cursor="hand2", padx=4, pady=2)
        self._seg_rand.pack(side="left")
        self._seg_fixed.bind("<Button-1>", lambda _: self._set_interval_mode("fixed"))
        self._seg_rand.bind("<Button-1>",  lambda _: self._set_interval_mode("random"))
        self._interval_mode = "fixed"

        # ── Fixed frame ───────────────────────────────────────────────────────
        self._fixed_frame = tk.Frame(outer, bg=BG)
        self._fixed_frame.pack(fill="x")

        self._interval_var = tk.IntVar(value=120)
        fr_top = tk.Frame(self._fixed_frame, bg=BG)
        fr_top.pack(fill="x", pady=(0, 2))
        tk.Label(fr_top, text="EVERY", bg=BG, fg=MUTED, font=F_LABEL).pack(side="left")
        self._fixed_val_lbl = tk.Label(fr_top, text=_fmt_s(120), bg=BG, fg=ACCENT,
                                       font=("Consolas", 10, "bold"))
        self._fixed_val_lbl.pack(side="right")
        self._fixed_slider = CustomSlider(
            self._fixed_frame, from_=10, to=900,
            variable=self._interval_var,
            command=self._on_fixed_slider, height=28)
        self._fixed_slider.pack(fill="x")
        self._build_ticks(self._fixed_frame)

        # ── Random frame ──────────────────────────────────────────────────────
        self._random_frame = tk.Frame(outer, bg=BG)
        # Not packed yet — shown only when mode == "random"

        self._lo_var = tk.IntVar(value=60)
        self._hi_var = tk.IntVar(value=300)

        # FROM slider
        lo_top = tk.Frame(self._random_frame, bg=BG)
        lo_top.pack(fill="x", pady=(0, 2))
        tk.Label(lo_top, text="FROM", bg=BG, fg=MUTED, font=F_LABEL).pack(side="left")
        self._lo_val_lbl = tk.Label(lo_top, text=_fmt_s(60), bg=BG, fg=ACCENT,
                                    font=("Consolas", 10, "bold"))
        self._lo_val_lbl.pack(side="right")
        self._lo_slider = CustomSlider(
            self._random_frame, from_=10, to=900,
            variable=self._lo_var,
            command=self._on_lo_slider, height=28)
        self._lo_slider.pack(fill="x")
        self._build_ticks(self._random_frame)

        # TO slider
        hi_top = tk.Frame(self._random_frame, bg=BG)
        hi_top.pack(fill="x", pady=(8, 2))
        tk.Label(hi_top, text="TO", bg=BG, fg=MUTED, font=F_LABEL).pack(side="left")
        self._hi_val_lbl = tk.Label(hi_top, text=_fmt_s(300), bg=BG, fg=ACCENT,
                                    font=("Consolas", 10, "bold"))
        self._hi_val_lbl.pack(side="right")
        self._hi_slider = CustomSlider(
            self._random_frame, from_=10, to=900,
            variable=self._hi_var,
            command=self._on_hi_slider, height=28)
        self._hi_slider.pack(fill="x")
        self._build_ticks(self._random_frame)

    def _build_ticks(self, parent):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=(0, 2))
        tk.Label(f, text="10s", bg=BG, fg=MUTED, font=F_TICK).pack(side="left")
        tk.Label(f, text="15m", bg=BG, fg=MUTED, font=F_TICK).pack(side="right")

    def _set_interval_mode(self, mode: str):
        if mode == self._interval_mode:
            return
        self._interval_mode = mode
        if mode == "fixed":
            self._random_frame.pack_forget()
            self._fixed_frame.pack(fill="x")
            self._seg_fixed.config(bg=ACCENT, fg="white")
            self._seg_rand.config(bg=CARD2, fg=MUTED)
            self.root.geometry(self._FIXED_GEOMETRY)
        else:
            self._fixed_frame.pack_forget()
            self._random_frame.pack(fill="x")
            self._seg_fixed.config(bg=CARD2, fg=MUTED)
            self._seg_rand.config(bg=ACCENT, fg="white")
            self.root.geometry(self._RANDOM_GEOMETRY)

    def _buttons_block(self, px):
        f = tk.Frame(self.root, bg=BG)
        f.pack(fill="x", padx=px, pady=(14, 10))

        self._toggle_btn = RoundedButton(
            f, text="▶   Start", command=self.toggle,
            bg_col=GREEN, fg_col="white", hover_col=GREEN_D,
            radius=8, font=F_BTN, height=46
        )
        self._toggle_btn.pack(fill="x", pady=(0, 8))

        self._exit_btn = RoundedButton(
            f, text="Exit", command=self.quit_app,
            bg_col=CARD2, fg_col=DIM, hover_col=BORDER,
            radius=8, font=("Segoe UI", 9), height=40
        )
        self._exit_btn.pack(fill="x")

    # ── callbacks ─────────────────────────────────────────────────────────────

    def _on_fixed_slider(self, val):
        v = int(float(val))
        self._fixed_val_lbl.config(text=_fmt_s(v))

    def _on_lo_slider(self, val):
        lo = int(float(val))
        hi = self._hi_var.get()
        if lo > hi:                          # clamp: FROM never exceeds TO
            self._hi_var.set(lo)
            self._hi_val_lbl.config(text=_fmt_s(lo))
            self._hi_slider._draw()
        self._lo_val_lbl.config(text=_fmt_s(lo))

    def _on_hi_slider(self, val):
        hi = int(float(val))
        lo = self._lo_var.get()
        if hi < lo:                          # clamp: TO never drops below FROM
            self._lo_var.set(hi)
            self._lo_val_lbl.config(text=_fmt_s(hi))
            self._lo_slider._draw()
        self._hi_val_lbl.config(text=_fmt_s(hi))

    def _on_mouse_moved(self):
        # worker thread → schedule on main thread
        self.root.after(0, self._refresh_stats)

    def _refresh_stats(self):
        self._moves_lbl.config(text=str(self.mover.move_count))
        if self.mover.last_move_time:
            self._last_lbl.config(text=self.mover.last_move_time)

    def toggle(self):
        if not self.mover.running:
            # Resolve interval bounds
            if self._interval_mode == "fixed":
                lo = hi = self._interval_var.get()
                lbl = f"every {_fmt_s(lo)}"
            else:
                lo = self._lo_var.get()
                hi = self._hi_var.get()
                if lo > hi:
                    lo, hi = hi, lo
                lbl = f"{_fmt_s(lo)} – {_fmt_s(hi)}"

            self.mover.start(lo, hi)
            self._session_start = time.monotonic()

            self._toggle_btn.configure_btn(
                text="⏹   Stop", bg_col=RED, hover_col=RED_D)
            self._status_lbl.config(text="ACTIVE", fg=GREEN)
            self._session_lbl.config(text=lbl)

            # Lock sliders and mode toggle while running
            self._fixed_slider.set_disabled(True)
            self._lo_slider.set_disabled(True)
            self._hi_slider.set_disabled(True)
            self._seg_fixed.config(cursor="arrow")
            self._seg_rand.config(cursor="arrow")

            self._moves_lbl.config(text="0")
            self._last_lbl.config(text="--:--:--")
        else:
            self.mover.stop()
            self._toggle_btn.configure_btn(
                text="▶   Start", bg_col=GREEN, hover_col=GREEN_D)
            self._status_lbl.config(text="IDLE", fg=MUTED)
            self._session_lbl.config(text="")
            self._cd_lbl.config(text="--:--")
            self._dot_cv.itemconfig(self._dot, fill=MUTED)

            # Re-enable sliders and mode toggle
            self._fixed_slider.set_disabled(False)
            self._lo_slider.set_disabled(False)
            self._hi_slider.set_disabled(False)
            self._seg_fixed.config(cursor="hand2")
            self._seg_rand.config(cursor="hand2")
            self._session_start = None

    # ── animation tick (runs every 500 ms on main thread) ────────────────────

    def _tick(self):
        # Countdown
        rem = self.mover.seconds_remaining()
        if rem is not None:
            remaining_seconds = math.ceil(rem) if rem > 0 else 0
            m, s = divmod(remaining_seconds, 60)
            self._cd_lbl.config(text=f"{m:02d}:{s:02d}")

        # Pulse dot + session timer
        if self.mover.running:
            col = self._PULSE_FRAMES[self._pulse_idx % len(self._PULSE_FRAMES)]
            self._dot_cv.itemconfig(self._dot, fill=col)
            self._pulse_idx += 1

            if self._session_start is not None:
                elapsed = int(time.monotonic() - self._session_start)
                em, es = divmod(elapsed, 60)
                eh, em = divmod(em, 60)
                t = f"{eh:02d}:{em:02d}:{es:02d}" if eh else f"{em:02d}:{es:02d}"
                self._session_lbl.config(text=f"session {t}")

        self.root.after(200, self._tick)

    # ── exit ──────────────────────────────────────────────────────────────────

    def quit_app(self):
        self.mover.stop()
        if self.mover.thread and self.mover.thread.is_alive():
            self.mover.thread.join(timeout=1.5)
        self.root.quit()
        self.root.destroy()


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
