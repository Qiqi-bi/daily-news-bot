from translate import Translator

# 测试翻译功能
def test_translation():
    # 测试英文翻译
    english_text = "Hello, how are you today?"
    translator = Translator(to_lang="zh", from_lang="en")
    translated = translator.translate(english_text)
    print(f"原文: {english_text}")
    print(f"翻译: {translated}")
    
    # 测试中文（应该保持不变）
    chinese_text = "你好，今天过得怎么样？"
    if any('\u4e00' <= char <= '\u9fff' for char in chinese_text):
        print(f"中文文本保持不变: {chinese_text}")
    else:
        translated_chinese = translator.translate(chinese_text)
        print(f"中文翻译结果: {translated_chinese}")

if __name__ == "__main__":
    test_translation()