# -*- coding: utf-8 -*-
"""人脸实验：数据集缓存与模型输出目录（与 manage.py 同级，供训练脚本共用）。"""
import os

# 本文件与 manage.py 同目录
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_OFFLINE_DIR = os.path.join(_PROJECT_ROOT, "offline")

DATA_ROOT = os.path.join(_OFFLINE_DIR, "data", "face_datasets")
SKLEARN_CACHE = os.path.join(DATA_ROOT, "sklearn_cache")

FACE_MODELS_ROOT = os.path.join(_OFFLINE_DIR, "data", "face_models")
CNN_MODEL_DIR = os.path.join(FACE_MODELS_ROOT, "cnn")
NAIVE_BAYES_MODEL_DIR = os.path.join(FACE_MODELS_ROOT, "朴素贝叶斯")
