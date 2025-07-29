import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import multiprocessing
from utils.clean_data import clean_text
from utils.extract_txt import baidu_ocr_image
from utils.extract_imgs import extract_image

def process_page(args):
    i, page_bytes, page_text, dpi = args
    img = np.frombuffer(page_bytes[0], dtype=np.uint8).reshape(page_bytes[1])

    if page_text:
        text = clean_text(page_text)
        images,legends = extract_image(img, "output", i)
    else:
        text = clean_text(baidu_ocr_image(img))
        images,legends = extract_image(img, "output", i)

    return i, text, images,legends

def extract_pdf(path, return_dict, queue, dpi=300):
    doc = fitz.open(path)
    total_pages = len(doc)

    # 准备任务参数
    tasks = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        pix = page.get_pixmap(dpi=dpi)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8)
        shape = (pix.height, pix.width, pix.n)
        tasks.append((i, (img_array.tobytes(), shape), text, dpi))

    text_map = {}
    images_map = {}
    legends_map = {}

    # 使用多进程池处理每一页
    with multiprocessing.Pool(processes=min(8, multiprocessing.cpu_count())) as pool:
        for j, (i, text, images,legends) in enumerate(pool.imap_unordered(process_page, tasks)):
            text_map[i] = text
            if images:
                images_map[i] = images
                legends_map[i] = legends
            queue.put(("progress", int((j + 1) / total_pages * 100)))

    return_dict["text"] = text_map
    return_dict["images"] = images_map
    return_dict["legends"] = legends_map
    queue.put(("done", True))
