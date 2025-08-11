# gui/editor_panel.py
import tkinter as tk
from tkinter import ttk
from tkhtmlview import HTMLLabel
import markdown

class EditorPanel:
    def __init__(self, parent, status_var):
        self.state = None
        self.status_var = status_var

        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 编辑器标签页
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

        # 预览标签页
        self.preview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.preview_tab, text="预览")
        self.preview_html_label = HTMLLabel(self.preview_tab, html="", background="white", width=100)
        self.preview_html_label.pack(fill=tk.BOTH, expand=True)

    def update_state(self, state):
        self.state = state

    def display_markdown(self, page_index):
        self.md_text.config(state=tk.NORMAL)
        self.md_text.delete(1.0, tk.END)
        if page_index < len(self.state.md_content):
            self.md_text.insert(tk.END, self.state.md_content[page_index])
        self.md_text.edit_reset()
        self.md_text.config(state=tk.NORMAL)
        self.update_md_preview()

    def save_markdown(self, page_index):
        if page_index < len(self.state.md_content):
            self.state.md_content[page_index] = self.md_text.get(1.0, tk.END).strip()

    def update_md_preview(self):
        try:
            raw_md = self.md_text.get(1.0, tk.END)
            html = markdown.markdown(raw_md)
            self.preview_html_label.set_html(html)
            self.status_var.set("Markdown渲染成功")
        except Exception as e:
            self.status_var.set(f"渲染失败: {str(e)}")

    def on_md_modified(self, event=None):
        if self.md_text.edit_modified():
            self.update_md_preview()
            self.md_text.edit_modified(False)
