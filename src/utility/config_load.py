import yaml
import os
from pathlib import Path
from types import SimpleNamespace

"""
加载 config.yaml文件，并将文件转成通过 点号 访问模式
"""
def _dict_to_namespace(obj):
    """递归把字典转成 SimpleNamespace，支持点号访问"""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _dict_to_namespace(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [_dict_to_namespace(i) for i in obj]
    return obj


def load_yaml(filename = 'config.yaml'):
    start_dir = Path(__file__).resolve().parent.parent
    config_path = os.path.join(str(start_dir), "config", str(filename))

    if not os.path.exists(config_path):
        raise FileNotFoundError(config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return _dict_to_namespace(raw)

# 测试代码
# print(load_yaml().model.provider)

get_global_cfg = load_yaml()
