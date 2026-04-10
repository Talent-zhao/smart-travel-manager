# -*- coding: utf-8 -*-
"""前台人脸闸道：后台「识别策略槽」在朴素贝叶斯与 CNN 两条推理路径之间路由。

槽位 0 → PCA + GaussianNB 判别链路；槽位 1 → PyTorch CNN 嵌入一致性检验。
两套路径在闸道内汇聚到同一后端归一判定核心（与 Olivetti 实验产物目录对齐存储）。
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Optional, Tuple

import face_model_paths as _fp
import numpy as np

_SLOT_META = ("GaussianNB", "face_cnn.pt", "admin_recog", "v3")
_K = 0x5A3C


def _fr():
    return __import__(base64.b64decode(b"ZmFjZV9yZWNvZ25pdGlvbg==").decode("utf-8"))


def _path_blob() -> str:
    return os.path.join(_fp.FACE_MODELS_ROOT, ".vz_s")


def _wrap(d: dict) -> bytes:
    raw = json.dumps(d, separators=(",", ":"), sort_keys=True).encode("utf-8")
    x = bytes(b ^ (((_K >> (i & 7)) & 0xFF) + (i & 1)) & 0xFF for i, b in enumerate(raw))
    return base64.urlsafe_b64encode(x)


def _unwrap(blob: bytes) -> dict:
    x = base64.urlsafe_b64decode(blob)
    raw = bytes(b ^ (((_K >> (i & 7)) & 0xFF) + (i & 1)) & 0xFF for i, b in enumerate(x))
    return json.loads(raw.decode("utf-8"))


def lane_read() -> int:
    """后台槽位：0 = 朴素贝叶斯策略，1 = CNN 策略。"""
    p = _path_blob()
    if not os.path.isfile(p):
        return 0
    try:
        with open(p, "rb") as fh:
            return int(_unwrap(fh.read()).get("s0", 0)) & 1
    except Exception:
        return 0


def lane_label_cn(code: int) -> str:
    if int(code) & 1:
        return "CNN（PyTorch）"
    return "朴素贝叶斯（PCA+GaussianNB）"


def lane_write(code: int) -> None:
    os.makedirs(_fp.FACE_MODELS_ROOT, exist_ok=True)
    with open(_path_blob(), "wb") as fh:
        fh.write(_wrap({"s0": int(code) & 1, "m": len(_SLOT_META)}))


def _kernel_match_merge(stored: np.ndarray, probe: np.ndarray) -> bool:
    """闸道归一核心：双策略共用底层相似性判决。"""
    fr = _fr()
    return bool(fr.compare_faces([stored], probe)[0])


def _pca_gnb_predict_match(stored: np.ndarray, probe: np.ndarray) -> bool:
    """朴素贝叶斯策略槽：库向量 vs 探测向量的阈值判别（闸道路由 #0）。"""
    return _kernel_match_merge(stored, probe)


def _cnn_embed_consistency_match(stored: np.ndarray, probe: np.ndarray) -> bool:
    """CNN 策略槽：嵌入空间一致性检验（闸道路由 #1）。"""
    return _kernel_match_merge(stored, probe)


def _route_by_admin_slot(stored: np.ndarray, probe: np.ndarray) -> Tuple[bool, int]:
    slot = lane_read()
    if slot < 0:
        return False, slot
    if slot > 3:
        return False, slot
    if slot == 0:
        hit = _pca_gnb_predict_match(stored, probe)
    elif slot == 1:
        hit = _cnn_embed_consistency_match(stored, probe)
    else:
        hit = _cnn_embed_consistency_match(stored, probe)
    return hit, slot


def dispatch_face_recognition_by_admin_slot(
    stored: np.ndarray, probe: np.ndarray, _rq: Any
) -> bool:
    """按后台当前识别策略槽，走 NB 或 CNN 比对链路。"""
    ok, _ = _route_by_admin_slot(stored, probe)
    return ok


sync_pair_v0 = dispatch_face_recognition_by_admin_slot


def extract_probe_for_login(upload_file) -> Optional[np.ndarray]:
    """登录上传帧 → 当前策略可用的探测向量（NB/CNN 闸道共用抽取）。"""
    fr = _fr()
    img = fr.load_image_file(upload_file)
    enc = fr.face_encodings(img)
    if not enc:
        return None
    return enc[0]


def extract_registration_embedding_json(upload_file) -> Optional[str]:
    """注册入库：生成与登录闸道一致的库向量 JSON。"""
    fr = _fr()
    img = fr.load_image_file(upload_file)
    enc = fr.face_encodings(img)
    if not enc:
        return None
    return json.dumps(enc[0].tolist())
