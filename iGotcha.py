"""
iGotcha - Stay Active
Periodically moves the mouse within the inner screen area to keep the session active.
Ultra-Modern Native Windows Edition powered by Edge Chromium WebView2.
"""

import webview
import threading
import random
import sys
import os
import time
import math
import io
import base64
from datetime import datetime

# Windows taskbar grouping & AppUserModelID
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("igotcha.stayactive.2.0")
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

# Pillow for icon loading
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Optional pyautogui import with native ctypes fallback
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


# ── Native Windows & Screen Utilities ────────────────────────────────────────
def get_screen_resolution():
    """Get screen width and height natively or via pyautogui."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            pass
    if HAS_PYAUTOGUI:
        return pyautogui.size()
    return 1920, 1080


def get_mouse_pos():
    """Get current cursor position (x, y)."""
    if sys.platform == "win32":
        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y
        except Exception:
            pass
    if HAS_PYAUTOGUI:
        return pyautogui.position()
    return 0, 0


def move_mouse_to(x, y, duration=0.6):
    """Smooth human-like mouse movement with ease-in-out curve."""
    if HAS_PYAUTOGUI:
        try:
            pyautogui.moveTo(x, y, duration=duration, tween=pyautogui.easeInOutQuad)
            return
        except Exception:
            pass

    if sys.platform == "win32":
        try:
            start_x, start_y = get_mouse_pos()
            steps = max(15, int(duration * 60))
            for i in range(1, steps + 1):
                t = i / steps
                ease = 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2
                cur_x = int(start_x + (x - start_x) * ease)
                cur_y = int(start_y + (y - start_y) * ease)
                ctypes.windll.user32.SetCursorPos(cur_x, cur_y)
                time.sleep(duration / steps)
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
        except Exception:
            pass


def get_logo_data_uri():
    """Extract highest resolution frame from igotcha.ico as base64 PNG data URI."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "igotcha.ico")
    if HAS_PIL and os.path.exists(ico_path):
        try:
            img = Image.open(ico_path)
            best_frame = None
            max_w = 0
            for i in range(getattr(img, "n_frames", 1)):
                img.seek(i)
                if img.width >= max_w:
                    max_w = img.width
                    best_frame = img.copy().convert("RGBA")
            buf = io.BytesIO()
            best_frame.save(buf, format="PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            pass
    return "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><path fill='%2322c55e' d='M6 16C6 10.477 10.477 6 16 6c5.523 0 10 4.477 10 10s-4.477 10-10 10S6 21.523 6 16z'/></svg>"


# ── Mouse Mover Engine ───────────────────────────────────────────────────────
class MouseMover:
    def __init__(self):
        self.running = False
        self.interval_lo = 120
        self.interval_hi = 120
        self.safe_margin = 0.125   # Inner 75% center screen
        self.max_step = 220
        self.move_speed = 0.6
        self.thread = None
        self.stop_event = threading.Event()
        self.move_count = 0
        self.last_move_time = None
        self.next_move_at = None
        self._on_move = None

    def set_callback(self, cb):
        self._on_move = cb

    def start(self, lo: int, hi: int):
        if self.running:
            return
        self.interval_lo = lo
        self.interval_hi = hi
        self.move_count = 0
        self.last_move_time = None
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.next_move_at = None
        self.stop_event.set()

    def seconds_remaining(self) -> float | None:
        if self.next_move_at is None or not self.running:
            return None
        return max(0.0, self.next_move_at - time.monotonic())

    def _run(self):
        sw, sh = get_screen_resolution()
        x_min = int(sw * self.safe_margin)
        x_max = int(sw * (1.0 - self.safe_margin))
        y_min = int(sh * self.safe_margin)
        y_max = int(sh * (1.0 - self.safe_margin))

        while self.running:
            wait = random.randint(self.interval_lo, self.interval_hi)
            self.next_move_at = time.monotonic() + wait

            if self.stop_event.wait(wait):
                break
            if not self.running:
                break

            try:
                cx, cy = get_mouse_pos()
                tx = random.randint(x_min, x_max)
                ty = random.randint(y_min, y_max)

                dx, dy = tx - cx, ty - cy
                dist = math.hypot(dx, dy)
                if dist > self.max_step:
                    scale = self.max_step / dist
                    tx = int(cx + dx * scale)
                    ty = int(cy + dy * scale)

                tx = max(x_min, min(x_max, tx))
                ty = max(y_min, min(y_max, ty))

                move_mouse_to(tx, ty, duration=self.move_speed)

                self.move_count += 1
                self.last_move_time = datetime.now().strftime("%H:%M:%S")

                if self._on_move:
                    self._on_move()

            except Exception:
                self.running = False
                self.stop_event.set()
                break


# ── Webview UI Backend Bridge ────────────────────────────────────────────────
class Api:
    def __init__(self, mover: MouseMover):
        self._mover = mover
        self._window = None
        self._session_start = None
        self._always_on_top = False

    def set_window(self, window):
        self._window = window

    def toggle(self, mode, fixed_sec, rand_lo, rand_hi):
        if not self._mover.running:
            if mode == "Fixed":
                lo = hi = int(fixed_sec)
            else:
                lo = int(rand_lo)
                hi = int(rand_hi)
            self._mover.start(lo, hi)
            self._session_start = time.monotonic()
            return {"running": True, "moves": 0, "last": "--:--:--"}
        else:
            self._mover.stop()
            self._session_start = None
            return {"running": False}

    def get_state(self):
        rem = self._mover.seconds_remaining()
        rem_str = "00:00"
        if rem is not None:
            s = math.ceil(rem) if rem > 0 else 0
            m, sec = divmod(s, 60)
            rem_str = f"{m:02d}:{sec:02d}"

        sess_str = "00:00"
        if self._mover.running and self._session_start is not None:
            elapsed = int(time.monotonic() - self._session_start)
            em, es = divmod(elapsed, 60)
            eh, em = divmod(em, 60)
            sess_str = f"{eh:02d}:{em:02d}:{es:02d}" if eh else f"{em:02d}:{es:02d}"

        return {
            "running": self._mover.running,
            "countdown": rem_str,
            "session": sess_str,
            "moves": self._mover.move_count,
            "last": self._mover.last_move_time or "--:--:--"
        }

    def save_settings(self, margin_pct, max_step, speed_mode, topmost):
        pct = int(margin_pct)
        self._mover.safe_margin = (100 - pct) / 200.0
        self._mover.max_step = int(max_step)
        self._mover.move_speed = 0.6 if speed_mode == "smooth" else 0.05
        self._always_on_top = bool(topmost)
        if self._window:
            self._window.on_top = self._always_on_top
        return True

    def minimize(self):
        if self._window:
            self._window.minimize()

    def close(self):
        self._mover.stop()
        if self._mover.thread and self._mover.thread.is_alive():
            self._mover.thread.join(timeout=1.0)
        if self._window:
            self._window.destroy()


def generate_html():
    logo_uri = get_logo_data_uri()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>iGotcha</title>
<style>
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    user-select: none;
    -webkit-user-select: none;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }}

  html, body {{
    width: 100%;
    height: 100%;
    background-color: #0b0f15;
    color: #f8fafc;
    overflow: hidden;
  }}

  .window {{
    width: 100%;
    height: 100%;
    background: #0e131b;
    border: 1px solid #1e2634;
    border-radius: 20px;
    padding: 16px 20px 20px 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
  }}

  /* ── Top Bar & Window Dragging ── */
  .top-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 32px;
    cursor: default;
  }}

  .brand-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    -webkit-app-region: drag;
  }}

  .logo-img {{
    width: 26px;
    height: 26px;
    object-fit: contain;
    filter: drop-shadow(0 2px 5px rgba(0,0,0,0.4));
    pointer-events: none;
  }}

  .brand-title {{
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
    pointer-events: none;
  }}

  .window-drag-region {{
    -webkit-app-region: drag;
    flex: 1;
    height: 100%;
    cursor: default;
  }}

  .win-controls {{
    display: flex;
    align-items: center;
    gap: 6px;
    color: #64748b;
    -webkit-app-region: no-drag;
  }}

  .win-btn {{
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 6px;
    transition: all 0.15s ease;
    -webkit-app-region: no-drag;
  }}
  .win-btn:hover {{ color: #f8fafc; background: rgba(255, 255, 255, 0.08); }}
  .win-btn.close:hover {{ color: #ffffff; background: #ef4444; }}

  /* ── Card 1: Status & Session ── */
  .status-card {{
    background: #111722;
    border: 1.5px solid #1a2332;
    border-radius: 14px;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: all 0.3s ease;
    -webkit-app-region: no-drag;
  }}

  .status-card.active {{
    border-color: #22c55e;
    box-shadow: 0 0 16px rgba(34, 197, 94, 0.15);
  }}

  .status-left {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .pulse-dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #475569;
    transition: all 0.3s ease;
  }}

  .status-card.active .pulse-dot {{
    background: #22c55e;
    box-shadow: 0 0 10px #22c55e, 0 0 20px rgba(34, 197, 94, 0.6);
    animation: glowPulse 2s infinite ease-in-out;
  }}

  @keyframes glowPulse {{
    0%, 100% {{ transform: scale(1); opacity: 1; }}
    50% {{ transform: scale(1.15); opacity: 0.85; }}
  }}

  .status-text {{
    font-size: 16px;
    font-weight: 700;
    color: #94a3b8;
    transition: color 0.3s ease;
  }}

  .status-card.active .status-text {{
    color: #22c55e;
  }}

  .session-group {{
    display: flex;
    align-items: center;
    gap: 14px;
  }}

  .session-divider {{
    width: 1px;
    height: 26px;
    background: #1e293b;
  }}

  .session-right {{
    text-align: right;
  }}

  .session-label {{
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }}

  .session-val {{
    font-size: 17px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.5px;
    font-variant-numeric: tabular-nums;
  }}

  /* ── Card 2: Next Move Big Display ── */
  .display-card {{
    background: #111722;
    border: 1px solid #1a2332;
    border-radius: 16px;
    padding: 16px 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    -webkit-app-region: no-drag;
  }}

  .display-header {{
    display: flex;
    align-items: center;
    gap: 6px;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
  }}

  .countdown-digits {{
    font-size: 52px;
    font-weight: 800;
    color: #cbd5e1;
    letter-spacing: 1.5px;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
    transition: all 0.3s ease;
  }}

  .display-card.active .countdown-digits {{
    color: #ffffff;
    text-shadow: 0 0 20px rgba(34, 197, 94, 0.45), 0 0 45px rgba(34, 197, 94, 0.2);
  }}

  /* ── Row: Dual Stats Cards ── */
  .stats-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    -webkit-app-region: no-drag;
  }}

  .stat-card {{
    background: #111722;
    border: 1px solid #1a2332;
    border-radius: 14px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
    -webkit-app-region: no-drag;
  }}

  .stat-header {{
    display: flex;
    align-items: center;
    gap: 6px;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
  }}

  .stat-val {{
    font-size: 22px;
    font-weight: 800;
    color: #ffffff;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  /* ── Card 3: Interval Setting ── */
  .interval-card {{
    background: #111722;
    border: 1px solid #1a2332;
    border-radius: 14px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    -webkit-app-region: no-drag;
  }}

  .interval-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    -webkit-app-region: no-drag;
  }}

  .interval-title {{
    display: flex;
    align-items: center;
    gap: 8px;
    color: #94a3b8;
    font-size: 13px;
    font-weight: 600;
  }}

  .pill-switch {{
    background: #080c12;
    border: 1px solid #1e2634;
    border-radius: 10px;
    padding: 3px;
    display: flex;
    gap: 2px;
    -webkit-app-region: no-drag;
  }}

  .pill-btn {{
    border: none;
    background: transparent;
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.2s ease;
    -webkit-app-region: no-drag;
  }}

  .pill-btn.active {{
    background: #132a20;
    border: 1px solid #22c55e;
    color: #22c55e;
    font-weight: 700;
  }}

  .slider-container {{
    display: flex;
    align-items: center;
    gap: 12px;
    -webkit-app-region: no-drag;
  }}

  .slider-wrapper {{
    flex: 1;
    position: relative;
    display: flex;
    align-items: center;
    min-width: 0;
    -webkit-app-region: no-drag;
  }}

  input[type=range] {{
    -webkit-appearance: none;
    width: 100%;
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
    outline: none;
    cursor: pointer;
    -webkit-app-region: no-drag;
    touch-action: none;
  }}

  input[type=range]::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #ffffff;
    border: 3px solid #22c55e;
    cursor: grab;
    box-shadow: 0 0 10px rgba(34, 197, 94, 0.6);
    -webkit-app-region: no-drag;
    transition: transform 0.1s ease;
  }}
  input[type=range]::-webkit-slider-thumb:active {{
    cursor: grabbing;
    transform: scale(1.2);
  }}

  .slider-val {{
    font-size: 14px;
    font-weight: 700;
    color: #22c55e;
    min-width: 50px;
    text-align: right;
    font-variant-numeric: tabular-nums;
    -webkit-app-region: no-drag;
  }}

  /* ── Action Button ── */
  .action-btn {{
    width: 100%;
    height: 50px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.3px;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    -webkit-app-region: no-drag;
  }}

  .action-btn.start {{
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #ffffff;
    box-shadow: 0 4px 18px rgba(16, 185, 129, 0.35);
  }}
  .action-btn.start:hover {{
    background: linear-gradient(135deg, #22c55e 0%, #10b981 100%);
    box-shadow: 0 6px 22px rgba(34, 197, 94, 0.45);
    transform: translateY(-1px);
  }}

  .action-btn.stop {{
    background: linear-gradient(135deg, #f87171 0%, #ef4444 100%);
    color: #ffffff;
    box-shadow: 0 4px 18px rgba(239, 68, 68, 0.35);
  }}
  .action-btn.stop:hover {{
    background: linear-gradient(135deg, #fca5a5 0%, #dc2626 100%);
    box-shadow: 0 6px 22px rgba(239, 68, 68, 0.45);
    transform: translateY(-1px);
  }}

  .action-btn:active {{
    transform: translateY(1px) scale(0.99);
  }}

  /* ── Settings Modal ── */
  .modal-overlay {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(8, 12, 18, 0.88);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    border-radius: 20px;
    display: none;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 20px;
    z-index: 100;
    opacity: 0;
    transition: opacity 0.2s ease;
    -webkit-app-region: no-drag;
  }}

  .modal-overlay.open {{
    display: flex;
    opacity: 1;
  }}

  .modal-card {{
    width: 100%;
    background: #111722;
    border: 1px solid #1e293b;
    border-radius: 16px;
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
    -webkit-app-region: no-drag;
  }}

  .modal-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .modal-title {{
    font-size: 16px;
    font-weight: 700;
    color: #ffffff;
  }}

  .modal-close {{
    cursor: pointer;
    color: #64748b;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 6px;
    transition: all 0.15s ease;
    -webkit-app-region: no-drag;
  }}
  .modal-close:hover {{ color: #ffffff; background: rgba(255,255,255,0.08); }}

  .setting-item {{
    display: flex;
    flex-direction: column;
    gap: 6px;
    -webkit-app-region: no-drag;
  }}

  .setting-label-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .setting-label {{
    font-size: 12px;
    font-weight: 600;
    color: #94a3b8;
  }}

  .setting-val-badge {{
    font-size: 12px;
    font-weight: 700;
    color: #22c55e;
  }}

  .setting-desc {{
    font-size: 10px;
    color: #475569;
  }}

  .toggle-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 2px 0;
    -webkit-app-region: no-drag;
  }}

  .switch {{
    position: relative;
    display: inline-block;
    width: 38px;
    height: 22px;
    -webkit-app-region: no-drag;
  }}

  .switch input {{
    opacity: 0;
    width: 0;
    height: 0;
  }}

  .slider-toggle {{
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background-color: #1e293b;
    transition: .3s;
    border-radius: 22px;
  }}

  .slider-toggle:before {{
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: .3s;
    border-radius: 50%;
  }}

  input:checked + .slider-toggle {{
    background-color: #22c55e;
  }}

  input:checked + .slider-toggle:before {{
    transform: translateX(16px);
  }}

  .modal-save-btn {{
    width: 100%;
    height: 38px;
    background: #22c55e;
    color: #0b0f15;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
    margin-top: 4px;
    transition: background 0.15s ease;
    -webkit-app-region: no-drag;
  }}
  .modal-save-btn:hover {{
    background: #4ade80;
  }}
</style>
</head>
<body>

<div class="window">
  <!-- Top Bar (Windows Native Style) -->
  <div class="top-bar">
    <div class="brand-header pywebview-drag-region">
      <img src="{logo_uri}" class="logo-img" alt="Logo" />
      <span class="brand-title">iGotcha</span>
    </div>
    
    <div class="window-drag-region pywebview-drag-region"></div>
    
    <div class="win-controls">
      <!-- Crisp Geometric Settings Gear Icon -->
      <div class="win-btn" id="btnSettings" title="Settings">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
      </div>
      <!-- Minimize Dash -->
      <div class="win-btn" id="btnMin" title="Minimize">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <line x1="4" y1="12" x2="20" y2="12"></line>
        </svg>
      </div>
      <!-- Close Cross -->
      <div class="win-btn close" id="btnClose" title="Close">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </div>
    </div>
  </div>

  <!-- Status & Session Card -->
  <div class="status-card" id="statusCard">
    <div class="status-left">
      <div class="pulse-dot"></div>
      <span class="status-text" id="statusText">Idle</span>
    </div>
    <div class="session-group">
      <div class="session-divider"></div>
      <div class="session-right">
        <div class="session-label">Session</div>
        <div class="session-val" id="sessionVal">00:00</div>
      </div>
    </div>
  </div>

  <!-- Big Display Card -->
  <div class="display-card" id="displayCard">
    <div class="display-header">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <polyline points="12 6 12 12 16 14"></polyline>
      </svg>
      <span>Next Move</span>
    </div>
    <div class="countdown-digits" id="countdownVal">00:00</div>
  </div>

  <!-- Dual Stats Row -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-header">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
        <span>Moves</span>
      </div>
      <div class="stat-val" id="movesVal">0</div>
    </div>
    
    <div class="stat-card">
      <div class="stat-header">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 14 10"></polyline>
        </svg>
        <span>Last</span>
      </div>
      <div class="stat-val" id="lastVal">--:--:--</div>
    </div>
  </div>

  <!-- Interval Card -->
  <div class="interval-card">
    <div class="interval-top">
      <div class="interval-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="4" y1="21" x2="4" y2="14"></line>
          <line x1="4" y1="10" x2="4" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12" y2="3"></line>
          <line x1="20" y1="21" x2="20" y2="16"></line>
          <line x1="20" y1="12" x2="20" y2="3"></line>
          <line x1="1" y1="14" x2="7" y2="14"></line>
          <line x1="9" y1="8" x2="15" y2="8"></line>
          <line x1="17" y1="16" x2="23" y2="16"></line>
        </svg>
        <span>Interval</span>
      </div>
      <div class="pill-switch">
        <button class="pill-btn active" id="btnModeFixed">Fixed</button>
        <button class="pill-btn" id="btnModeRandom">Random</button>
      </div>
    </div>

    <!-- Fixed Slider View -->
    <div class="slider-container" id="fixedView">
      <div class="slider-wrapper">
        <input type="range" id="fixedSlider" min="10" max="600" step="5" value="120">
      </div>
      <span class="slider-val" id="fixedValLabel">2m</span>
    </div>

    <!-- Random Slider View -->
    <div class="slider-container" id="randomView" style="display: none;">
      <div class="slider-wrapper" style="flex-direction: column; gap: 4px;">
        <input type="range" id="randLoSlider" min="10" max="300" step="5" value="60">
        <input type="range" id="randHiSlider" min="30" max="600" step="5" value="300">
      </div>
      <span class="slider-val" id="randValLabel">1m-5m</span>
    </div>
  </div>

  <!-- Start / Stop Button -->
  <button class="action-btn start" id="btnAction">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" id="actionIcon">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>
    <span id="actionText">Start</span>
  </button>

  <!-- Preferences Modal -->
  <div class="modal-overlay" id="modalOverlay">
    <div class="modal-card">
      <div class="modal-header">
        <span class="modal-title">Preferences</span>
        <div class="modal-close" id="btnModalClose">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </div>
      </div>

      <div class="setting-item">
        <div class="setting-label-row">
          <span class="setting-label">Safe Screen Area</span>
          <span class="setting-val-badge" id="marginVal">75%</span>
        </div>
        <input type="range" id="marginSlider" min="50" max="95" step="5" value="75">
        <span class="setting-desc">Keeps mouse movement safely inside center screen area.</span>
      </div>

      <div class="setting-item">
        <div class="setting-label-row">
          <span class="setting-label">Max Step Distance</span>
          <span class="setting-val-badge" id="stepVal">220 px</span>
        </div>
        <input type="range" id="stepSlider" min="50" max="500" step="10" value="220">
        <span class="setting-desc">Limits mouse movement distance per step.</span>
      </div>

      <div class="toggle-row">
        <div>
          <div class="setting-label">Always On Top</div>
          <div class="setting-desc">Keep iGotcha above other windows</div>
        </div>
        <label class="switch">
          <input type="checkbox" id="chkTopmost">
          <span class="slider-toggle"></span>
        </label>
      </div>

      <button class="modal-save-btn" id="btnSavePrefs">Save & Close</button>
    </div>
  </div>
</div>

<script>
  let currentMode = "Fixed";
  let isRunning = false;

  function formatTimeLabel(sec) {{
    sec = parseInt(sec);
    if (sec < 60) return sec + "s";
    let m = Math.floor(sec / 60);
    let s = sec % 60;
    return s === 0 ? m + "m" : m + "m " + s + "s";
  }}

  function updateSliderFill(slider) {{
    const min = slider.min || 0;
    const max = slider.max || 100;
    const val = slider.value;
    const pct = ((val - min) / (max - min)) * 100;
    slider.style.background = `linear-gradient(to right, #22c55e 0%, #22c55e ${{pct}}%, #1e293b ${{pct}}%, #1e293b 100%)`;
  }}

  // DOM Elements
  const statusCard = document.getElementById("statusCard");
  const statusText = document.getElementById("statusText");
  const sessionVal = document.getElementById("sessionVal");
  const displayCard = document.getElementById("displayCard");
  const countdownVal = document.getElementById("countdownVal");
  const movesVal = document.getElementById("movesVal");
  const lastVal = document.getElementById("lastVal");

  const btnModeFixed = document.getElementById("btnModeFixed");
  const btnModeRandom = document.getElementById("btnModeRandom");
  const fixedView = document.getElementById("fixedView");
  const randomView = document.getElementById("randomView");
  const fixedSlider = document.getElementById("fixedSlider");
  const fixedValLabel = document.getElementById("fixedValLabel");
  const randLoSlider = document.getElementById("randLoSlider");
  const randHiSlider = document.getElementById("randHiSlider");
  const randValLabel = document.getElementById("randValLabel");

  const btnAction = document.getElementById("btnAction");
  const actionIcon = document.getElementById("actionIcon");
  const actionText = document.getElementById("actionText");

  // Prevent event bubbling from controls that could trigger drag
  ['mousedown', 'pointerdown', 'touchstart'].forEach(evt => {{
    document.querySelectorAll('input[type=range], .pill-btn, .action-btn, .win-btn, .switch, .modal-card').forEach(el => {{
      el.addEventListener(evt, (e) => e.stopPropagation());
    }});
  }});

  // Mode switching
  btnModeFixed.addEventListener("click", () => {{
    currentMode = "Fixed";
    btnModeFixed.classList.add("active");
    btnModeRandom.classList.remove("active");
    fixedView.style.display = "flex";
    randomView.style.display = "none";
  }});

  btnModeRandom.addEventListener("click", () => {{
    currentMode = "Random";
    btnModeRandom.classList.add("active");
    btnModeFixed.classList.remove("active");
    fixedView.style.display = "none";
    randomView.style.display = "flex";
  }});

  // Sliders
  fixedSlider.addEventListener("input", (e) => {{
    fixedValLabel.textContent = formatTimeLabel(e.target.value);
    updateSliderFill(fixedSlider);
  }});
  updateSliderFill(fixedSlider);

  function updateRandLabel() {{
    let lo = parseInt(randLoSlider.value);
    let hi = parseInt(randHiSlider.value);
    if (lo > hi) {{
      randHiSlider.value = lo;
      hi = lo;
    }}
    randValLabel.textContent = formatTimeLabel(lo) + "-" + formatTimeLabel(hi);
    updateSliderFill(randLoSlider);
    updateSliderFill(randHiSlider);
  }}

  randLoSlider.addEventListener("input", updateRandLabel);
  randHiSlider.addEventListener("input", updateRandLabel);
  updateRandLabel();

  // Start / Stop Toggle
  btnAction.addEventListener("click", async () => {{
    if (window.pywebview && window.pywebview.api) {{
      const res = await window.pywebview.api.toggle(
        currentMode,
        fixedSlider.value,
        randLoSlider.value,
        randHiSlider.value
      );
      applyRunningState(res.running);
    }}
  }});

  function applyRunningState(running) {{
    isRunning = running;
    if (running) {{
      statusCard.classList.add("active");
      displayCard.classList.add("active");
      statusText.textContent = "Active";
      btnAction.className = "action-btn stop";
      actionIcon.innerHTML = '<rect x="5" y="5" width="14" height="14" rx="2"></rect>';
      actionText.textContent = "Stop";
    }} else {{
      statusCard.classList.remove("active");
      displayCard.classList.remove("active");
      statusText.textContent = "Idle";
      countdownVal.textContent = "00:00";
      sessionVal.textContent = "00:00";
      btnAction.className = "action-btn start";
      actionIcon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
      actionText.textContent = "Start";
    }}
  }}

  // Window Controls
  document.getElementById("btnMin").addEventListener("click", () => {{
    if (window.pywebview && window.pywebview.api) window.pywebview.api.minimize();
  }});

  document.getElementById("btnClose").addEventListener("click", () => {{
    if (window.pywebview && window.pywebview.api) window.pywebview.api.close();
  }});

  // Settings Modal
  const modalOverlay = document.getElementById("modalOverlay");
  const btnSettings = document.getElementById("btnSettings");
  const btnModalClose = document.getElementById("btnModalClose");
  const marginSlider = document.getElementById("marginSlider");
  const marginVal = document.getElementById("marginVal");
  const stepSlider = document.getElementById("stepSlider");
  const stepVal = document.getElementById("stepVal");
  const chkTopmost = document.getElementById("chkTopmost");
  const btnSavePrefs = document.getElementById("btnSavePrefs");

  btnSettings.addEventListener("click", () => {{
    modalOverlay.classList.add("open");
  }});

  btnModalClose.addEventListener("click", () => {{
    modalOverlay.classList.remove("open");
  }});

  marginSlider.addEventListener("input", (e) => {{
    marginVal.textContent = e.target.value + "%";
    updateSliderFill(marginSlider);
  }});
  updateSliderFill(marginSlider);

  stepSlider.addEventListener("input", (e) => {{
    stepVal.textContent = e.target.value + " px";
    updateSliderFill(stepSlider);
  }});
  updateSliderFill(stepSlider);

  btnSavePrefs.addEventListener("click", async () => {{
    if (window.pywebview && window.pywebview.api) {{
      await window.pywebview.api.save_settings(
        marginSlider.value,
        stepSlider.value,
        "smooth",
        chkTopmost.checked
      );
    }}
    modalOverlay.classList.remove("open");
  }});

  // State Polling Loop (150ms)
  async function pollState() {{
    if (window.pywebview && window.pywebview.api) {{
      try {{
        const state = await window.pywebview.api.get_state();
        if (state.running !== isRunning) {{
          applyRunningState(state.running);
        }}
        if (state.running) {{
          countdownVal.textContent = state.countdown;
          sessionVal.textContent = state.session;
          movesVal.textContent = state.moves;
          lastVal.textContent = state.last;
        }}
      }} catch (err) {{}}
    }}
  }}

  window.addEventListener('pywebviewready', () => {{
    setInterval(pollState, 150);
  }});
</script>
</body>
</html>
"""
    return html


def main():
    mover = MouseMover()
    api = Api(mover)

    # Calculate centered position on screen
    sw, sh = get_screen_resolution()
    win_w, win_h = 370, 580
    pos_x = (sw - win_w) // 2
    pos_y = (sh - win_h) // 2

    html_content = generate_html()

    window = webview.create_window(
        title="iGotcha",
        html=html_content,
        js_api=api,
        width=win_w,
        height=win_h,
        x=pos_x,
        y=pos_y,
        resizable=False,
        frameless=True,
        easy_drag=False,
        on_top=False,
        background_color="#0b0f15"
    )
    api.set_window(window)

    # Start Edge WebView2
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    main()
