import os
import json

def check_songci():
    base_dir = "宋词"
    excludes = ["authors.song.json", "ci.db", "main.py", "README.md", "UpdateCi.py"]
    tag = "paragraphs"
    
    print("开始检查宋词文件...")
    
    for filename in os.listdir(base_dir):
        if filename in excludes:
            continue
            
        filepath = os.path.join(base_dir, filename)
        if not os.path.isfile(filepath):
            continue
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for i, poem in enumerate(data):
                if tag not in poem:
                    print(f"文件 {filename} 中的第 {i} 条数据缺少 '{tag}' 字段")
                    print(f"数据内容: {poem}")
                    # 只打印第一个错误
                    return
        except Exception as e:
            print(f"读取文件 {filename} 出错: {e}")

if __name__ == "__main__":
    check_songci()
