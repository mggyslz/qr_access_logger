# apps/admin_app.py
import sqlite3
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from core.error_utils import safe_exec
import os
from pathlib import Path
try:
    import customtkinter as ctk
    CTK = True
except Exception:
    CTK = False

from core.database import add_user, list_users, export_logs_csv
from core.security import generate_salt, hash_pin
from core.qr_utils import make_qr_token, generate_qr_image
from config.settings import EXPORT_DIR

EXPORT_DIR.mkdir(parents=True, exist_ok=True)

DB = None  # not used here, DB handled by core.database

# Choose widget set
if CTK:
    WidgetFrame = ctk.CTkFrame
    WidgetButton = ctk.CTkButton
    WidgetLabel = ctk.CTkLabel
    WidgetEntry = ctk.CTkEntry
    TextBoxClass = ctk.CTkTextbox
else:
    WidgetFrame = tk.Frame
    WidgetButton = tk.Button
    WidgetLabel = tk.Label
    WidgetEntry = tk.Entry
    # fallback textbox uses tk.Text

class AdminApp:
    def __init__(self):
        if CTK:
            ctk.set_appearance_mode("system")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
            self.root.protocol("WM_DELETE_WINDOW", self.logout)
            self.root.geometry("820x520")
            self.root.title("QR Access Logger — Admin")
        else:
            self.root = tk.Tk()
            self.root.geometry("820x520")
            self.root.title("QR Access Logger — Admin (tkinter)")

        self.build_ui()
        self.refresh_users()
        
    @safe_exec
    def build_ui(self):
        if CTK:
            tabs = ctk.CTkTabview(self.root, width=800, height=480)
            tabs.pack(padx=10, pady=10, fill="both", expand=True)
            tab_users = tabs.add("Users")
            tab_inside = tabs.add("Who's Inside")
            tab_logs = tabs.add("Access Logs")
        else:
            from tkinter import ttk
            tabs = ttk.Notebook(self.root)
            tabs.pack(fill="both", expand=True)
            tab_users = ttk.Frame(tabs); tabs.add(tab_users, text="Users")
            tab_inside = ttk.Frame(tabs); tabs.add(tab_inside, text="Who's Inside")
            tab_logs = ttk.Frame(tabs); tabs.add(tab_logs, text="Access Logs")

        # ---------- USERS TAB ----------
        from tkinter import ttk
        WidgetLabel(tab_users, text="Manage Users", font=("Helvetica", 16)).pack(pady=8)
        # --- Add User Section ---
        frm_add = tk.Frame(tab_users)
        frm_add.pack(pady=5, fill="x", padx=10)

        tk.Label(frm_add, text="Name:").grid(row=0, column=0, sticky="w")
        self.name_entry = tk.Entry(frm_add, width=25)
        self.name_entry.grid(row=0, column=1, padx=5)

        tk.Label(frm_add, text="Role:").grid(row=0, column=2, sticky="w")
        self.role_entry = tk.Entry(frm_add, width=15)
        self.role_entry.grid(row=0, column=3, padx=5)
        self.role_entry.insert(0, "Staff")

        tk.Label(frm_add, text="PIN:").grid(row=0, column=4, sticky="w")
        self.pin_entry = tk.Entry(frm_add, width=15, show="*")
        self.pin_entry.grid(row=0, column=5, padx=5)

        WidgetButton(frm_add, text="Add User", command=self.add_user).grid(row=0, column=6, padx=10)

        # Table
        self.user_table = ttk.Treeview(tab_users, columns=("ID", "Name", "Role", "Status"), show="headings", height=10)
        for col in ("ID", "Name", "Role", "Status"):
            self.user_table.heading(col, text=col)
            self.user_table.column(col, width=100)
        self.user_table.pack(padx=10, pady=6, fill="x")

        WidgetButton(tab_users, text="Refresh Users", command=self.refresh_users).pack(pady=5)

        # Edit controls
        frm_edit = ttk.Frame(tab_users)
        frm_edit.pack(pady=5, fill="x", padx=10)

        tk.Label(frm_edit, text="Name:").grid(row=0, column=0, sticky="w")
        self.edit_name = tk.Entry(frm_edit, width=25)
        self.edit_name.grid(row=0, column=1, padx=5)

        tk.Label(frm_edit, text="Role:").grid(row=0, column=2, sticky="w")
        self.edit_role = tk.Entry(frm_edit, width=15)
        self.edit_role.grid(row=0, column=3, padx=5)

        tk.Label(frm_edit, text="New PIN:").grid(row=1, column=0, sticky="w")
        self.edit_pin = tk.Entry(frm_edit, width=15, show="*")
        self.edit_pin.grid(row=1, column=1, padx=5)

        WidgetButton(frm_edit, text="Update", command=self.update_selected).grid(row=1, column=2, padx=6)
        WidgetButton(frm_edit, text="Deactivate", command=self.deactivate_selected).grid(row=1, column=3, padx=6)
        WidgetButton(frm_edit, text="Delete", command=self.delete_selected).grid(row=1, column=4, padx=6)

        # ---------- WHO'S INSIDE TAB ----------
        self.inside_text = tk.Text(tab_inside, width=80, height=20)
        self.inside_text.pack(padx=10, pady=10)
        WidgetButton(tab_inside, text="Refresh", command=self.refresh_inside).pack(pady=5)

        # ---------- LOGS TAB ----------
        self.logs_text = tk.Text(tab_logs, width=100, height=20)
        self.logs_text.pack(padx=10, pady=10)
        WidgetButton(tab_logs, text="Refresh", command=self.refresh_logs).pack(pady=5)

        # ---------- REPORTS TAB ----------
        if CTK:
            tab_reports = tabs.add("Reports")
        else:
            from tkinter import ttk
            tab_reports = ttk.Frame(tabs)
            tabs.add(tab_reports, text="Reports")

        self.reports_frame = tab_reports
        WidgetButton(tab_reports, text="Refresh Charts", command=self.refresh_reports).pack(pady=5)
        self.canvas_frame = tk.Frame(tab_reports)
        self.canvas_frame.pack(fill="both", expand=True)


    @safe_exec
    def add_user(self):
        from core.database import add_user
        import sqlite3
        from core.error_utils import log_error

        name = self.name_entry.get().strip()
        role = self.role_entry.get().strip()
        pin = self.pin_entry.get().strip()

        # --- Validation rules ---
        if not name or not pin:
            messagebox.showwarning("Invalid", "Name and PIN cannot be empty.")
            return
        if len(pin) < 4:
            messagebox.showwarning("Invalid", "PIN must be at least 4 digits.")
            return
        if not pin.isdigit():
            messagebox.showwarning("Invalid", "PIN must contain only numbers.")
            return
        if len(name) > 50:
            messagebox.showwarning("Invalid", "Name too long.")
            return

        # --- Try adding user safely ---
        try:
            qr_token = add_user(name, role, pin)
            generate_qr_image(qr_token, f"{name}.png")
            messagebox.showinfo("Success", f"User '{name}' added successfully.\nQR code generated.")
            self.refresh_users()
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate User", "A user with this name already exists.")
        except Exception as e:
            log_error(e, "add_user()")
            messagebox.showerror("Database Error", f"Could not add user: {e}")
                
    @safe_exec
    def get_selected_user(self):
        sel = self.user_table.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a user first.")
            return None
        vals = self.user_table.item(sel[0])["values"]
        return vals  # [user_id, name, role, status]

    @safe_exec
    def update_selected(self):
        from core.database import update_user
        user = self.get_selected_user()
        if not user: return
        user_id = user[0]
        name = self.edit_name.get().strip() or user[1]
        role = self.edit_role.get().strip() or user[2]
        pin = self.edit_pin.get().strip() or None
        update_user(user_id, name, role, pin)
        messagebox.showinfo("Updated", f"User {name} updated.")
        self.refresh_users()

    @safe_exec
    def deactivate_selected(self):
        from core.database import set_user_status
        user = self.get_selected_user()
        if not user: return
        new_status = "Inactive" if user[3] == "Active" else "Active"
        set_user_status(user[0], new_status)
        messagebox.showinfo("Status Changed", f"{user[1]} set to {new_status}.")
        self.refresh_users()

    @safe_exec
    def delete_selected(self):
        from core.database import delete_user
        user = self.get_selected_user()
        if not user: return
        if messagebox.askyesno("Confirm Delete", f"Delete {user[1]} permanently?"):
            delete_user(user[0])
            self.refresh_users()

    @safe_exec
    def refresh_users(self):
        from core.database import get_all_users
        for i in self.user_table.get_children():
            self.user_table.delete(i)
        rows = get_all_users()
        for r in rows:
            self.user_table.insert("", "end", values=r)

    @safe_exec        
    def refresh_inside(self):
        from core.database import get_current_inside
        rows = get_current_inside()
        self.inside_text.delete("1.0", "end")
        if not rows:
            self.inside_text.insert("end", "No users currently inside.\n")
            return
        for r in rows:
            uid, name, role, t = r
            self.inside_text.insert("end", f"{name} ({role}) — IN since {t}\n")
    @safe_exec
    def refresh_logs(self):
        from core.database import get_recent_logs
        rows = get_recent_logs(100)
        self.logs_text.delete("1.0", "end")
        for r in rows:
            log_id, name, action, ts, loc = r
            self.logs_text.insert("end", f"{log_id:04d} | {name:<20} | {action:<3} | {ts} | {loc}\n")
    @safe_exec
    def refresh_reports(self):
        from core.database import get_daily_counts, get_total_inside
        rows = get_daily_counts(7)
        total_in = get_total_inside()

        # clear previous charts
        for child in self.canvas_frame.winfo_children():
            child.destroy()

        if not rows:
            tk.Label(self.canvas_frame, text="No data yet.").pack()
            return

        days = [r[0] for r in rows]
        ins = [r[1] for r in rows]
        outs = [r[2] for r in rows]

        fig, axs = plt.subplots(1, 2, figsize=(8, 3))
        fig.suptitle(f"Total inside: {total_in}", fontsize=12)

        axs[0].bar(days, ins, label="IN", color="green")
        axs[0].bar(days, outs, bottom=ins, label="OUT", color="red")
        axs[0].set_title("Daily Movements")
        axs[0].legend()

        # pie chart
        axs[1].pie(
            [sum(ins), sum(outs)],
            labels=["Entries", "Exits"],
            autopct="%1.0f%%",
            colors=["green", "red"]
        )
        axs[1].set_title("Total Activity")

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
    def export_logs(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialdir=EXPORT_DIR.as_posix(),
                                            filetypes=[("CSV files", "*.csv")], title="Save logs as")
        if not path:
            return
        try:
            export_logs_csv(path)
            messagebox.showinfo("Exported", f"Logs exported to {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def open_qr_folder(self):
        import webbrowser, pathlib
        webbrowser.open(str(Path("qrcodes").absolute()))
        
    def logout(self):
        """Close the dashboard and return to login window."""
        self.root.destroy()
        from apps.login_window import LoginWindow
        login = LoginWindow()
        if login.run():
            AdminApp().run()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    AdminApp().run()
