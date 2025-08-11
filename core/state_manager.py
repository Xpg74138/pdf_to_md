# core/state_manager.py
import json
import os
import time
import numpy as np
from PIL import Image

class StateManager:
    def __init__(self):
        self.pdf_path = None
        self.current_page = 0
        self.total_pages = 0
        self.md_content = []
        self.image_descriptions = {}
        self.images_content = {}
        self.export_dir = None

    def save_to_record(self):
        if not self.export_dir:
            return
        img_dir = os.path.join(self.export_dir, "images")
        os.makedirs(img_dir, exist_ok=True)

        md_files = {}
        images_content_paths = {}

        for i, md in enumerate(self.md_content):
            md_path = f"page_{i+1}.md"
            with open(os.path.join(self.export_dir, md_path), "w", encoding="utf-8") as f:
                f.write(md)
            md_files[str(i)] = md_path

        for page_idx, images in self.images_content.items():
            images_content_paths[str(page_idx)] = []
            for j, img_array in enumerate(images):
                img_path = f"images/page_{page_idx+1}_{j}.png"
                images_content_paths[str(page_idx)].append(img_path)

        record = {
            "pdf_path": self.pdf_path,
            "current_page": self.current_page,
            "md_files": md_files,
            "images_content": images_content_paths,
            "image_descriptions": self.image_descriptions
        }

        with open(os.path.join(self.export_dir, "record.json"), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

    def restore_from_record(self, record_path):
        with open(record_path, "r", encoding="utf-8") as f:
            record = json.load(f)

        self.export_dir = os.path.dirname(record_path)
        self.pdf_path = record["pdf_path"]
        self.current_page = record.get("current_page", 0)
        self.md_content = []
        self.image_descriptions = {}
        self.images_content = {}

        for i, md_path in record["md_files"].items():
            with open(os.path.join(self.export_dir, md_path), "r", encoding="utf-8") as f:
                self.md_content.append(f.read())

        for i, img_list in record["images_content"].items():
            self.images_content[int(i)] = []
            for img_path in img_list:
                img = Image.open(os.path.join(self.export_dir, img_path))
                self.images_content[int(i)].append(np.array(img))

        for i, desc_list in record["image_descriptions"].items():
            self.image_descriptions[int(i)] = desc_list

    def reset_state(self):
        self.pdf_path = None
        self.current_page = 0
        self.total_pages = 0
        self.md_content = []
        self.image_descriptions = {}
        self.images_content = {}
        self.export_dir = None
