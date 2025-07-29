import cv2
import requests
import base64
import os
from utils.extract_txt import get_access_token

TOKEN = get_access_token()

def get_ocr_text(image_crop):
    # 将图像编码为 base64
    _, buffer = cv2.imencode('.jpg', image_crop)
    img_base64 = base64.b64encode(buffer).decode()

    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general?access_token={TOKEN}" 
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {"image": img_base64}

    response = requests.post(url, headers=headers, data=data)
    result = response.json()
    words = []
    if "words_result" in result:
        for w in result["words_result"]:
            words.append(w["words"])
    return "\n".join(words)


def extract_image(img, output_dir, index, min_area=90000):
    os.makedirs(output_dir, exist_ok=True)

    if img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    extracted_figures = []
    legends = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = w / h

        if area > min_area and 0.5 < aspect_ratio < 2.0:
            figure = img[y:y+h, x:x+w]
            extracted_figures.append(figure)

            # 尝试提取图形下方的图例（向下偏移一定高度）
            legend_height = min(200, img.shape[0] - (y+h))  # 避免越界
            if legend_height > 20:
                legend_crop = img[y+h:y+h+legend_height, x:x+w]
                legend_text = get_ocr_text(legend_crop)
                legends.append(legend_text)
            else:
                legends.append("")

    print(f"✅ 第 {index+1} 页提取 {len(extracted_figures)} 个图形及图例")
    return extracted_figures, legends
