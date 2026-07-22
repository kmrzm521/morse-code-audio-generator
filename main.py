"""程序入口。"""

import tkinter as tk

from morse_app.gui import MorseGeneratorApp


def main() -> None:
    root = tk.Tk()
    MorseGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
