# -*- coding: utf-8 -*-
"""
用户 K-means 分群统一管理模块（与 user_cluster.pkl 约定一致）。

职责：
- 默认 pkl 路径（与项目根下 recommend_random_forest.py 同级目录的 user_cluster.pkl）
- 离线：特征矩阵标准化 + sklearn.cluster.KMeans 拟合与标签
- 在线：从 pkl 解析当前用户所在簇的用户 id 列表

训练脚本、recommend_random_forest 等只需 import 本模块，避免算法散落多处。
"""
from __future__ import annotations

import os
from typing import Optional
from collections import defaultdict

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def get_user_cluster_pkl_path() -> str:
    """user_cluster.pkl 默认路径（本文件所在项目根目录）。"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_cluster.pkl")


def to_int_id(val):
    """统一将 pkl / numpy 标量转为 int，解析失败返回 None。"""
    if val is None:
        return None
    if hasattr(val, "item"):
        try:
            val = val.item()
        except Exception:
            pass
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def choose_n_clusters(n_samples: int) -> int:
    """
    根据样本量自动选 K，避免 K 过大或超过样本数；上限 8，小样本保守。
    """
    if n_samples <= 0:
        return 0
    if n_samples == 1:
        return 1
    if n_samples == 2:
        return 2
    if n_samples <= 4:
        return min(2, n_samples - 1)
    if n_samples <= 10:
        return min(3, n_samples - 1)
    if n_samples <= 30:
        return min(5, n_samples - 1)
    k = int(round(np.sqrt(n_samples)))
    k = max(3, min(8, k))
    return min(k, n_samples - 1)


def scale_fit_kmeans_labels(X: np.ndarray):
    """
    对特征矩阵做 StandardScaler + KMeans。

    :param X: shape (n_samples, n_features)
    :return: (labels, k_config) — labels 为每样本簇编号；k_config 为选用的 n_clusters 参数（1 表示未跑 KMeans）
    """
    X = np.asarray(X, dtype=np.float64)
    n_samples = X.shape[0]
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    k = choose_n_clusters(n_samples)
    if k <= 1:
        return np.zeros(n_samples, dtype=int), 1
    km = KMeans(
        n_clusters=k,
        n_init=10,
        random_state=42,
        max_iter=300,
    )
    labels = km.fit_predict(Xs)
    return labels.astype(int), int(k)


def build_cluster_payload(user_ids: list, labels: np.ndarray, feature_names: list) -> dict:
    """
    由用户 id 与聚类标签构造写入 pkl 的标准 dict。
    """
    user_clusters: dict[int, int] = {}
    cluster_users: dict[int, list] = defaultdict(list)
    for i, uid in enumerate(user_ids):
        lab = int(labels[i])
        uid = int(uid)
        user_clusters[uid] = lab
        cluster_users[lab].append(uid)
    cluster_users = {int(c): sorted(v) for c, v in sorted(cluster_users.items())}
    return {
        "user_clusters": user_clusters,
        "cluster_users": cluster_users,
        "feature_names": list(feature_names),
        "n_clusters": int(len(cluster_users)),
    }


def load_cluster_user_ids_for_user(user_id, pkl_path: Optional[str] = None):
    """
    从 user_cluster.pkl 解析与 user_id 同一簇的全部用户 id 列表。

    :param pkl_path: 默认 None 时使用 get_user_cluster_pkl_path()
    :return: list[int] 或 None（文件缺失、解析失败、用户未命中）

    兼容格式：cluster_users / user_ids+labels / user_clusters / 扁平 user->cluster
    """
    uid = to_int_id(user_id)
    if uid is None:
        return None
    path = pkl_path or get_user_cluster_pkl_path()
    if not os.path.exists(path):
        return None
    try:
        payload = joblib.load(path)
    except Exception as e:
        print(f"user_cluster.pkl 读取失败，降级热门推荐: {e}")
        return None
    if payload is None:
        return None

    if isinstance(payload, dict) and "user_ids" in payload and "labels" in payload:
        try:
            raw_uids = payload["user_ids"]
            labels = payload["labels"]
            uids = [to_int_id(u) for u in raw_uids]
            idx = None
            for i, u in enumerate(uids):
                if u == uid and i < len(labels):
                    idx = i
                    break
            if idx is None:
                return None
            out = []
            for i, u in enumerate(uids):
                if u is None or i >= len(labels):
                    continue
                li = labels[i]
                if hasattr(li, "item"):
                    try:
                        li = li.item()
                    except Exception:
                        pass
                lj = labels[idx]
                if hasattr(lj, "item"):
                    try:
                        lj = lj.item()
                    except Exception:
                        pass
                if li == lj:
                    out.append(u)
            return out if out else None
        except Exception as e:
            print(f"解析 user_ids/labels 簇格式失败: {e}")
            return None

    if not isinstance(payload, dict):
        return None

    if "cluster_users" in payload:
        try:
            cu = payload["cluster_users"]
            for _cid, members in cu.items():
                mem = []
                for m in members:
                    mi = to_int_id(m)
                    if mi is not None:
                        mem.append(mi)
                if uid in mem:
                    return mem
        except Exception as e:
            print(f"解析 cluster_users 失败: {e}")
        return None

    if "user_clusters" in payload:
        uc = payload["user_clusters"]
        try:
            cid = None
            for k, v in uc.items():
                if to_int_id(k) == uid:
                    cid = v
                    if hasattr(cid, "item"):
                        try:
                            cid = cid.item()
                        except Exception:
                            pass
                    break
            if cid is None:
                return None
            members = []
            for k, v in uc.items():
                ki = to_int_id(k)
                if ki is None:
                    continue
                vv = v
                if hasattr(vv, "item"):
                    try:
                        vv = vv.item()
                    except Exception:
                        pass
                if vv == cid:
                    members.append(ki)
            return members if members else None
        except Exception as e:
            print(f"解析 user_clusters 失败: {e}")
            return None

    reserved = frozenset({
        "user_clusters", "cluster_users", "user_ids", "labels",
        "model", "kmeans", "scaler", "n_clusters", "feature_names",
    })
    mapping = {}
    for k, v in payload.items():
        if k in reserved:
            continue
        ki = to_int_id(k)
        if ki is None:
            continue
        if isinstance(v, (list, tuple, dict, set)):
            continue
        vv = v
        if hasattr(vv, "item"):
            try:
                vv = vv.item()
            except Exception:
                pass
        vi = to_int_id(vv)
        if vi is None:
            continue
        mapping[ki] = vi
    if uid not in mapping:
        return None
    cid = mapping[uid]
    return [u for u, c in mapping.items() if c == cid]


def save_cluster_payload(payload: dict, pkl_path: Optional[str] = None) -> str:
    """写入 pkl；路径默认 get_user_cluster_pkl_path()。返回实际写入路径。"""
    path = pkl_path or get_user_cluster_pkl_path()
    joblib.dump(payload, path)
    return path
