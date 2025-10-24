# core/gui_utils.py
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class PinPad(tk.Toplevel):
    def __init__(self, name="User"):
        super().__init__()
        self.title(f"Enter PIN - {name}")
        self.geometry("300x400")
        self.resizable(False, False)
        self.pin = ""
        self.result = None
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.create_widgets()

    def create_widgets(self):
        self.display = ttk.Entry(self, show="*", font=("Helvetica", 18), justify="center")
        self.display.pack(pady=20, ipadx=8, ipady=8, fill="x", padx=20)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(expand=True)

        digits = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["C", "0", "⏎"]
        ]
        for row_vals in digits:
            row = ttk.Frame(btn_frame)
            row.pack()
            for val in row_vals:
                btn = ttk.Button(row, text=val, width=6, command=lambda v=val: self.on_press(v))
                btn.pack(side="left", padx=5, pady=5)

    def on_press(self, value):
        if value == "C":
            self.pin = ""
        elif value == "⏎":
            self.result = self.pin
            self.destroy()
            return
        else:
            self.pin += value
        self.display.delete(0, "end")
        self.display.insert(0, "*" * len(self.pin))

    def on_cancel(self):
        self.result = None
        self.destroy()

def show_feedback(success=True, name="User"):
    win = tk.Toplevel()
    win.geometry("300x200")
    win.title("Result")
    color = "green" if success else "red"
    msg = "ACCESS GRANTED" if success else "ACCESS DENIED"
    lbl = tk.Label(win, text=msg, fg=color, font=("Helvetica", 20, "bold"))
    lbl.pack(expand=True)
    win.after(2000, win.destroy)  # close after 2 seconds
