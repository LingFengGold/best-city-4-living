"""把 data.json 嵌入 template.html，生成可发布的 index.html。"""
import os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl = open(os.path.join(root, "template.html"), encoding="utf-8").read()
data = open(os.path.join(root, "pipeline", "data.json"), encoding="utf-8").read()
open(os.path.join(root, "index.html"), "w", encoding="utf-8").write(tpl.replace("__DATA__", data))
