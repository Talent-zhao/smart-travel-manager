# 离线资源目录（非 Django 运行时最小集）

与 **线上 Web 服务**无直接耦合的文档、数据与独立脚本统一放在此处，便于维护与部署时区分。

| 路径 | 说明 |
|------|------|
| `docs/` | **开发文档.md**（维护/排错）、算法说明、运行说明、Tesseract/爬虫依赖、pip 镜像等 |
| `scripts/` | 命令行脚本：`import_all_data.py`（导入/检查 `travel.txt`）、`spider_hotel_qyer.py`（穷游酒店独立爬虫） |
| `data/` | 爬虫辅助数据：`citys.txt`（已爬城市标记）、`hotels_qyer_data.json`（酒店脚本输出，运行后生成） |

## 仍在项目根目录的线上相关文件

- `travel.txt` / `travel0.txt`：后台「导入数据」与爬虫写入的目标文件（`views.import_data`、`travel.spiders`）。
- `recommend_random_forest.py`、`recommend_sights.py`：视图层推荐逻辑直接 import。
- `randomforest.joblib`：随机森林模型（与 `recommend_random_forest.py` 同目录）。

## 常用命令（在项目根目录执行）

```bash
# 检查 travel.txt 结构（不写库）
python offline/scripts/import_all_data.py check

# 命令行全量导入 travel.txt
python offline/scripts/import_all_data.py

# 独立酒店爬虫（结果写入 offline/data/hotels_qyer_data.json）
python offline/scripts/spider_hotel_qyer.py
```

后台「一键爬取」仍使用应用内模块 `travel.spiders.travel_spider_data`，结果追加到根目录 `travel.txt`。
