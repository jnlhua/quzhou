# 单独跑这个脚本下载模型，下载一次永久缓存
from modelscope import snapshot_download

# Embedding 模型
snapshot_download('BAAI/bge-m3', cache_dir='./models')

# 重排序模型
snapshot_download('BAAI/bge-reranker-base', cache_dir='./models')