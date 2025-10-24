# main.py
import argparse
from db_init import init_db
from apps.admin_app import AdminApp
from apps import scanner_app

def main():
    parser = argparse.ArgumentParser(description="QR Access Logger")
    parser.add_argument("mode", nargs='?', choices=["admin", "scanner", "init"], default="admin",
                        help="Mode to run: admin (GUI admin), scanner (camera scanner), init (create DB)")
    args = parser.parse_args()
    if args.mode == "init":
        init_db()
        return
    if args.mode == "admin":
        from apps.login_window import LoginWindow
        login = LoginWindow()
        if login.run():
            from apps.admin_app import AdminApp
            AdminApp().run()
        else:
            print("Login cancelled or failed.")
    elif args.mode == "scanner":
        scanner_app.scanner_loop()

if __name__ == "__main__":
    main()
