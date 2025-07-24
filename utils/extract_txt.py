import base64
import requests
import io
from PIL import Image

# 百度 API 密钥
API_KEY = ""
SECRET_KEY = ""

# 获取 access_token
def get_access_token():
    url = f"https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": SECRET_KEY
    }
    response = requests.post(url, data=params)
    return response.json().get("access_token", "")

access_token = get_access_token()

def baidu_ocr_image(image):
    """对PIL图像进行百度OCR识别"""
    if image.shape[2] == 4:  # RGBA
        img_pil = Image.fromarray(image, mode="RGBA")
    else:  # RGB
        img_pil = Image.fromarray(image, mode="RGB")
    buffered = io.BytesIO()
    img_pil.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general?access_token={access_token}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"image": img_base64}
    resp = requests.post(url, headers=headers, data=data)
    words = [item["words"] for item in resp.json().get("words_result", [])]
    return "\n".join(words)