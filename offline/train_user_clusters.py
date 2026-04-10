# -*- coding: utf-8 -*-
"""
离线从数据库抽特征并生成 user_cluster.pkl。K-means 核心逻辑在 user_cluster_kmeans.py；
线上读取使用 user_cluster_kmeans.load_cluster_user_ids_for_user（由 recommend_by_forse 调用）。

特征说明（见 FEATURE_NAMES 与 build_feature_matrix）：
  - 问卷：sight_type / travel_way / sight_way、cost_min / cost_max
  - 行为：评分条数与均分、有效点赞/收藏/评论/预订次数

保存路径：user_cluster_kmeans.get_user_cluster_pkl_path()（项目根 user_cluster.pkl）。

运行（项目根目录）：
  python offline/train_user_clusters.py
"""
from __future__ import annotations

import os
import sys

# -----------------------------------------------------------------------------
# Django：项目根 = 本文件所在目录的上一级（含 manage.py、recommend_random_forest.py）
# -----------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travel_manager.settings")

import django

django.setup()

import numpy as np

from django.db.models import Avg, Count, Q

from travel.models import (
    User,
    QuestionnaireSight,
    RateSight,
    LikeSight,
    CollectSight,
    CommentSight,
    BookingSight,
)

from user_cluster_kmeans import (
    build_cluster_payload,
    get_user_cluster_pkl_path,
    save_cluster_payload,
    scale_fit_kmeans_labels,
)

# 特征列名（顺序与矩阵列一致，写入 pkl 便于论文/调试）
FEATURE_NAMES = [
    "q_sight_type",
    "q_travel_way",
    "q_sight_way",
    "q_cost_min",
    "q_cost_max",
    "rate_count",
    "rate_avg",
    "like_count",
    "collect_count",
    "comment_count",
    "booking_count",
]


def _safe_int_choice(val, default=0):
    """问卷 choice 字段多为 '0'..'3' 字符串。"""
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        try:
            return int(float(val))
        except (TypeError, ValueError):
            return default


def questionnaire_row(user) -> tuple[list[int], bool]:
    """
    返回 ([5 个问卷相关整数], has_questionnaire)。
    无问卷时用模型默认值等价特征，避免脚本崩溃；has_questionnaire=False 仅作统计打印。
    """
    try:
        qs = QuestionnaireSight.objects.get(user=user)
        return [
            _safe_int_choice(qs.sight_type, 0),
            _safe_int_choice(qs.travel_way, 0),
            _safe_int_choice(qs.sight_way, 0),
            int(qs.cost_min) if qs.cost_min is not None else 1,
            int(qs.cost_max) if qs.cost_max is not None else 10,
        ], True
    except QuestionnaireSight.DoesNotExist:
        return [0, 0, 0, 1, 10], False


def build_behavior_maps(user_ids: list[int]):
    """一次性聚合行为计数，避免对每个用户 N 次查询。"""
    uid_set = set(user_ids)

    rate_qs = (
        RateSight.objects.filter(user_id__in=uid_set)
        .values("user_id")
        .annotate(c=Count("id"), avg=Avg("score"))
    )
    rate_map = {
        r["user_id"]: (r["c"], float(r["avg"]) if r["avg"] is not None else 0.0)
        for r in rate_qs
    }

    def count_map(model, extra_q=None):
        q = model.objects.filter(user_id__in=uid_set)
        if extra_q is not None:
            q = q.filter(extra_q)
        rows = q.values("user_id").annotate(c=Count("id"))
        return {r["user_id"]: r["c"] for r in rows}

    like_map = count_map(LikeSight, Q(is_delete=False))
    collect_map = count_map(CollectSight, Q(is_delete=False))
    comment_map = count_map(CommentSight)
    booking_map = count_map(BookingSight)

    return rate_map, like_map, collect_map, comment_map, booking_map


def build_feature_matrix(users: list[User]):
    """
    为每个用户构造一行特征；无问卷用户不抛异常，问卷维用默认；
    无行为用户对应计数为 0，rate_avg 为 0。
    """
    user_ids = [u.id for u in users]
    rate_map, like_map, collect_map, comment_map, booking_map = build_behavior_maps(user_ids)

    X = []
    n_no_q = 0
    for u in users:
        q_part, has_q = questionnaire_row(u)
        if not has_q:
            n_no_q += 1

        rc, ra = rate_map.get(u.id, (0, 0.0))
        row = q_part + [
            float(rc),
            float(ra),
            float(like_map.get(u.id, 0)),
            float(collect_map.get(u.id, 0)),
            float(comment_map.get(u.id, 0)),
            float(booking_map.get(u.id, 0)),
        ]
        X.append(row)

    return np.asarray(X, dtype=np.float64), user_ids, n_no_q


def run():
    print("BASE_DIR:", BASE_DIR)
    out_path = get_user_cluster_pkl_path()
    print("OUTPUT_PATH:", out_path)

    users = list(User.objects.all().order_by("id"))
    n_users = len(users)
    if n_users == 0:
        print("数据库中无用户，不生成 pkl。")
        sys.exit(1)

    X, user_ids, n_no_q = build_feature_matrix(users)
    print(f"用户数: {n_users}，无问卷用户(已用默认问卷特征): {n_no_q}")

    labels, k_cfg = scale_fit_kmeans_labels(X)
    print(f"K-means 配置 n_clusters = {k_cfg}")

    payload = build_cluster_payload(user_ids, labels, FEATURE_NAMES)
    save_cluster_payload(payload)
    print(f"已写入: {out_path}")
    print("键: user_clusters, cluster_users, feature_names, n_clusters")
    print("各簇人数:", {c: len(v) for c, v in payload["cluster_users"].items()})


if __name__ == "__main__":
    run()
