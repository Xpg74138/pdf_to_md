# gui/preview_panel.py
import tkinter as tk
from PIL import Image, ImageTk
import fitz

class PDFPreviewPanel:
    def __init__(self, parent, state, status_var):
        self.state = state
        self.status_var = status_var
        self.canvas_image_id = None
        self.photo_image = None
        self.zoom_factor = 1.0

        self.canvas_frame = tk.Frame(parent)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.x_scrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.y_scrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="white",
            xscrollcommand=self.x_scrollbar.set,
            yscrollcommand=self.y_scrollbar.set
        )
        self.x_scrollbar.config(command=self.canvas.xview)
        self.y_scrollbar.config(command=self.canvas.yview)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.y_scrollbar.grid(row=0, column=1, sticky="ns")
        self.x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind("<MouseWheel>", self.on_mousewheel)

        self.pdf_document = None  # 外部设置

    def set_document(self, pdf_document):
        self.pdf_document = pdf_document
        self.zoom_factor = 1.0

    def display_pdf(self, page_index):
        if not self.pdf_document or page_index >= len(self.pdf_document):
            return
        self.state.current_page = page_index

        page = self.pdf_document.load_page(page_index)
        zoom_matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=zoom_matrix)
        try:
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.photo_image = ImageTk.PhotoImage(img)
        except Exception as e:
            self.status_var.set(f"图像渲染失败: {str(e)}")
            return

        self.center_image(pix.width, pix.height)

    def center_image(self, w, h):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = cw // 2
        y = ch // 2

        if self.canvas_image_id is None:
            self.canvas_image_id = self.canvas.create_image(
                x, y, anchor=tk.CENTER, image=self.photo_image
            )
        else:
            self.canvas.coords(self.canvas_image_id, x, y)
            self.canvas.itemconfig(self.canvas_image_id, image=self.photo_image)

        self.canvas.config(scrollregion=(0, 0, w, h))

    def on_mousewheel(self, event):
        if not self.pdf_document:
            return
        scale = 1.1 if event.delta > 0 else 0.9
        self.zoom_factor = max(0.5, min(3.0, self.zoom_factor * scale))
        self.display_pdf(self.state.current_page)
