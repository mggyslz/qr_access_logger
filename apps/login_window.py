# apps/login_window.py
try:
    import customtkinter as ctk
    CTK=True
except Exception:
    import tkinter as ctk
    CTK=False

from tkinter import messagebox
from core.database import check_admin_credentials

class LoginWindow:
    def __init__(self):
        if CTK:
            ctk.set_appearance_mode("system")
            self.root = ctk.CTk()
        else:
            self.root = ctk.Tk()
        self.root.title("Admin Login")
        self.root.geometry("320x240")
        self.username = ctk.CTkEntry(self.root, placeholder_text="Username") if CTK else ctk.Entry(self.root)
        self.password = ctk.CTkEntry(self.root, placeholder_text="Password", show="*") if CTK else ctk.Entry(self.root, show="*")
        self.login_btn = ctk.CTkButton(self.root, text="Login", command=self.try_login) if CTK else ctk.Button(self.root, text="Login", command=self.try_login)
        self.username.pack(pady=12, padx=30, fill="x")
        self.password.pack(pady=12, padx=30, fill="x")
        self.login_btn.pack(pady=16)
        self.success=False

    def try_login(self):
        u=self.username.get().strip()
        p=self.password.get().strip()
        if not u or not p:
            messagebox.showwarning("Missing","Enter username and password.")
            return
        if check_admin_credentials(u,p):
            self.success=True
            self.root.destroy()
        else:
            messagebox.showerror("Error","Invalid credentials.")

    def run(self):
        self.root.mainloop()
        return self.success
