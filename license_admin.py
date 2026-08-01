"""会员激活码生成工具入口。"""

import tkinter as tk

from morse_app.license_admin_gui import LicenseAdminApp


def main() -> None:
    root = tk.Tk()
    LicenseAdminApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
