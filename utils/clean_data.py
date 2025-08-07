import re

def clean_text(text):
    # 替换 “〜” 为 “至”
    text = text.replace("〜", "至")

    # 去除杂项符号
    text = re.sub(r"[■»>●◆※▪•★◆◇▶▲▼■]", "", text)

    # 去除控制字符
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    lines = text.splitlines()
    # 去除每行末尾的 所有空白字符，包括制表符、全角空格等
    stripped_lines = [re.sub(r"[ \t\u3000]+$", "", line) for line in lines]
    paragraph = " ".join(stripped_lines)


    # ✅ 删除各种“图x-x”引用（含括号/空格/图内文字）
    paragraph = re.sub(r"[（(【\[]?\s*图\s*\d+(?:[-－–—]\d+)*\s*[）)】\]]?", "", paragraph)
    # 删除“（图xxx内容）”或“(图xxx)”等括号包围的整段图描述
    paragraph = re.sub(r"[（(]图.*?[）)]", "", paragraph)


    # 合并多余空格
    paragraph = re.sub(r"[ \t]+", " ", paragraph)

    return paragraph.strip()
