# gui/image_panel.py
import tkinter as tk
from PIL import Image, ImageTk
import threading
import numpy as np

class ImagePanel:
    def __init__(self, parent, state, status_var, save_callback):
        self.state = state
        self.status_var = status_var
        self.save_callback = save_callback

        self.image_canvas = tk.Canvas(parent, bg="white")
        self.image_canvas.pack(side="left", fill=tk.BOTH, expand=True)
        self.img_scrollbar = tk.Scrollbar(parent, orient="vertical", command=self.image_canvas.yview)
        self.img_scrollbar.pack(side="right", fill="y")
        self.image_canvas.configure(yscrollcommand=self.img_scrollbar.set)
        self.image_frame = tk.Frame(self.image_canvas)
        self.canvas_window = self.image_canvas.create_window((0, 0), window=self.image_frame, anchor="nw")
        self.image_canvas.bind(
            "<Configure>",
            lambda e: self.image_canvas.itemconfig(self.canvas_window, width=e.width)
        )
        self.image_frame.bind(
            "<Configure>",
            lambda e: self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
        )

        self.image_desc_entries = []
        self.photo_image_refs = []

    def display_images(self, page_index):
        """后台线程加载并在主线程显示图像"""
        for widget in self.image_frame.winfo_children():
            widget.destroy()

        if page_index not in self.state.images_content:
            self.status_var.set(f"第 {page_index + 1} 页无图像")
            return

        images = self.state.images_content[page_index]
        descriptions = self.state.image_descriptions.get(page_index, [""] * len(images))

        if len(descriptions) < len(images):
            descriptions += [""] * (len(images) - len(descriptions))
        elif len(descriptions) > len(images):
            descriptions = descriptions[:len(images)]

        self.state.image_descriptions[page_index] = descriptions

        self.image_desc_entries = []

        def load_images():
            rendered = []
            for idx, img_array in enumerate(images):
                try:
                    img = Image.fromarray(img_array)
                    img_resized = img.resize((200, 200), resample=Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img_resized)
                    rendered.append((idx, tk_img))
                except Exception:
                    rendered.append((idx, None))
            self.image_frame.after(0, lambda: self.render_images(rendered, descriptions, page_index))

        threading.Thread(target=load_images, daemon=True).start()
        self.status_var.set("正在加载图像...")

    def render_images(self, rendered, descriptions, page_index):
        self.photo_image_refs.clear()

        for idx, tk_img in rendered:
            row = tk.Frame(self.image_frame, pady=5)
            row.pack(fill="x", padx=10)
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=1)
            row.grid_columnconfigure(2, weight=1)

            desc_var = tk.StringVar(value=descriptions[idx])
            desc_entry = tk.Entry(row, textvariable=desc_var)
            desc_entry.grid(row=0, column=1, sticky="nsew", padx=5)
            self.image_desc_entries.append(desc_var)

            if tk_img:
                img_label = tk.Label(row, image=tk_img, width=200, height=200)
                img_label.grid(row=0, column=0, sticky="nsew", padx=5)
                self.photo_image_refs.append(tk_img)
            else:
                tk.Label(row, text="加载失败", width=25, height=10).grid(row=0, column=0)

            btn = tk.Button(row, text="删除", command=lambda i=idx: self.delete_image(i, page_index))
            btn.grid(row=0, column=2, sticky="nsew", padx=5)

        self.image_frame.update_idletasks()
        self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))
        self.status_var.set(f"第 {page_index + 1} 页，共 {len(rendered)} 张图")

    def delete_image(self, idx, page_index):
        if page_index in self.state.images_content and 0 <= idx < len(self.state.images_content[page_index]):
            del self.state.images_content[page_index][idx]
            del self.state.image_descriptions[page_index][idx]
            self.save_callback()
            self.display_images(page_index)

    def save_descriptions(self, page_index):
        if not self.image_desc_entries:
            return
        self.state.image_descriptions[page_index] = [v.get() for v in self.image_desc_entries]
        self.save_callback()
