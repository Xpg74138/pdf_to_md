# core/exporter.py
import os
import json
from PIL import Image

class MarkdownExporter:
    def __init__(self, state, status_var=None):
        self.state = state
        self.status_var = status_var  # 可选：绑定状态栏字符串

    def export(self, export_root):
        if not self.state.md_content:
            raise ValueError("没有 Markdown 内容可导出")

        if not self.state.pdf_path:
            raise ValueError("PDF 文件路径缺失，无法确定导出子目录")

        pdf_name = os.path.splitext(os.path.basename(self.state.pdf_path))[0]
        export_folder = os.path.join(export_root, pdf_name)
        image_folder = os.path.join(export_folder, "images")
        os.makedirs(image_folder, exist_ok=True)

        description_map = {}
        fig_count = 1
        merged_md = ""

        for page_idx, md in enumerate(self.state.md_content):
            merged_md += md.strip() + "\n\n"
            images = self.state.images_content.get(page_idx, [])
            descriptions = self.state.image_descriptions.get(page_idx, [])
            for i, img_array in enumerate(images):
                filename = f"fig{fig_count:03d}.png"
                desc = descriptions[i] if i < len(descriptions) else f"图 {fig_count}"
                img = Image.fromarray(img_array)
                img.save(os.path.join(image_folder, filename))
                description_map[filename] = desc
                fig_count += 1

        # 保存 Markdown 文件
        md_path = os.path.join(export_folder, "export.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(merged_md.strip())

        # 保存图像描述 JSON
        json_path = os.path.join(export_folder, "image_descriptions.json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(description_map, jf, ensure_ascii=False, indent=2)

        if self.status_var:
            self.status_var.set(f"导出成功: {os.path.basename(md_path)}")

        return export_folder, fig_count - 1
