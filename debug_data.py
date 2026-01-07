import os
import sys
import json

# 将当前目录添加到路径中
sys.path.append(os.getcwd())

from loader.data_loader import PlainDataLoader

def check_data_types():
    loader = PlainDataLoader()
    
    print("正在检查各数据集的数据类型...")
    
    for key, config in loader.datasets.items():
        try:
            # 这里的 key 类似于 "tang-shi"
            data = loader.body_extractor(key)
            if not data:
                print(f"[{key}] 数据为空")
                continue
                
            sample = data[0]
            print(f"[{key}] 数据类型: {type(sample)}")
            
            if isinstance(sample, str):
                print(f"  -> 样本: {sample[:50]}...")
            elif isinstance(sample, dict):
                print(f"  -> 键: {list(sample.keys())}")
            
        except Exception as e:
            print(f"[{key}] 读取出错: {e}")

if __name__ == "__main__":
    check_data_types()
