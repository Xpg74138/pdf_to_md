import cv2
import os

def extract_image(img, output_dir, index, min_area=90000):
    os.makedirs(output_dir, exist_ok=True)

    if img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    extracted_images = []
    count = 0
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = w / h

        if area > min_area and 0.5 < aspect_ratio < 2.0:
            figure = img[y:y+h, x:x+w]
            extracted_images.append(figure)  # ✅ 保存为 ndarray
            count += 1

    print(f"✅ 第 {index+1} 页提取 {count} 个矩形图像")
    return extracted_images  # ✅ 返回图像列表
