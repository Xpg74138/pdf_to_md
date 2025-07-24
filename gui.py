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


# 强制设置控制台编码为UTF-8
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
        self.md_content = []  # 存储各页面Markdown内容
        self.photo_image = None  # 存储当前显示的PDF图像
        
        # 图像标签和描述存储
        self.image_descriptions = {}  # 存储图像描述性文字
        
        # 通信队列
        self.communication_queue = queue.Queue()
        
        # 创建主布局
        self.main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧PDF预览区
        self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=1)
        
        # PDF预览画布（带滚动条）
        self.canvas_frame = ttk.Frame(self.left_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 水平和垂直滚动条
        self.x_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.y_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        
        # PDF显示画布
        self.pdf_canvas = tk.Canvas(
            self.canvas_frame,
            bg='white',
            xscrollcommand=self.x_scrollbar.set,
            yscrollcommand=self.y_scrollbar.set
        )
        
        # 配置滚动条
        self.x_scrollbar.config(command=self.pdf_canvas.xview)
        self.y_scrollbar.config(command=self.pdf_canvas.yview)
        
        # 网格布局
        self.pdf_canvas.grid(row=0, column=0, sticky="nsew")
        self.y_scrollbar.grid(row=0, column=1, sticky="ns")
        self.x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 配置网格权重
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        
        # 绑定滚轮事件用于缩放
        self.pdf_canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # 右侧界面：切换显示Markdown或图像
        self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=1)
        
        # 使用ttk.Notebook来切换Markdown和图像显示
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Markdown编辑器标签页
        self.md_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.md_tab, text="Markdown")
        
        # Markdown编辑器
        self.md_text = tk.Text(
            self.md_tab, 
            wrap=tk.WORD, 
            font=("Consolas", 12),
            undo=True,
            maxundo=-1
        )
        self.md_scrollbar = ttk.Scrollbar(self.md_tab, command=self.md_text.yview)
        self.md_text.config(yscrollcommand=self.md_scrollbar.set)
        
        # Markdown编辑器布局
        self.md_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.md_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        
        # 图像显示标签页
        self.img_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.img_tab, text="图像")

        # 图像显示区域 + 滚动条
        self.image_canvas = tk.Canvas(self.img_tab, bg="white")
        self.image_canvas.pack(side="left", fill=tk.BOTH, expand=True)

        self.img_scrollbar = ttk.Scrollbar(self.img_tab, orient="vertical", command=self.image_canvas.yview)
        self.img_scrollbar.pack(side="right", fill="y")
        self.image_canvas.configure(yscrollcommand=self.img_scrollbar.set)


        # 图像内容 Frame 嵌入 Canvas
        self.image_frame = tk.Frame(self.image_canvas)
        self.canvas_window = self.image_canvas.create_window((0, 0), window=self.image_frame, anchor="nw")

        self.image_canvas.bind(
            "<Configure>",
            lambda e: self.image_canvas.itemconfig(self.canvas_window, width=e.width)
        )


        # 滚动区域刷新绑定
        self.image_frame.bind(
            "<Configure>",
            lambda e: self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
        )

        # 底部控制栏
        self.bottom_frame = ttk.Frame(root)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 操作按钮
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
        
        # 页面导航控制
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
        
        # 设置窗口网格布局
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 绑定队列检查
        self.check_processing_queue()
    
    
    def display_image(self):
        """显示当前页所有图像：缩略图 + 描述输入框 + 删除按钮"""
        # 清空 canvas 内容
        for widget in self.image_frame.winfo_children():
            widget.destroy()

        if self.current_page not in self.images_content:
            self.status_var.set(f"第 {self.current_page + 1} 页无图像")
            return

        images = self.images_content[self.current_page]


        self.photo_image_refs = []
        self.image_desc_entries = []

        for idx, img_array in enumerate(images):
            row_frame = tk.Frame(self.image_frame, pady=5)
            row_frame.pack(fill="x", padx=10)

            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=1)
            row_frame.grid_columnconfigure(2, weight=1)

            # ✅ 设置第0行垂直方向可拉伸，使控件高度一致
            row_frame.grid_rowconfigure(0, weight=1)

            # 图像缩略显示（统一拉伸为 200x200）
            img = Image.fromarray(img_array)
            img_resized = img.resize((200, 200), resample=Image.Resampling.LANCZOS)  # ✅ 拉伸
            tk_img = ImageTk.PhotoImage(img_resized)
            self.photo_image_refs.append(tk_img)

            img_label = tk.Label(row_frame, image=tk_img, width=200, height=200)  # ✅ 固定尺寸防止缩小
            img_label.grid(row=0, column=0, sticky="nsew", padx=5)


            # 可编辑描述输入框
            desc_var = tk.StringVar(value=self.image_descriptions[self.current_page][idx])
            desc_entry = tk.Entry(row_frame, textvariable=desc_var)
            desc_entry.grid(row=0, column=1, sticky="nsew", padx=5)
            self.image_desc_entries.append(desc_var)

            # 删除按钮
            btn = tk.Button(row_frame, text="删除", command=lambda i=idx: self.delete_image(i))
            btn.grid(row=0, column=2, sticky="nsew", padx=5)


        self.image_frame.update_idletasks()
        self.image_canvas.config(scrollregion=self.image_canvas.bbox("all"))

        self.status_var.set(f"第 {self.current_page + 1} 页，共 {len(images)} 张图")

    def delete_image(self, index):
        """从当前页中删除指定图像"""
        if self.current_page in self.images_content and 0 <= index < len(self.images_content[self.current_page]):
            del self.images_content[self.current_page][index]

            # 如果删除后该页图像为空，也一并清除
            if not self.images_content[self.current_page]:
                del self.images_content[self.current_page]

            self.display_image()  # 重新刷新视图

    def save_current_image_descriptions(self):
        """保存当前页面用户修改的图像描述"""
        if not hasattr(self, "image_desc_entries"):
            return
        if self.current_page in self.image_descriptions:
            self.image_descriptions[self.current_page] = [
                var.get() for var in self.image_desc_entries
            ]

    def on_mousewheel(self, event):
        """鼠标滚轮缩放处理"""
        if self.pdf_document:
            # 确定缩放方向（在Windows和Mac上delta值不同）
            delta = event.delta
            if event.num == 5 or event.delta < 0:  # 向下滚
                scale = 0.9
            else:  # 向上滚
                scale = 1.1
            
            # 应用缩放因子（有限制范围）
            self.zoom_factor *= scale
            self.zoom_factor = max(0.5, min(self.zoom_factor, 3.0))
            
            # 重新绘制当前页面
            self.display_page(self.current_page)
    
    def import_pdf(self):
        """导入PDF文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        
        # 重置状态
        self.reset_state()
        self.pdf_path = file_path
        
        try:
            # 打开PDF文档获取总页数
            self.pdf_document = fitz.open(self.pdf_path)
            self.total_pages = len(self.pdf_document)
            
            # 更新UI状态
            self.update_ui_after_import()
            self.status_var.set(f"正在处理: {os.path.basename(file_path)}...")
            
            # 启动后台处理任务
            threading.Thread(target=self.start_processing, daemon=True).start()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开PDF文件: {str(e)}")
            self.status_var.set("导入失败")
    
    def reset_state(self):
        """重置状态变量"""
        self.md_content = []
        self.current_page = 0
        self.zoom_factor = 1.0
        self.md_text.delete(1.0, tk.END)
        self.pdf_canvas.delete("all")
    
    def update_ui_after_import(self):
        """导入PDF后更新UI状态"""
        self.page_var.set(f"1/{self.total_pages}")
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED if self.total_pages <= 1 else tk.NORMAL)
        self.jump_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
    
    def start_processing(self):
        """启动后台处理任务"""
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        
        # 使用队列进行进程间通信
        process_queue = multiprocessing.Queue()
        
        # 启动处理进程
        process = multiprocessing.Process(
            target=extract_pdf,
            args=(self.pdf_path, return_dict, process_queue)
        )
        process.start()
        
        # 监听处理结果
        while process.is_alive():
            if not process_queue.empty():
                msg_type, data = process_queue.get()
                
                # 通过主线程安全队列传递更新
                if msg_type == "progress":
                    self.communication_queue.put(("progress", data))
                elif msg_type == "done":
                    self.communication_queue.put(("done", return_dict.copy()))
                    return
                elif msg_type == "error":
                    self.communication_queue.put(("error", data))
                    return
        
        # 如果进程结束但未收到完成信号
        if not process_queue.empty():
            msg_type, data = process_queue.get()
            self.communication_queue.put((msg_type, data))
    
    def check_processing_queue(self):
        """检查处理队列并更新UI"""
        try:
            while True:
                msg_type, data = self.communication_queue.get_nowait()
                
                if msg_type == "progress":
                    self.progress_var.set(data)
                    self.status_var.set(f"处理中... {data}%")
                    
                elif msg_type == "done":
                    # 保存提取的文本和图像信息
                    self.text_map = data["text"]
                    self.images_map = data["images"]
                    
                    # 创建按页码排序的Markdown内容列表
                    self.md_content = [self.text_map[i] for i in sorted(self.text_map.keys())]
                    self.images_content = {
                                                i: self.images_map[i]
                                                for i in sorted(self.images_map.keys())
                                            }
                    for i  in sorted(self.images_map.keys()):
                        self.image_descriptions[i] = [f"图 {i}-{j+1}" for j in range(len(self.images_map[i]))]
                    
                    # 显示第一页
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
            # 每100毫秒检查一次队列
            self.root.after(100, self.check_processing_queue)
    
    def display_page(self, page_num):
        """显示指定页码的PDF和Markdown内容"""
        if not self.pdf_document or page_num >= self.total_pages:
            return
            
        self.current_page = page_num
        
        # 清空画布
        self.pdf_canvas.delete("all")
        
        # 获取PDF页面
        page = self.pdf_document.load_page(page_num)
        
        # 使用缩放因子创建变换矩阵
        zoom_matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        
        # 渲染页面
        pix = page.get_pixmap(matrix=zoom_matrix)
        
        # 修复：使用PIL将图像数据转换为Tkinter兼容格式
        try:
            # 将pixmap转换为PIL图像
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 转换为Tkinter PhotoImage
            self.photo_image = ImageTk.PhotoImage(img)
        except Exception as e:
            messagebox.showerror("图像错误", f"无法加载图像: {str(e)}")
            return
        
        # 在画布上居中显示图像
        self.center_image_on_canvas(pix.width, pix.height)
        
        # 显示对应的Markdown内容
        self.display_markdown_content()

        self.display_image()  # 显示图像
        
        # 更新页码显示
        self.page_var.set(f"{page_num + 1}/{self.total_pages}")
        
        # 更新导航按钮状态
        self.update_navigation_buttons()

    
    def center_image_on_canvas(self, img_width, img_height):
        """将图像居中显示在画布上"""
        # 获取画布当前尺寸
        canvas_width = self.pdf_canvas.winfo_width()
        canvas_height = self.pdf_canvas.winfo_height()
        
        # 计算居中位置
        x_pos = (canvas_width - img_width) / 2 if canvas_width > img_width else 0
        y_pos = (canvas_height - img_height) / 2 if canvas_height > img_height else 0
        
        # 在画布上显示图像
        self.pdf_canvas.create_image(
            max(0, x_pos), 
            max(0, y_pos), 
            anchor=tk.NW, 
            image=self.photo_image
        )
        
        # 更新滚动区域
        self.pdf_canvas.config(scrollregion=(0, 0, img_width, img_height))
    
    def display_markdown_content(self):
        """在编辑器中显示当前页的Markdown内容"""
        self.md_text.config(state=tk.NORMAL)
        self.md_text.delete(1.0, tk.END)
        
        if self.current_page < len(self.md_content):
            content = self.md_content[self.current_page]
            self.md_text.insert(tk.END, content)
        
        self.md_text.config(state=tk.NORMAL)
    
    def update_navigation_buttons(self):
        """更新导航按钮状态"""
        self.prev_btn.config(
            state=tk.NORMAL if self.current_page > 0 else tk.DISABLED
        )
        self.next_btn.config(
            state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED
        )
    
    def prev_page(self):
        """转到上一页"""
        if self.current_page > 0:
            self.save_current_image_descriptions()
            self.save_markdown_content()  # 保存当前页面的编辑内容
            self.display_page(self.current_page - 1)
    
    def next_page(self):
        """转到下一页"""
        if self.current_page < self.total_pages - 1:
            self.save_current_image_descriptions()
            self.save_markdown_content()  # 保存当前页面的编辑内容
            self.display_page(self.current_page + 1)
    
    def goto_page(self):
        """跳转到指定页面"""
        try:
            page_num = int(self.goto_entry.get()) - 1
            if 0 <= page_num < self.total_pages:
                self.save_current_image_descriptions()
                self.save_markdown_content()  # 保存当前页面的编辑内容
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

            # 1. 合并所有 Markdown 文本内容
            merged_md = "\n\n".join(self.md_content).strip()

            # 2. 遍历图像并导出
            for page_idx, images in self.images_content.items():
                descriptions = self.image_descriptions.get(page_idx, [])

                for i, img_array in enumerate(images):
                    filename = f"fig{fig_count:03d}.png"
                    desc = descriptions[i] if i < len(descriptions) else f"图 {fig_count}"

                    img = Image.fromarray(img_array)
                    img.save(os.path.join(image_folder, filename))
                    description_map[filename] = desc

                    fig_count += 1

            # 3. 写 Markdown 文件
            md_path = os.path.join(export_folder, "export.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(merged_md)

            # 4. 写 JSON 文件
            json_path = os.path.join(export_folder, "image_descriptions.json")
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(description_map, jf, ensure_ascii=False, indent=2)

            messagebox.showinfo("导出成功", f"已导出到:\n{export_folder}\n图像数量: {fig_count-1}")
            self.status_var.set(f"导出成功: {os.path.basename(md_path)}")

        except Exception as e:
            messagebox.showerror("导出错误", f"无法保存文件:\n{str(e)}")




    def save_markdown_content(self):
        """保存当前页的Markdown编辑内容"""
        if self.current_page < len(self.md_content):
            # 更新当前页的内容
            self.md_content[self.current_page] = self.md_text.get(1.0, tk.END).strip()


