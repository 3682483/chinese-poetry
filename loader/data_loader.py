import json
import os


DATAS_CONFIG = "./loader/datas.json"


class PlainDataLoader():
    def __init__(self, config_path: str=DATAS_CONFIG) -> None:
        self._path = config_path
        with open(config_path, 'r', encoding='utf-8') as config:
            data = json.load(config)
            self.top_level_path:str = data["cp_path"]
            self.datasets:dict = data["datasets"]
            self.id_table = {
                v["id"]: k for (k, v) in self.datasets.items()
            }
    
    def body_extractor(self, target: str) -> list:
        if target not in self.datasets:
            print(f"{target} is not included in datas.json as a dataset")
            return None
        configs = self.datasets[target]
        tag = configs["tag"]
        body = []  # may get a bit huge... 
        full_path = os.path.join(self.top_level_path, configs["path"])
        
        def extract_from_file(filepath):
            local_body = []
            try:
                with open(filepath, mode='r', encoding='utf-8') as file:
                    data = json.load(file)
                    for poem in data:
                        if tag in poem:
                            local_body += poem[tag]
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
            return local_body

        if os.path.isfile(full_path):  # single file json
            return extract_from_file(full_path)
        
        # a dir, probably with a skip list
        subpaths = os.listdir(full_path)
        for filename in subpaths:
            if filename in configs.get("excludes", []):
                continue
            body += extract_from_file(os.path.join(full_path, filename))
        return body

    def get_poems(self, target: str) -> list:
        """获取完整的诗词对象列表，包含标题、作者等信息"""
        if target not in self.datasets:
            print(f"{target} is not included in datas.json as a dataset")
            return []
        configs = self.datasets[target]
        poems = []
        full_path = os.path.join(self.top_level_path, configs["path"])
        
        def load_file(filepath):
            local_poems = []
            try:
                with open(filepath, mode='r', encoding='utf-8') as file:
                    data = json.load(file)
                    # 确保是列表
                    if isinstance(data, list):
                        local_poems.extend(data)
                    elif isinstance(data, dict):
                        local_poems.append(data)
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
            return local_poems

        if os.path.isfile(full_path):
            return load_file(full_path)
        
        if not os.path.isdir(full_path):
            return []

        subpaths = os.listdir(full_path)
        for filename in subpaths:
            if filename in configs.get("excludes", []):
                continue
            poems.extend(load_file(os.path.join(full_path, filename)))
        return poems

    def extract_from_multiple(self, targets: list) -> list:
        results = []
        for target in targets:
            results += self.body_extractor(target)
        return results
    
    def extract_with_ids(self, ids: list) -> list:
        results = []
        for id in ids:
            results += self.body_extractor(
                self.id_table[id]
            )
        return results



if __name__ == "__main__":
    loader = PlainDataLoader()
    print(loader.id_table)
    print(
        loader.body_extractor("wudai-huajianji")[-1]
    )
    print(
        len(loader.extract_from_multiple(["wudai-huajianji", "wudai-nantang"]))
    )
    print(
        loader.extract_with_ids([0, 1, 2])
    )

