import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import datetime
import json
import os
import pygame

# Initialize pygame mixer for sound playback
pygame.mixer.init()

CONFIG_FILE = "timer_alarm_config.json"
DEFAULT_SOUND = "alarm.wav"

# Helper functions for tooltips
class CreateToolTip(object):
    """
    Create a tooltip for a given widget.
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500  # milliseconds
        self.wraplength = 250  # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.id = None
        self.tw = None
    def enter(self, event=None):
        self.schedule()
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)
    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)
    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)  # removes all decorations
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
            background="#ffffe0", relief='solid', borderwidth=1,
            wraplength=self.wraplength, font=("Segoe UI", 9))
        label.pack(ipadx=1)
    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

# Sound playback helper
class SoundPlayer:
    def __init__(self):
        self.sound_path = DEFAULT_SOUND
        self.volume = 1.0  # Max volume

    def play(self):
        try:
            pygame.mixer.music.load(self.sound_path)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Sound playback error: {e}")

    def stop(self):
        pygame.mixer.music.stop()

class TimerAlarmApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Timer & Alarm Clock")
        self.configure(bg="#eaf1fb")
        self.geometry("430x520")
        self.resizable(False, False)
        self.configure_window_rounding()

        self.sound_player = SoundPlayer()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_config()

        self.active_timer_thread = None
        self.active_alarm_threads = {}
        self.timer_paused = threading.Event()
        self.timer_stopped = threading.Event()
        self.alarm_paused = {}  # alarm_id -> paused state
        self.alarm_stopped = {} # alarm_id -> stopped state

        self.build_ui()
        self.bind("<Return>", lambda e: self.start_timer())
        self.bind("<Escape>", lambda e: self.reset_all())

    def configure_window_rounding(self):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.SetWindowRgn(hwnd, ctypes.windll.gdi32.CreateRoundRectRgn(
                0, 0, 430, 520, 30, 30), True)
        except Exception:
            pass

    def build_ui(self):
        # ttk style
        style = ttk.Style(self)
        style.theme_use('clam')

        self.main_frame = ttk.Frame(self, padding=18)
        self.main_frame.pack(expand=True, fill='both')

        # Current Clock Display
        ttk.Label(self.main_frame, text="Current Time:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.current_time_var = tk.StringVar(value="")
        self.current_time_label = ttk.Label(self.main_frame, textvariable=self.current_time_var, font=("Segoe UI", 16))
        self.current_time_label.pack(anchor="w", pady=(0,12))
        self.update_clock()

        # Timer section
        ttk.Label(self.main_frame, text="Countdown Timer:", font=("Segoe UI", 13, "bold"), anchor='w').pack(anchor="w")
        timer_row = ttk.Frame(self.main_frame)
        timer_row.pack(fill='x', pady=6)
        self.timer_entry = ttk.Entry(timer_row, width=10, font=("Segoe UI", 12))
        self.timer_entry.pack(side='left', fill='x', expand=True)
        self.timer_unit_var = tk.StringVar(value="Minutes")
        self.timer_unit_combo = ttk.Combobox(timer_row, textvariable=self.timer_unit_var, values=["Seconds", "Minutes", "Hours"], state="readonly", width=10)
        self.timer_unit_combo.pack(side='left', padx=6)
        self.timer_unit_combo.current(1)  # default Minutes
        self.timer_start_button = ttk.Button(self.main_frame, text="Start Timer", command=self.start_timer)
        self.timer_start_button.pack(fill='x', pady=(0, 8))
        self.timer_pause_button = ttk.Button(self.main_frame, text="Pause Timer", command=self.pause_timer, state=tk.DISABLED)
        self.timer_pause_button.pack(fill='x', pady=(0, 8))
        self.timer_stop_button = ttk.Button(self.main_frame, text="Stop Timer", command=self.stop_timer, state=tk.DISABLED)
        self.timer_stop_button.pack(fill='x', pady=(0, 12))
        CreateToolTip(self.timer_entry, "Enter a positive number for the countdown")
        CreateToolTip(self.timer_unit_combo, "Select time unit")
        CreateToolTip(self.timer_start_button, "Start the countdown timer")
        CreateToolTip(self.timer_pause_button, "Pause/Resume the timer")
        CreateToolTip(self.timer_stop_button, "Stop and reset the timer")

        self.timer_progress = ttk.Progressbar(self.main_frame, orient='horizontal', length=400, mode='determinate')
        self.timer_progress.pack(pady=(0, 12))
        
        self.timer_status_var = tk.StringVar(value="Ready")
        self.timer_status_label = tk.Label(self.main_frame, textvariable=self.timer_status_var, font=("Segoe UI", 11, "italic"), fg="#1a73e8", bg="#eaf1fb")
        self.timer_status_label.pack()

        # Separator
        ttk.Separator(self.main_frame).pack(fill='x', pady=14)

        # Alarm section
        ttk.Label(self.main_frame, text="Set Alarm(s) (12-hour HH:MM):", font=("Segoe UI", 13, "bold"), anchor='w').pack(anchor='w')
        alarm_input_frame = ttk.Frame(self.main_frame)
        alarm_input_frame.pack(fill='x', pady=6)

        self.alarm_entry = ttk.Entry(alarm_input_frame, width=10, font=("Segoe UI", 12))
        self.alarm_entry.pack(side='left', fill='x', expand=True)
        self.ampm_var = tk.StringVar(value="AM")
        self.ampm_combo = ttk.Combobox(alarm_input_frame, textvariable=self.ampm_var, values=["AM", "PM"], state="readonly", width=5)
        self.ampm_combo.pack(side='left', padx=6)
        self.ampm_combo.current(0)

        self.set_alarm_button = ttk.Button(alarm_input_frame, text="Set Alarm", command=self.add_alarm)
        self.set_alarm_button.pack(side='left', padx=6)
        CreateToolTip(self.set_alarm_button, "Set/add this alarm time")


        self.alarm_sound_button = ttk.Button(self.main_frame, text="Choose Sound", command=self.choose_sound)
        self.alarm_sound_button.pack(fill='x', pady=(0,6))
        self.alarm_sound_label_var = tk.StringVar(value=DEFAULT_SOUND)
        ttk.Label(self.main_frame, textvariable=self.alarm_sound_label_var, font=("Segoe UI", 10)).pack(anchor='w', pady=(0,12))

        alarm_button_frame = ttk.Frame(self.main_frame)
        alarm_button_frame.pack(fill='x')
        self.alarm_add_button = ttk.Button(alarm_button_frame, text="Add Alarm", command=self.add_alarm)
        self.alarm_add_button.pack(fill='x', pady=(0, 8))
        CreateToolTip(self.alarm_add_button, "Add the alarm to the list")
        self.alarm_reset_button = ttk.Button(alarm_button_frame, text="Reset Alarms", command=self.reset_alarms, state=tk.DISABLED)
        self.alarm_reset_button.pack(side='left', fill='x', expand=True)

        # Alarm List
        self.alarms_frame = ttk.LabelFrame(self.main_frame, 
        text="Scheduled Alarms")
        self.alarms_frame.pack(fill='both', pady=8)
        self.alarms_listbox = tk.Listbox(self.alarms_frame, height=6, 
        font=("Segoe UI", 11), selectmode='extended')
        self.alarms_listbox.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(self.alarms_frame, orient='vertical', 
        command=self.alarms_listbox.yview)
        scrollbar.pack(side='right', fill='y')
        self.alarms_listbox.config(yscrollcommand=scrollbar.set)
        CreateToolTip(self.alarms_listbox, "Select multiple alarms with Shift/Ctrl + click. Press DELETE or use Delete button to remove.")
        self.delete_alarm_button = ttk.Button(self.main_frame, text="Delete Selected Alarm", command=self.delete_selected_alarm)
        self.delete_alarm_button.pack(fill='x', padx=10, pady=(0, 10))
        CreateToolTip(self.delete_alarm_button, "Delete the selected alarm from the list")


        self.alarms_listbox.bind('<Delete>', self.delete_selected_alarm)
        self.alarm_status_var = tk.StringVar(value="No alarms set")
        self.alarm_status_label = tk.Label(self.main_frame, textvariable=self.alarm_status_var, font=("Segoe UI", 11, "italic"), fg="#1a73e8", bg="#eaf1fb")
        self.alarm_status_label.pack(pady=(6,12))

        self.snooze_button = ttk.Button(self.main_frame, text="Snooze Alarm (5 min)", command=self.snooze_alarm, state=tk.DISABLED)
        self.snooze_button.pack(fill='x', pady=(0, 12))
        CreateToolTip(self.snooze_button, "Snooze the currently ringing alarm for 5 minutes")

        ttk.Label(self.main_frame, text="Created by: Shital Singh", font=("Segoe UI", 9), foreground="#888").pack(side='bottom', pady=(10,0))
    
    def update_clock(self):
        now = datetime.datetime.now()
        self.current_time_var.set(now.strftime("%I:%M:%S %p"))
        self.after(1000, self.update_clock)

    def alert(self, msg, alarm_id=None):
        # Visual blink of label
        def blink(times=6):
            def toggle(count):
                if count > 0:
                    current = self.alarm_status_label.cget("foreground")
                    self.alarm_status_label.config(foreground="#eaf1fb" if current == "#1a73e8" else "#1a73e8")
                    self.after(300, toggle, count-1)
                else:
                    self.alarm_status_label.config(foreground="#1a73e8")
            toggle(times)
        blink()

        messagebox.showinfo("Alert", msg)
        self.sound_player.play()
        # Enable snooze only if alarm_id is given
        if alarm_id is not None:
            self.snooze_button.config(state=tk.NORMAL)
            self.current_ringing_alarm = alarm_id

    def pause_timer(self):
        if self.timer_paused.is_set():
            self.timer_paused.clear()
            self.timer_pause_button.config(text="Pause Timer")
            self.timer_status_var.set(f"⏳ Timer resumed")
        else:
            self.timer_paused.set()
            self.timer_pause_button.config(text="Resume Timer")
            self.timer_status_var.set(f"⏸ Timer paused")

    def stop_timer(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to stop the timer?"):
            self.timer_stopped.set()
            self.timer_paused.clear()
            self.timer_status_var.set("Timer stopped.")
            self.timer_start_button.config(state=tk.NORMAL)
            self.timer_pause_button.config(state=tk.DISABLED, text="Pause Timer")
            self.timer_stop_button.config(state=tk.DISABLED)
            self.timer_progress['value'] = 0

    def reset_all(self):
        self.stop_timer()
        self.reset_alarms()
        self.timer_entry.delete(0, tk.END)
        self.alarm_entry.delete(0, tk.END)
        self.alarm_status_var.set("No alarms set")
        self.timer_status_var.set("Ready")
        self.snooze_button.config(state=tk.DISABLED)

    def start_timer(self):
        if self.active_timer_thread and self.active_timer_thread.is_alive():
            messagebox.showwarning("Timer Running", "A timer is already running. Please stop it first.")
            return
        try:
            value = float(self.timer_entry.get())
            if value <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", f"Enter timer as a number > 0")
            return

        unit = self.timer_unit_var.get()
        if unit == "Seconds":
            total_seconds = int(value)
        elif unit == "Minutes":
            total_seconds = int(value * 60)
        else:  # Hours
            total_seconds = int(value * 3600)

        self.timer_start_button.config(state=tk.DISABLED)
        self.timer_pause_button.config(state=tk.NORMAL, text="Pause Timer")
        self.timer_stop_button.config(state=tk.NORMAL)
        self.timer_paused.clear()
        self.timer_stopped.clear()

        self.timer_progress.config(maximum=total_seconds, value=total_seconds)
        self.timer_status_var.set(f"⏳ Time left: {value} {unit.lower()}")

        def run_timer():
            remaining = total_seconds
            while remaining >= 0:
                if self.timer_stopped.is_set():
                    break
                if self.timer_paused.is_set():
                    time.sleep(0.5)
                    continue
                mins, secs = divmod(remaining, 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    time_str = f"{hours:02}:{mins:02}:{secs:02}"
                else:
                    time_str = f"{mins:02}:{secs:02}"
                self.timer_status_var.set(f"⏳ Time left: {time_str}")
                self.timer_progress['value'] = remaining
                if remaining == 0:
                    break
                time.sleep(1)
                remaining -= 1

            if not self.timer_stopped.is_set():
                self.timer_status_var.set("Timer finished!")
                self.alert(f"⏰ Time is up! {value} {unit.lower()} have passed.")
            else:
                self.timer_status_var.set("Timer stopped.")
            self.timer_start_button.config(state=tk.NORMAL)
            self.timer_pause_button.config(state=tk.DISABLED, text="Pause Timer")
            self.timer_stop_button.config(state=tk.DISABLED)

        self.active_timer_thread = threading.Thread(target=run_timer, daemon=True)
        self.active_timer_thread.start()

        self.save_config()

    def choose_sound(self):
        filetypes = (("Audio Files", "*.wav *.mp3"), ("All files", "*.*"))
        filename = filedialog.askopenfilename(title="Select Alarm Sound", filetypes=filetypes)
        if filename:
            self.sound_player.sound_path = filename
            self.alarm_sound_label_var.set(os.path.basename(filename))
            self.save_config()

    def add_alarm(self):
        alarm_time = self.alarm_entry.get().strip()
        ampm = self.ampm_var.get()
        # Validate time
        try:
            t = datetime.datetime.strptime(alarm_time, "%I:%M")
            hour = t.hour
            minute = t.minute
            if ampm == "PM" and hour != 12:
                hour += 12
            if ampm == "AM" and hour == 12:
                hour = 0
            now = datetime.datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
        except Exception:
            messagebox.showerror("Invalid Input", "Enter time as HH:MM (12-hour) format")
            return

        # Add to listbox and threads dict
        alarm_str = target.strftime("%I:%M %p")
        if alarm_str in self.active_alarm_threads:
            messagebox.showwarning("Duplicate Alarm", f"Alarm for {alarm_str} already set")
            return

        self.alarms_listbox.insert(tk.END, alarm_str)
        self.alarm_status_var.set(f"{self.alarms_listbox.size()} alarm(s) set")
        self.alarm_reset_button.config(state=tk.NORMAL)
        self.alarm_entry.delete(0, tk.END)

        self.alarm_paused[alarm_str] = threading.Event()
        self.alarm_stopped[alarm_str] = threading.Event()
        self.alarm_entry.focus_set()

        def alarm_thread(alarm_id, alarm_target):
            while not self.alarm_stopped[alarm_id].is_set():
                if self.alarm_paused[alarm_id].is_set():
                    time.sleep(0.5)
                    continue
                if datetime.datetime.now() >= alarm_target:
                    self.alarm_status_var.set(f"Alarm ringing: {alarm_id}")
                    self.alert(f"⏰ Alarm for {alarm_id} is ringing!", alarm_id=alarm_id)
                    break
                time.sleep(1)
            # Remove from active alarms and update UI
            if alarm_id in self.active_alarm_threads:
                del self.active_alarm_threads[alarm_id]
            # Remove from alarms listbox (in main thread)
            self.after(0, lambda: self.remove_alarm_from_listbox(alarm_id))
            self.alarm_status_var.set(f"{self.alarms_listbox.size()} alarm(s) set")

        t = threading.Thread(target=alarm_thread, args=(alarm_str, target), daemon=True)
        self.active_alarm_threads[alarm_str] = t
        t.start()

        self.save_config()

    def remove_alarm_from_listbox(self, alarm_id):
        items = self.alarms_listbox.get(0, tk.END)
        if alarm_id in items:
            idx = items.index(alarm_id)
            self.alarms_listbox.delete(idx)

    def delete_selected_alarm(self, event=None):
        selection = self.alarms_listbox.curselection()
        if not selection:
            return
        alarms_to_delete = [self.alarms_listbox.get(i) for i in selection]
        if messagebox.askyesno("Delete Alarm(s)", f"Delete {len(alarms_to_delete)} selected alarm(s)?"):
            for alarm_id in alarms_to_delete:
                if alarm_id in self.alarm_stopped:
                    self.alarm_stopped[alarm_id].set()
                # Remove alarm from active alarms dict safely
                self.active_alarm_threads.pop(alarm_id, None)
            # Delete from the listbox, remove from end to start to keep indices valid
            for i in reversed(selection):
                self.alarms_listbox.delete(i)
            self.alarm_status_var.set(f"{self.alarms_listbox.size()} alarm(s) set")
            self.save_config()


    def reset_alarms(self):
        if messagebox.askyesno("Reset All", "Delete all alarms?"):
            # Stop all threads
            for alarm_id in list(self.alarm_stopped.keys()):
                self.alarm_stopped[alarm_id].set()
            self.active_alarm_threads.clear()
            self.alarm_paused.clear()
            self.alarm_stopped.clear()
            self.alarms_listbox.delete(0, tk.END)
            self.alarm_status_var.set("No alarms set")
            self.alarm_reset_button.config(state=tk.DISABLED)
            self.snooze_button.config(state=tk.DISABLED)
            self.save_config()

    def snooze_alarm(self):
        if hasattr(self, "current_ringing_alarm") and self.current_ringing_alarm:
            alarm_id = self.current_ringing_alarm
            self.sound_player.stop()
            self.snooze_button.config(state=tk.DISABLED)
            # Add 5 minutes to alarm (new thread)
            now = datetime.datetime.now()
            new_time = now + datetime.timedelta(minutes=5)
            alarm_str = new_time.strftime("%I:%M %p")
            if alarm_str in self.active_alarm_threads:
                messagebox.showwarning("Duplicate Alarm", f"Snooze alarm for {alarm_str} already exists")
                return
            self.alarms_listbox.insert(tk.END, alarm_str)
            self.alarm_status_var.set(f"{self.alarms_listbox.size()} alarm(s) set")
            self.alarm_reset_button.config(state=tk.NORMAL)
            self.alarm_paused[alarm_str] = threading.Event()
            self.alarm_stopped[alarm_str] = threading.Event()

            def alarm_thread(alarm_id_snooze, alarm_target):
                while not self.alarm_stopped[alarm_id_snooze].is_set():
                    if self.alarm_paused[alarm_id_snooze].is_set():
                        time.sleep(0.5)
                        continue
                    if datetime.datetime.now() >= alarm_target:
                        self.alarm_status_var.set(f"Alarm ringing: {alarm_id_snooze}")
                        self.alert(f"⏰ Snoozed alarm for {alarm_id_snooze} is ringing!", alarm_id=alarm_id_snooze)
                        break
                    time.sleep(1)
                if alarm_id_snooze in self.active_alarm_threads:
                    del self.active_alarm_threads[alarm_id_snooze]
                self.after(0, lambda: self.remove_alarm_from_listbox(alarm_id_snooze))
                self.alarm_status_var.set(f"{self.alarms_listbox.size()} alarm(s) set")

            t = threading.Thread(target=alarm_thread, args=(alarm_str, new_time), daemon=True)
            self.active_alarm_threads[alarm_str] = t
            t.start()
            self.current_ringing_alarm = None
        else:
            messagebox.showinfo("No Alarm", "No alarm is currently ringing to snooze.")

    def save_config(self):
        config = {
            "sound_path": self.sound_player.sound_path,
            "alarms": self.alarms_listbox.get(0, tk.END),
            "timer_entry": self.timer_entry.get(),
            "timer_unit": self.timer_unit_var.get(),
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_config(self):
        if not os.path.isfile(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            self.sound_player.sound_path = config.get("sound_path", DEFAULT_SOUND)
        except Exception as e:
            print(f"Error loading config: {e}")

    def on_close(self):
        """Handle cleanup and close the app."""
        try:
            self.sound_player.stop()
        except Exception:
            pass
        self.destroy()

if __name__ == "__main__":
    app = TimerAlarmApp()
    app.mainloop()
