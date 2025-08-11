# main.py
import tkinter as tk
import multiprocessing
from guis import PDFCleanerGUI

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = PDFCleanerGUI(root)
    root.geometry("1000x600")
    root.mainloop()
