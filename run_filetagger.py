# run_filetagger.py
import ttkbootstrap as ttk
from filetagger.main_app import FileRenamerApp

if __name__ == "__main__":
    root = ttk.Window(themename="darkly")
    app = FileRenamerApp(root)
    root.mainloop()
