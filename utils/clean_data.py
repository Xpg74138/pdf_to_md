import re

def clean_text(text):
    # 替换掉“〜”符号为“至”
    text = text.replace("〜", "至")
    
    # 移除文本中的图示引用（例如 图4-1）
    text = re.sub(r"(图\d+[-\d]*)", "", text)
    
    # 去除多余的空格、换行符
    text = re.sub(r"\s+", " ", text).strip()
    
    # 去除行间多余的空行
    text = re.sub(r"\n\s*\n", "\n", text)
    
    return text