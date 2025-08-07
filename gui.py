import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import fitz  # PyMuPDF
import threading
import queue
import numpy as np
import multiprocessing
import os
import sys
from PIL import Image, ImageTk
import json
from parse import extract_pdf
import shutil
import time
from tkhtmlview import HTMLLabel
import markdown

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class PDFCleanerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF转Markdown编辑器")
        self.root.geometry("1200x700")

        # 变量初始化
        self.pdf_path = None
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.md_content = []
        self.photo_image = None
        self.image_descriptions = {}
        self.images_content = {}
        self.export_dir = None
        self.record_path = None
        self.canvas_image_id = None  # 用于复用canvas上的图片

        self.communication_queue = queue.Queue()

        # 主布局
        self.main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧PDF预览区
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=1)

        self.canvas_frame = ttk.Frame(self.left_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.x_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.y_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)

        self.pdf_canvas = tk.Canvas(
            self.canvas_frame,
            bg='white',
            xscrollcommand=self.x_scrollbar.set,
            yscrollcommand=self.y_scrollbar.set
        )
        self.x_scrollbar.config(command=self.pdf_canvas.xview)
        self.y_scrollbar.config(command=self.pdf_canvas.yview)
        self.pdf_canvas.grid(row=0, column=0, sticky="nsew")
        self.y_scrollbar.grid(row=0, column=1, sticky="ns")
        self.x_scrollbar.grid(row=1, column=0, sticky="ew")
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.pdf_canvas.bind("<MouseWheel>", self.on_mousewheel)

        # 右侧Notebook
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=1)
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Markdown编辑器
        self.md_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.md_tab, text="编辑")
        self.md_text = tk.Text(
            self.md_tab,
            wrap=tk.WORD,
            font=("Consolas", 12),
            undo=True,
            maxundo=-1
        )
        self.md_scrollbar = ttk.Scrollbar(self.md_tab, command=self.md_text.yview)
        self.md_text.config(yscrollcommand=self.md_scrollbar.set)
        self.md_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.md_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.md_text.bind("<<Modified>>", self.on_md_modified)


        # Markdown预览标签页
        self.preview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.preview_tab, text="预览")
        self.preview_html_label = HTMLLabel(self.preview_tab, html="", background="white", width=100)
        self.preview_html_label.pack(fill=tk.BOTH, expand=True)
        

        # 图像显示标签页
        self.img_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.img_tab, text="图像")
        self.image_canvas = tk.Canvas(self.img_tab, bg="white")
        self.image_canvas.pack(side="left", fill=tk.BOTH, expand=True)
        self.img_scrollbar = ttk.Scrollbar(self.img_tab, orient="vertical", command=self.image_canvas.yview)
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

        # 底部控制栏
        self.bottom_frame = ttk.Frame(root)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        self.btn_frame = ttk.Frame(self.bottom_frame)
        self.btn_frame.pack(side=tk.LEFT, padx=5)
        self.import_btn = ttk.Button(
            self.btn_frame,
            text="导入PDF",
            command=self.import_pdf,
            width=10
        )
        self.import_btn.pack(side=tk.LEFT, padx=2)
        self.export_btn = ttk.Button(
            self.btn_frame,
            text="导出",
            command=self.export,
            state=tk.DISABLED,
            width=10
        )
        self.export_btn.pack(side=tk.LEFT, padx=2)

        # 页面导航
        self.nav_frame = ttk.Frame(self.bottom_frame)
        self.nav_frame.pack(side=tk.LEFT, padx=10)
        self.prev_btn = ttk.Button(
            self.nav_frame,
            text="上一页",
            command=self.prev_page,
            state=tk.DISABLED
        )
        self.prev_btn.pack(side=tk.LEFT, padx=2)
        self.next_btn = ttk.Button(
            self.nav_frame,
            text="下一页",
            command=self.next_page,
            state=tk.DISABLED
        )
        self.next_btn.pack(side=tk.LEFT, padx=2)
        self.page_label = ttk.Label(self.nav_frame, text="页码：")
        self.page_label.pack(side=tk.LEFT, padx=(15, 2))
        self.page_var = tk.StringVar(value="0/0")
        self.page_display = ttk.Label(self.nav_frame, textvariable=self.page_var, width=8)
        self.page_display.pack(side=tk.LEFT, padx=2)
        self.goto_label = ttk.Label(self.nav_frame, text="转到：")
        self.goto_label.pack(side=tk.LEFT, padx=(10, 2))
        self.goto_entry = ttk.Entry(self.nav_frame, width=5)
        self.goto_entry.pack(side=tk.LEFT, padx=2)
        self.jump_btn = ttk.Button(
            self.nav_frame,
            text="跳转",
            command=self.goto_page,
            state=tk.DISABLED
        )
        self.jump_btn.pack(side=tk.LEFT, padx=2)

        # 进度条
        self.progress_frame = ttk.Frame(self.bottom_frame)
        self.progress_frame.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, expand=True, padx=5)

        # 状态栏
        self.status_frame = ttk.Frame(root)
        self.status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(
            self.status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X)

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.check_processing_queue()

    def import_pdf(self):
        """导入PDF文件，并自动查找同名目录恢复历史记录"""
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        self.reset_state()
        self.pdf_path = file_path

        # 检查是否有同名导出目录
        pdf_dir = os.path.dirname(file_path)
        pdf_name = os.path.splitext(os.path.basename(file_path))[0]
        export_folder = os.path.join(pdf_dir, pdf_name)
        record_path = os.path.join(export_folder, "record.json")

        if os.path.exists(record_path):
            # 有历史记录，询问是否恢复
            if messagebox.askyesno("恢复历史", f"检测到历史编辑记录，是否恢复？\n{record_path}"):
                self.export_dir = export_folder
                self.restore_from_record(record_path)
                self.status_var.set("已从历史记录恢复")
                return
        try:
            self.pdf_document = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_document)
            self.export_dir = export_folder
            self.update_ui_after_import()
            self.status_var.set(f"正在处理: {os.path.basename(file_path)}...")
            threading.Thread(target=self.start_processing, daemon=True).start()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开PDF文件: {str(e)}")
            self.status_var.set("导入失败")

    def restore_from_record(self, record_path):
        """从record.json恢复"""
        with open(record_path, "r", encoding="utf-8") as f:
            record = json.load(f)
        self.export_dir = os.path.dirname(record_path)
        self.pdf_path = record["pdf_path"]
        self.current_page = record.get("current_page", 0)
        self.md_content = []
        self.image_descriptions = {}
        self.images_content = {}
        # 恢复md
        for i, md_path in record["md_files"].items():
            with open(os.path.join(self.export_dir, md_path), "r", encoding="utf-8") as f:
                self.md_content.append(f.read())
        # 恢复图片
        for i, img_list in record["images_content"].items():
            self.images_content[int(i)] = []
            for img_path in img_list:
                img = Image.open(os.path.join(self.export_dir, img_path))
                self.images_content[int(i)].append(np.array(img))
        # 恢复图像描述
        for i, img_descriptions_list in record["image_descriptions"].items():
            self.image_descriptions[int(i)] = []
            for img_descriptions in img_descriptions_list:
                self.image_descriptions[int(i)].append(img_descriptions)
        # 恢复PDF
        if self.pdf_path and os.path.exists(self.pdf_path):
            self.pdf_document = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_document)
            self.display_page(self.current_page)
            self.update_ui_after_import()
            self.update_navigation_buttons()


    def save_to_record(self):
        if not self.export_dir:
            return

        # 1. 创建目录
        img_dir = os.path.join(self.export_dir, "images")
        os.makedirs(img_dir, exist_ok=True)

        md_files = {}
        images_content_paths = {}

        # --- 测试 MD 保存耗时 ---
        t_md_start = time.time()
        for i, md in enumerate(self.md_content):
            md_path = f"page_{i+1}.md"
            with open(os.path.join(self.export_dir, md_path), "w", encoding="utf-8") as f:
                f.write(md)
            md_files[str(i)] = md_path
        print(f"▶️ MD 保存耗时：{time.time() - t_md_start:.2f} 秒")

        # --- 测试图片保存耗时 ---
        t_img_start = time.time()
        for page_idx, images in self.images_content.items():
            images_content_paths[str(page_idx)] = []
            for j, img_array in enumerate(images):
                #img = Image.fromarray(img_array)
                img_path = f"images/page_{page_idx+1}_{j}.png"
                #img.save(os.path.join(self.export_dir, img_path),format="PNG", compress_level=1)
                images_content_paths[str(page_idx)].append(img_path)
        print(f"▶️ 图片保存耗时：{time.time() - t_img_start:.2f} 秒")

        # --- 测试 JSON 写入耗时 ---
        record = {
            "pdf_path": self.pdf_path,
            "current_page": self.current_page,
            "md_files": md_files,
            "images_content": images_content_paths,
            "image_descriptions": self.image_descriptions
        }
        t_json_start = time.time()
        with open(os.path.join(self.export_dir, "record.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        print(f"▶️ JSON 写入耗时：{time.time() - t_json_start:.2f} 秒")

    def init_record(self):
        if not self.export_dir:
            return

        # 1. 创建目录
        img_dir = os.path.join(self.export_dir, "images")
        os.makedirs(img_dir, exist_ok=True)

        md_files = {}
        images_content_paths = {}

        # --- 测试 MD 保存耗时 ---
        t_md_start = time.time()
        for i, md in enumerate(self.md_content):
            md_path = f"page_{i+1}.md"
            with open(os.path.join(self.export_dir, md_path), "w", encoding="utf-8") as f:
                f.write(md)
            md_files[str(i)] = md_path
        print(f"▶️ MD 保存耗时：{time.time() - t_md_start:.2f} 秒")

        # --- 测试图片保存耗时 ---
        t_img_start = time.time()
        for page_idx, images in self.images_content.items():
            images_content_paths[str(page_idx)] = []
            for j, img_array in enumerate(images):
                img = Image.fromarray(img_array)
                img_path = f"images/page_{page_idx+1}_{j}.png"
                img.save(os.path.join(self.export_dir, img_path),format="PNG", compress_level=1)
                images_content_paths[str(page_idx)].append(img_path)
        print(f"▶️ 图片保存耗时：{time.time() - t_img_start:.2f} 秒")

        # --- 测试 JSON 写入耗时 ---
        record = {
            "pdf_path": self.pdf_path,
            "current_page": self.current_page,
            "md_files": md_files,
            "images_content": images_content_paths,
            "image_descriptions": self.image_descriptions
        }
        t_json_start = time.time()
        with open(os.path.join(self.export_dir, "record.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        print(f"▶️ JSON 写入耗时：{time.time() - t_json_start:.2f} 秒")


    def reset_state(self):
        self.md_content = []
        self.current_page = 0
        self.zoom_factor = 1.0
        self.md_text.delete(1.0, tk.END)
        self.pdf_canvas.delete("all")
        self.images_content = {}
        self.image_descriptions = {}

    def update_ui_after_import(self):
        self.page_var.set(f"{self.current_page+1}/{self.total_pages}")
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED if self.total_pages <= 1 else tk.NORMAL)
        self.jump_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)

    def start_processing(self):
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        process_queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=extract_pdf,
            args=(self.pdf_path, return_dict, process_queue)
        )
        process.start()
        while process.is_alive():
            if not process_queue.empty():
                msg_type, data = process_queue.get()
                if msg_type == "progress":
                    self.communication_queue.put(("progress", data))
                elif msg_type == "done":
                    self.communication_queue.put(("done", return_dict.copy()))
                    return
                elif msg_type == "error":
                    self.communication_queue.put(("error", data))
                    return
        if not process_queue.empty():
            msg_type, data = process_queue.get()
            self.communication_queue.put((msg_type, data))

    def check_processing_queue(self):
        try:
            while True:
                msg_type, data = self.communication_queue.get_nowait()
                if msg_type == "progress":
                    self.progress_var.set(data)
                    self.status_var.set(f"处理中... {data}%")
                elif msg_type == "done":
                    self.text_map = data["text"]
                    self.images_map = data["images"]
                    self.legends_map= data["legends"]
                    self.md_content = [self.text_map[i] for i in sorted(self.text_map.keys())]
                    self.images_content = {
                        i: self.images_map[i]
                        for i in sorted(self.images_map.keys())
                    }
                    for i in sorted(self.images_map.keys()):
                        self.image_descriptions[i] = [f"{self.legends_map[i][j]}" for j in range(len(self.images_map[i]))]

                    self.init_record()
                    self.display_page(0)
                    self.progress_var.set(100)
                    self.status_var.set("处理完成!")
                    self.export_btn.config(state=tk.NORMAL)
                elif msg_type == "error":
                    messagebox.showerror("处理错误", data)
                    self.status_var.set("处理失败")
                    self.progress_var.set(0)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_processing_queue)

    def display_page(self, page_num):
        if not self.pdf_document or page_num >= self.total_pages:
            return
        self.current_page = page_num
        page = self.pdf_document.load_page(page_num)
        zoom_matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=zoom_matrix)
        try:
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.photo_image = ImageTk.PhotoImage(img)
        except Exception as e:
            messagebox.showerror("图像错误", f"无法加载图像: {str(e)}")
            return
        self.center_image_on_canvas(pix.width, pix.height)
        self.display_markdown_content()
        self.display_image()
        self.page_var.set(f"{page_num + 1}/{self.total_pages}")
        self.update_navigation_buttons()

    def center_image_on_canvas(self, img_width, img_height):
        canvas_width = self.pdf_canvas.winfo_width()
        canvas_height = self.pdf_canvas.winfo_height()
        x_pos = canvas_width // 2
        y_pos = canvas_height // 2

        # 复用canvas上的图片item
        if self.canvas_image_id is None:
            self.canvas_image_id = self.pdf_canvas.create_image(
                x_pos, y_pos, anchor=tk.CENTER, image=self.photo_image
            )
        else:
            self.pdf_canvas.coords(self.canvas_image_id, x_pos, y_pos)
            self.pdf_canvas.itemconfig(self.canvas_image_id, image=self.photo_image)

        self.pdf_canvas.config(scrollregion=(0, 0, img_width, img_height))

    def display_markdown_content(self):
        self.md_text.config(state=tk.NORMAL)
        self.md_text.delete(1.0, tk.END)
        if self.current_page < len(self.md_content):
            content = self.md_content[self.current_page]
            self.md_text.insert(tk.END, content)
        self.md_text.edit_reset()
        self.md_text.config(state=tk.NORMAL)

    def display_image(self):
        """将图像加载放入后台线程，加快主界面响应速度"""
        for widget in self.image_frame.winfo_children():
            widget.destroy()

        if self.current_page not in self.images_content:
            self.status_var.set(f"第 {self.current_page + 1} 页无图像")
            return

        images = self.images_content[self.current_page]
        descriptions = self.image_descriptions.get(self.current_page, [""] * len(images))

        if len(descriptions) < len(images):
            descriptions += [""] * (len(images) - len(descriptions))
        elif len(descriptions) > len(images):
            descriptions = descriptions[:len(images)]
        self.image_descriptions[self.current_page] = descriptions

        self.photo_image_refs = []
        self.image_desc_entries = []

        def load_images_in_thread():
            rendered_images = []
            for idx, img_array in enumerate(images):
                try:
                    img = Image.fromarray(img_array)
                    img_resized = img.resize((200, 200), resample=Image.Resampling.LANCZOS)
                    tk_img = ImageTk.PhotoImage(img_resized)
                    rendered_images.append((idx, tk_img))
                except Exception as e:
                    rendered_images.append((idx, None))
            self.root.after(0, lambda: self.render_images(rendered_images, descriptions))

        threading.Thread(target=load_images_in_thread, daemon=True).start()
        self.status_var.set("正在加载图像...")

    def render_images(self, rendered_images, descriptions):
        """在主线程中更新UI"""
        for idx, tk_img in rendered_images:
            row_frame = tk.Frame(self.image_frame, pady=5)
            row_frame.pack(fill="x", padx=10)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_columnconfigure(2, weight=1)
            row_frame.grid_rowconfigure(0, weight=1)

            desc_var = tk.StringVar(value=descriptions[idx])
            desc_entry = tk.Entry(row_frame, textvariable=desc_var)
            desc_entry.grid(row=0, column=1, sticky="nsew", padx=5)
            self.image_desc_entries.append(desc_var)

            if tk_img:
                img_label = tk.Label(row_frame, image=tk_img, width=200, height=200)
                img_label.grid(row=0, column=0, sticky="nsew", padx=5)
                self.photo_image_refs.append(tk_img)
            else:
                tk.Label(row_frame, text="加载失败", width=25, height=10).grid(row=0, column=0)

            btn = tk.Button(row_frame, text="删除", command=lambda i=idx: self.delete_image(i))
            btn.grid(row=0, column=2, sticky="nsew", padx=5)

        self.image_frame.update_idletasks()
        self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))
        self.status_var.set(f"第 {self.current_page + 1} 页，共 {len(rendered_images)} 张图")


    def delete_image(self, index):
        """从当前页中删除指定图像并删除文件"""
        if self.current_page in self.images_content and 0 <= index < len(self.images_content[self.current_page]):
            # 删除图片文件记录
            del self.images_content[self.current_page][index]
            del self.image_descriptions[self.current_page][index]
            self.save_to_record()
            self.display_image()

    def save_current_image_descriptions(self):
        if not hasattr(self, "image_desc_entries") or not self.image_desc_entries:
            print("⚠️ 当前页面图像尚未加载完毕，跳过描述保存")
            return
        if self.current_page in self.image_descriptions:
            self.image_descriptions[self.current_page] = [
                var.get() for var in self.image_desc_entries
            ]
            self.save_to_record()

    def save_markdown_content(self):
        if self.current_page < len(self.md_content):
            self.md_content[self.current_page] = self.md_text.get(1.0, tk.END).strip()
            self.save_to_record()

    def on_mousewheel(self, event):
        if self.pdf_document:
            delta = event.delta
            if event.num == 5 or event.delta < 0:
                scale = 0.9
            else:
                scale = 1.1
            self.zoom_factor *= scale
            self.zoom_factor = max(0.5, min(self.zoom_factor, 3.0))
            self.display_page(self.current_page)

    def update_navigation_buttons(self):
        self.prev_btn.config(
            state=tk.NORMAL if self.current_page > 0 else tk.DISABLED
        )
        self.next_btn.config(
            state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED
        )

    def prev_page(self):
        if self.current_page > 0:
            self.save_current_image_descriptions()
            self.save_markdown_content()
            self.display_page(self.current_page - 1)

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.save_current_image_descriptions()
            self.save_markdown_content()
            self.display_page(self.current_page + 1)

    def goto_page(self):
        try:
            page_num = int(self.goto_entry.get()) - 1
            if 0 <= page_num < self.total_pages:
                self.save_current_image_descriptions()
                self.save_markdown_content()
                self.display_page(page_num)
            else:
                messagebox.showwarning(
                    "无效的页码",
                    f"页码必须在1和{self.total_pages}之间"
                )
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的页码数字")

    def export(self):
        """导出：合并Markdown文本 + 保留图像 + 图像描述 JSON"""
        if not self.md_content:
            messagebox.showinfo("没有内容", "没有要导出的Markdown内容")
            return

        self.save_markdown_content()
        self.save_current_image_descriptions()

        # 选择导出目录（不是文件）
        export_root = filedialog.askdirectory(title="选择导出目录")
        if not export_root:
            return

        # 用导入 PDF 的文件名作为子目录名
        if not self.pdf_path:
            messagebox.showerror("导出错误", "无法获取PDF文件名")
            return
        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        export_folder = os.path.join(export_root, pdf_name)
        image_folder = os.path.join(export_folder, "images")
        os.makedirs(image_folder, exist_ok=True)

        try:
            description_map = {}
            fig_count = 1
            merged_md = ""
            # 合并Markdown并插入图片引用
            for page_idx, md in enumerate(self.md_content):
                merged_md += md.strip() + "\n\n"
                images = self.images_content.get(page_idx, [])
                descriptions = self.image_descriptions.get(page_idx, [])
                for i, img_array in enumerate(images):
                    filename = f"fig{fig_count:03d}.png"
                    desc = descriptions[i] if i < len(descriptions) else f"图 {fig_count}"
                    img = Image.fromarray(img_array)
                    img.save(os.path.join(image_folder, filename))
                    description_map[filename] = desc
                    fig_count += 1

            # 写 Markdown 文件
            md_path = os.path.join(export_folder, "export.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(merged_md.strip())

            # 写 JSON 文件
            json_path = os.path.join(export_folder, "image_descriptions.json")
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(description_map, jf, ensure_ascii=False, indent=2)

            messagebox.showinfo("导出成功", f"已导出到:\n{export_folder}\n图像数量: {fig_count-1}")
            self.status_var.set(f"导出成功: {os.path.basename(md_path)}")

        except Exception as e:
            messagebox.showerror("导出错误", f"无法保存文件:\n{str(e)}")

    def update_md_preview(self):
        """更新Markdown渲染预览"""
        try:
            raw_md = self.md_text.get(1.0, tk.END)
            html = markdown.markdown(raw_md)
            self.preview_html_label.set_html(html)
            self.status_var.set("Markdown渲染成功")
        except Exception as e:
            self.status_var.set(f"渲染失败: {str(e)}")


    def on_md_modified(self, event=None):
        """每当Markdown文本修改时自动刷新预览"""
        if self.md_text.edit_modified():  # 确保是用户输入引起的变化
            self.update_md_preview()
            self.md_text.edit_modified(False)  # 重置修改标志

