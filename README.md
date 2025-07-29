 
## Timer & Alarm Clock (Python Tkinter App)

A modern **timer and alarm app** for Windows (and Linux) built in Python with Tkinter and Pygame.  
Features an easy countdown timer and alarm with AM/PM support, custom alarm sounds, and a friendly UI.

---

## Features

- **Countdown Timer:** Set timer in hours, minutes, or seconds with progress bar & notifications.
- **Alarm:** Set a single alarm that rings at the chosen time.
- **Visual & Audio Alerts:** Get popups and sound notification when timer or alarm rings.
- **Custom Alarm Sound:** Pick your favorite `.wav` or `.mp3` audio.
- **Keyboard Shortcuts:**  
  - `Enter`: Start Timer  
  - `Escape`: Reset All  
- **User Tooltips:** Hover any button or field for explanations.

---


## Usage

1. **Install Requirements**

   Python 3.x must be installed.

pip install pygame

2. **Run the App**

Save your code (e.g., as `timer_alarm_app.py`) and run:

python timer_alarm_app.py

3. **Using the App**

- **Timer:**  
  - Enter a time and select Seconds/Minutes/Hours, then click `Start Timer`.  
  - Use Pause/Resume or Stop as needed.
- **Set Alarm:**  
  - Enter a 12-hour time (e.g., `07:30`), choose AM/PM, and click `Set Alarm`.
- **Choose Alarm Sound:**  
  - Click `Choose Sound` to pick your `.mp3` or `.wav` file, or use the default.

    ---

## Configuration/Files

- The default alarm sound is `alarm.wav` (place a valid `alarm.wav` in the same folder or use `Choose Sound`).

  ---

## Code Structure

- **Timer/Alarm logic:** Threaded for reliability and smooth UI.
- **UI:** Tkinter + ttk for a modern, easy interface.
- **Sound:** Played using `pygame` mixer.
- **Tooltips:** Custom tooltip code for field explanations.

  ---

## Platform Notes

- Windows and Linux supported (MacOS untested, may work).
- UI is fixed size (`430x520`).  
- For best look, use a modern theme, or enhance with packages like [ttkbootstrap](https://ttkbootstrap.readthedocs.io/).

  ---

## License

MIT License — feel free to use, fork, improve!

---

## Credits

- Idea, UI & logic: **Shital Singh**
- Tkinter, Pygame, Python.

---
## Issues & Suggestions
- PRs and UX/UI improvements are welcome!

---
**Enjoy your improved Python Timer & Alarm Clock app!**


