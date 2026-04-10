# Travel Manager（个人学习 / 记录）

> 本仓库仅用于**个人学习、练习与过程记录**，不承诺稳定性与生产可用性。

## 项目简介

基于 **Django** 的旅游管理相关 Web 项目，包含景点、酒店、用户等业务的模型与页面；并尝试接入 **人脸识别 / 证件识别** 等能力（如训练脚本、核验流程相关代码），用于理解「Web 后端 + 视觉算法」如何组合在一个应用里。

## 技术栈（当前仓库可见部分）

| 类别 | 说明 |
| --- | --- |
| 后端框架 | Django 3.2 |
| 后台 | xadmin、django-crispy-forms 等 |
| 数据库 | MySQL（`settings.py` 中配置，本地需自行准备库与账号） |
| 视觉 / 机器学习 | OpenCV、`face-recognition`、PyTorch、scikit-learn 等（见 `requirements.txt`） |
| 其他 | Pillow、import-export、爬虫相关脚本等 |

## 目录结构（简要）

```
travel_manager/
├── manage.py
├── requirements.txt
├── travel_manager/          # 项目配置（settings、urls 等）
├── travel/                  # 主应用：模型、视图、人脸/证件相关脚本
│   ├── face_algo_train.py   # 人脸算法训练相关
│   ├── face_verify_lane.py  # 核验流程相关
│   ├── id_card_recognition.py
│   └── spiders/             # 数据采集脚本
└── template/                # 模板（若存在）
```

具体以本机文件为准；迁移到别的机器时请自行核对路径与依赖。

## 本地运行（备忘）

1. 创建并激活 Python 虚拟环境（建议）。
2. 安装依赖：`pip install -r requirements.txt`  
   - Windows 下若 `mysqlclient` 安装失败，可查阅官方文档或改用已兼容的安装方式（学习阶段可先在本地调好数据库驱动）。
3. 在 MySQL 中创建数据库（名称需与 `settings.py` 中一致或自行修改配置）。
4. 迁移：`python manage.py migrate`
5. 启动：`python manage.py runserver`

**安全提示：** 若将来将代码推送到公开仓库，请勿提交数据库密码、`SECRET_KEY`、`.env` 等敏感信息；推送前请检查 `.gitignore`。

## 学习记录（可自行维护）

在下面追加日期与笔记即可，例如：

- **YYYY-MM-DD**：解决了什么问题 / 读了哪段代码 / 下一步想试什么

---

## 许可与声明

学习笔记性质项目；代码与文档仅供参考，使用后果自负。
