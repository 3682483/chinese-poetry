import os
import json
import random

def show_random_poem():
    # 设定全唐诗的目录
    tang_dir = os.path.join("全唐诗")
    
    # 获取目录下所有的json文件
    files = [f for f in os.listdir(tang_dir) if f.startswith("poet.tang") and f.endswith(".json")]
    
    if not files:
        print("未找到全唐诗数据文件")
        return

    # 随机选择一个文件
    random_file = random.choice(files)
    file_path = os.path.join(tang_dir, random_file)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 随机选择一首诗
        if data:
            poem = random.choice(data)
            print("\n--- 随机一首唐诗 ---\n")
            print(f"标题: {poem.get('title', '无题')}")
            print(f"作者: {poem.get('author', '佚名')}")
            print("\n内容:")
            for line in poem.get('paragraphs', []):
                print(line)
            print("\n---------------------\n")
        else:
            print("文件中没有诗歌数据")
            
    except Exception as e:
        print(f"读取文件出错: {e}")

if __name__ == "__main__":
    show_random_poem()
