# -*- coding: utf-8 -*-
"""
下载 Olivetti Faces（AT&T）人脸数据集到项目 offline/data，并导出按人分文件夹的 PNG。

适用：
- CNN：直接使用 64x64 灰度图（形状可扩为 Nx64x64x1）
- 朴素贝叶斯：使用 bundle.data 形状 (400, 4096)，常配合 PCA 降维后用 GaussianNB

用法（在项目根目录，与 manage.py 同级）：
  python offline/scripts/download_face_dataset_olivetti.py

说明：https://scikit-learn.org/stable/datasets/real_world.html#olivetti-faces-dataset
"""
from __future__ import annotations

import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OFFLINE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_ROOT = os.path.join(OFFLINE_DIR, "data", "face_datasets")
SKLEARN_HOME = os.path.join(DATA_ROOT, "sklearn_cache")
EXPORT_DIR = os.path.join(DATA_ROOT, "olivetti_export")
INFO_FILE = os.path.join(DATA_ROOT, "olivetti_README.txt")


def main():
    try:
        from sklearn.datasets import fetch_olivetti_faces
    except ImportError:
        print("请先安装 scikit-learn: pip install scikit-learn")
        sys.exit(1)

    os.makedirs(DATA_ROOT, exist_ok=True)
    os.makedirs(SKLEARN_HOME, exist_ok=True)

    print("正在下载或加载 Olivetti Faces（已缓存则不再联网）...")
    bundle = fetch_olivetti_faces(
        data_home=SKLEARN_HOME,
        shuffle=True,
        random_state=42,
        download_if_missing=True,
    )
    X, y, images = bundle.data, bundle.target, bundle.images
    n_classes = len(set(y))
    print(
        f"  样本数={X.shape[0]}, 展平特征维={X.shape[1]}, "
        f"图像数组={images.shape}, 人数(类)={n_classes}"
    )

    try:
        from PIL import Image
    except ImportError:
        print("未安装 Pillow，跳过 PNG 导出。")
        _write_info(X.shape, images.shape, n_classes)
        return

    if os.path.isdir(EXPORT_DIR):
        shutil.rmtree(EXPORT_DIR)
    os.makedirs(EXPORT_DIR, exist_ok=True)

    per_person_index: dict[int, int] = {}
    for i in range(len(y)):
        pid = int(y[i])
        seq = per_person_index.get(pid, 0)
        per_person_index[pid] = seq + 1
        sub = os.path.join(EXPORT_DIR, f"person_{pid:02d}")
        os.makedirs(sub, exist_ok=True)
        arr = (images[i] * 255.0).clip(0, 255).astype("uint8")
        Image.fromarray(arr, mode="L").save(os.path.join(sub, f"{seq:02d}.png"))

    _write_info(X.shape, images.shape, n_classes)
    print(f"  sklearn 缓存目录: {SKLEARN_HOME}")
    print(f"  PNG 导出目录: {EXPORT_DIR}")
    print(f"  说明文件: {INFO_FILE}")


def _write_info(flat_shape, img_shape, n_classes):
    text = f"""Olivetti Faces（AT&T Cambridge）
- 约 400 张灰度人脸，40 人，每人 10 张，像素 64x64。
- sklearn 缓存: {SKLEARN_HOME}
- 按人导出的 PNG: {EXPORT_DIR}（person_XX/00.png ..）

Python 加载示例:
  from sklearn.datasets import fetch_olivetti_faces
  d = fetch_olivetti_faces(data_home={repr(SKLEARN_HOME)})
  X, y, imgs = d.data, d.target, d.images  # X 用于 NB+PCA；imgs 用于 CNN

扁平形状: {flat_shape}, 图像形状: {img_shape}, 类别数: {n_classes}
"""
    with open(INFO_FILE, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
