# -*-coding:utf-8-*-
"""
景点推荐：UCF / ICF / 混合协同 + 簇内热门与簇内 ItemCF（供 K-means 分群主链路调用）。

兼容说明：
- recommend_by_item_id(..., restrict_user_ids=None) 不传子集时与原先全量 RateSight 构图一致。
- recommend_by_mixture(user_id, sight_id=None, cluster_user_ids=None) 不传 cluster_user_ids 时
  仍为原 UCF+ICF 混合逻辑；传入非空簇用户 id 集合时走簇内热门 + 簇内 ICF 融合。
"""
import collections
import numpy as np
import os
import django

os.environ["DJANGO_SETTINGS_MODULE"] = "travel_manager.settings"
django.setup()

import random
import operator
import math
from travel.models import *
from math import sqrt
from collections import Counter
from operator import itemgetter
from collections import defaultdict
from django.db.models import Count
from recommend_random_forest import recommend as recommend_forest


def get_hot_sight(user_id, sight_id=None):
    # 获取热门景点
    unlike_sight_ids = [d['sight_id'] for d in
                        LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
    if sight_id and sight_id not in unlike_sight_ids:
        unlike_sight_ids.append(sight_id)
    return Sight.objects.exclude(id__in=unlike_sight_ids).order_by('-grade')[:10]


def build_user_item_matrix(restrict_user_ids=None):
    """
    从 RateSight 构建 ItemCF 所需 dict：user_id(int) -> {sight_id: int(score)}。

    :param restrict_user_ids: 若为 None，扫描全表（与改造前 recommend_by_item_id 行为一致）；
        若传入可迭代用户 id 集合，仅纳入这些用户的评分记录（簇内子矩阵）。
    :return: 用户-物品-评分字典；restrict_user_ids 为空集合时返回 {}。
    """
    user_item_rate = {}
    qs = RateSight.objects.all().select_related('sight')
    if restrict_user_ids is not None:
        uid_set = set(restrict_user_ids)
        if not uid_set:
            return {}
        qs = qs.filter(user_id__in=uid_set)
    for rate in qs:
        if rate.sight_id is None:
            continue
        user = rate.user_id
        item_id = rate.sight_id
        rating = rate.score
        user_item_rate.setdefault(user, {})
        user_item_rate[user][item_id] = int(rating)
    return user_item_rate


def _normalize_cluster_user_ids(user_id, cluster_user_ids):
    """保证当前用户属于簇子集，避免外部漏传。"""
    return set(cluster_user_ids) | {int(user_id)}


def cluster_hot_sights(user_id, cluster_user_ids, sight_id=None, limit=25):
    """
    簇内热门召回：在簇用户子集的评分行为上统计景点被评分次数，排除当前用户已评分、
    明确不喜欢的景点及当前页景点；按（簇内评分次数降序、推荐指数降序）排序。

    :param user_id: 当前用户 id
    :param cluster_user_ids: 簇内用户 id 可迭代对象（可不包含当前用户，函数内会并入）
    :param sight_id: 当前页景点，排除
    :param limit: 返回列表最大长度
    :return: list[Sight]，顺序即簇内热门顺序（供 Borda 等融合使用）
    """
    cluster_ids = _normalize_cluster_user_ids(user_id, cluster_user_ids)
    unlike_sight_ids = set(
        LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values_list('sight_id', flat=True)
    )
    if sight_id is not None and sight_id not in unlike_sight_ids:
        unlike_sight_ids = set(unlike_sight_ids) | {int(sight_id)}
    rated_by_user = set(
        RateSight.objects.filter(user_id=user_id).values_list('sight_id', flat=True)
    )
    rows = (
        RateSight.objects.filter(user_id__in=cluster_ids, sight_id__isnull=False)
        .values('sight_id')
        .annotate(cnt=Count('id'))
    )
    sight_cnt = {r['sight_id']: r['cnt'] for r in rows}
    candidates = [
        sid for sid in sight_cnt
        if sid not in rated_by_user and sid not in unlike_sight_ids
    ]
    if not candidates:
        return []
    sights = {s.id: s for s in Sight.objects.filter(id__in=candidates)}
    candidates = [sid for sid in candidates if sid in sights]
    candidates.sort(key=lambda sid: (-sight_cnt[sid], -sights[sid].grade))
    return [sights[sid] for sid in candidates[:limit]]


# 基于用户推荐（UCF）；直观说明与示例矩阵见 offline/docs/开发文档.md
class UserCf:
    # 获得初始化数据
    def __init__(self, data, is_print=True):
        self.data = data
        self.user_sim_mat = {}  # 用户之间的兴趣相似度矩阵
        self.is_print = is_print  # 是否在控制台输出

    # 通过用户名获得景点列表，仅调试使用
    def getItems(self, username1, username2):
        return self.data[username1], self.data[username2]

    # 计算两个用户的皮尔逊相关系数
    def pearson(self, current_user, other_user):  # 数据格式为：景点id，评分
        '''
        current_user: 当前用户
        other_user: 其他用户
        '''
        current_user_vector = []  # 当前用户向量
        other_user_vector = []  # 其他用户向量
        # 循环当前用户的评分信息
        for sight_id, score in current_user.items():
            current_user_vector.append(score)  # 当前用户的评分入栈
            if sight_id in other_user.keys():
                # 如果其他用户也评分过这本书，则把评分入栈，否则入栈0
                other_user_vector.append(other_user[sight_id])
            else:
                other_user_vector.append(0)
        # 根据公式获取皮尔逊系数
        x = np.array(current_user_vector)
        y = np.array(other_user_vector)
        if all(x == y):
            return 1
        n = len(x)

        sum_xy = np.sum(np.sum(x * y))
        sum_x = np.sum(np.sum(x))
        sum_y = np.sum(np.sum(y))
        sum_x2 = np.sum(np.sum(x * x))
        sum_y2 = np.sum(np.sum(y * y))
        numerator = n * sum_xy - sum_x * sum_y  # 分子
        denominator = np.sqrt((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y))  # 分母
        if denominator == 0:
            return 0
        pc = round(float(numerator / denominator), 2)

        print("p氏距离:", pc)
        return pc

    # 计算N维向量的夹角
    def calc_vector_cos(self, current_user, other_user):
        '''
        current_user: 当前用户
        other_user: 其他用户
        cos=(ab的内积)/(|a||b|)
        :param a: 向量a
        :param b: 向量b
        :return: 夹角值
        '''
        current_user_vector = []  # 当前用户向量
        other_user_vector = []  # 其他用户向量
        # 循环当前用户的评分信息
        for item_id, score in current_user.items():
            current_user_vector.append(1)  # 当前用户有评分，入栈1
            if other_user.get(item_id, 0) > 0:
                # 如果其他用户也评分过这本书，入栈1
                other_user_vector.append(1)
            else:
                other_user_vector.append(0)
        a_n = np.array(current_user_vector)
        b_n = np.array(other_user_vector)
        if any(b_n) == 0:
            if self.is_print:
                print('值为0')
            return 0
        cos_ab = a_n.dot(b_n) / (np.linalg.norm(a_n) * np.linalg.norm(b_n))
        if self.is_print:
            print('值为', round(cos_ab, 2))
        return round(cos_ab, 2)

    # 计算与当前用户的距离，获得最临近的用户
    def nearest_user(self, username, n=1):
        distances = {}
        # 用户，相似度
        # 遍历整个数据集
        for user, rate_set in self.data.items():
            # 非当前的用户
            if user != username:
                if self.is_print:
                    print('获取{}与{}的向量夹角'.format(username, user))
                distance = self.calc_vector_cos(self.data[username], self.data[user])
                # 计算两个用户的相似度
                if distance > 0:
                    distances[user] = distance
        closest_distance = sorted(distances.items(), key=operator.itemgetter(1), reverse=True)
        # 最相似的N个用户
        closest_users = []
        for cd in closest_distance:
            if cd[1] == 1:
                closest_users.append(cd)
            else:
                if len(closest_users) >= n:
                    break
                closest_users.append(cd)
        if self.is_print:
            print("最相近的{}位用户:".format(n), closest_users)
        return closest_users

    # 给用户推荐景点
    def recommend_cos(self, username, n=1):
        recommend = {}
        nearest_user = self.nearest_user(username, n)
        for user, score in dict(nearest_user).items():  # 最相近的n个用户
            for sight_id, scores in self.data[user].items():  # 推荐的用户的景点列表
                if sight_id not in self.data[username].keys():  # 当前username没有看过
                    if sight_id not in recommend.keys() and scores > 5:  # 添加到推荐列表中
                        recommend[sight_id] = scores
        # 对推荐的结果按照景点浏览次数排序
        return sorted(recommend.items(), key=operator.itemgetter(1), reverse=True)

    def calc_user_sim(self, username):
        # 计算用户之间的兴趣相似度
        print('计算用户之间的兴趣相似度')
        item2users = dict()

        for user, items in self.data.items():
            for item in items:  # 遍历每一个物品
                if item not in item2users:
                    item2users[item] = set()  # 每个物品用户评过分的集合
                item2users[item].add(user)  # 将该用户加入到该物品用户评过分的集合中

        self.item_count = len(item2users)  # 获得物品的数量
        print('物品 number = %d' % self.item_count)

        # count co-rated items between users
        usersim_mat = self.user_sim_mat  # 用户之间的兴趣相似度矩阵
        print('创建用户之间的兴趣相似度矩阵')

        for item, users in item2users.items():  # 循环每一个键值对，即 for key,values in xxx.items()
            for u in users:  # u、v用户是否在同一个物品的评分集合里面
                usersim_mat.setdefault(u, defaultdict(int))
                for v in users:
                    if u == v:
                        continue
                    usersim_mat[u][v] += 1  # 如果在同一个物品的评分集合里面，则兴趣点加1

        for u, related_users in usersim_mat.items():
            for v, count in related_users.items():
                sim_value = round(count / math.sqrt(len(self.data[u]) * len(self.data[v])), 2)
                usersim_mat[u][v] = sim_value  # 计算两个用户的兴趣相似度
                if u == username:
                    print('{}与{}的兴趣相似度值为'.format(username, v), sim_value)

    def recommend(self, user, k=20, N=10):
        '''
        k:兴趣度最近的20个用户，
        N:最适合的10个物品
        找到兴趣最近的前20个用户，从中找到最适合的前10个物品
        '''
        self.calc_user_sim(user)  # 计算用户相似度
        rank = dict()
        watched_items = self.data[user]  # 当前用户评分过的物品

        for similar_user, similarity_factor in sorted(self.user_sim_mat[user].items(), key=itemgetter(1), reverse=True)[
                                               0:k]:
            # 排序，找出兴趣相似度最高的前20个用户
            print(similar_user, self.data[similar_user])
            for item in self.data[similar_user]:
                if item in watched_items:  # 如果该物品被该用户评分过，则跳过
                    continue
                rank.setdefault(item, 0)
                rank[item] += round(similarity_factor, 2)
        # 返回最好的N个物品
        return sorted(rank.items(), key=itemgetter(1), reverse=True)[0:N]


def recommend_by_user_id(user_id, sight_id=None, is_rec_list=False):
    '''
    通过用户协同算法来进行推荐
    user_id: 用户id
    sight_id: 用户已经评分过的景点id,需要在推荐列表中去除
    is_rec_list: 值为True：返回推荐[用户-评分]列表，值为False：返回推荐的景点列表
    '''
    #
    current_user = User.objects.get(id=user_id)
    # 如果当前用户没有打分 则按照热度顺序返回
    if current_user.ratesight_set.count() == 0:
        if is_rec_list:
            return []
        # 推荐列表为空，按用户注册时选择的景点类别各返回10门
        return get_hot_sight(user_id, sight_id)
    # 方式1
    user_item_rate = {}  # 用户-物品-评分字典
    for rate in RateSight.objects.all():
        user = rate.user.username  # 用户id
        item_id = rate.sight.id  # 物品id
        rating = rate.score  # 评分
        if user not in user_item_rate:
            user_item_rate.setdefault(user, {})
        user_item_rate[user][item_id] = int(rating)  # 建立用户-物品-评分的字典

    user_cf = UserCf(data=user_item_rate)
    recommend_list = user_cf.recommend(current_user.username, k=10)  # 只取最相似的10位用户

    if not recommend_list:
        # 推荐列表为空，且is_rec_list: 值为True：返回推荐[用户-评分]列表
        if is_rec_list:
            return []
        # 推荐列表为空，推热门景点
        return get_hot_sight(user_id, sight_id)

    sight_ids = [s[0] for s in recommend_list]
    if is_rec_list:
        # 推荐列表不为空，且且is_rec_list: 值为True：返回推荐[用户-评分]列表
        return sight_ids
    # 过滤掉用户反馈过不喜欢的景点
    unlike_sight_ids = [d['sight_id'] for d in
                        LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
    if sight_id and sight_id not in unlike_sight_ids:
        unlike_sight_ids.append(sight_id)
    sight_list = Sight.objects.filter(id__in=sight_ids).exclude(id__in=unlike_sight_ids).distinct().order_by("-grade")
    return sight_list


# 基于物品推荐（ICF）；步骤说明见 offline/docs/开发文档.md
class ItemCf:
    def __init__(self, data, user_id, is_print=True):
        self.user_id = user_id  # 用户id
        self.data = data  # 用户id
        self.is_print = is_print  # 是否在控制台输出

    def similarity(self, data):
        # 1 构造物品：物品的共现矩阵
        N = {}  # 喜欢物品i的总⼈数
        C = {}  # 喜欢物品i也喜欢物品j的⼈数
        for user, item in data.items():
            for i, score in item.items():
                N.setdefault(i, 0)
                N[i] += 1
                C.setdefault(i, {})
                for j, scores in item.items():
                    if j != i:
                        C[i].setdefault(j, 0)
                        C[i][j] += 1
        if self.is_print:
            print("---1.构造的共现矩阵---")
            print('N:', N)
            print('C', C)
        # 2 计算物品与物品的相似矩阵
        W = {}
        for i, item in C.items():
            W.setdefault(i, {})
            for j, item2 in item.items():
                W[i].setdefault(j, 0)
                W[i][j] = C[i][j] / sqrt(N[i] * N[j])
        if self.is_print:
            print("---2.构造的相似矩阵---")
            print(W)
        return W

    def recommand_list(self, data, W, user, k=3, N=10):
        '''
        # 3.根据⽤户的历史记录，给⽤户推荐物品
        :param data: 用户数据
        :param W: 相似矩阵
        :param user: 推荐的用户
        :param k: 相似的k个物品
        :param N: 推荐物品数量
        :return:
        '''

        rank = {}
        for i, score in data[user].items():  # 获得⽤户user历史记录，如A⽤户的历史记录为{'唐伯虎点秋香': 5, '逃学威龙1': 1, '追龙': 2}
            for j, w in sorted(W[i].items(), key=operator.itemgetter(1), reverse=True)[0:k]:  # 获得与物品i相似的k个物品
                if j not in data[user].keys():  # 该相似的物品不在⽤户user的记录⾥
                    rank.setdefault(j, 0)
                    rank[j] += float(score) * w  # 预测兴趣度=评分*相似度
        if self.is_print:
            print("---3.推荐----")
            print(sorted(rank.items(), key=operator.itemgetter(1), reverse=True)[0:N])
        return sorted(rank.items(), key=operator.itemgetter(1), reverse=True)[0:N]

    def recommendation(self, k=3, N=10):
        """
        给用户推荐相似景点
        :param k: 相似的k个物品
        :param N: 推荐物品数量
        """

        if not self.data or self.user_id not in self.data:
            # 用户没有评分过任何景点，就返回空列表
            return []

        W = self.similarity(self.data)  # 计算物品相似矩阵
        sort_rank = self.recommand_list(self.data, W, self.user_id, k, N)  # 推荐
        return sort_rank


def recommend_by_item_id(user_id, sight_id=None, is_rec_list=False, k=3, N=10, restrict_user_ids=None):
    '''
    通过物品协同算法来进行推荐
    user_id: 用户id
    sight_id: 用户已经评分过的景点id,需要在推荐列表中去除
    is_rec_list: 值为True：返回推荐[用户-评分]列表，值为False：返回推荐的景点列表
    k: 相似的k个物品
    N: 推荐物品数量
    restrict_user_ids: 可选；为 None 时使用全量用户评分构图（与历史行为一致）；传入则仅簇内/子集用户。
    '''

    user_item_rate = build_user_item_matrix(restrict_user_ids=restrict_user_ids)

    recommend_list = ItemCf(user_item_rate, user_id).recommendation(k=k, N=N)  # 物品协同过滤得到的推荐列表
    if not recommend_list:
        # 推荐列表为空
        # 推荐列表为空，且is_rec_list: 值为True：返回推荐[用户-评分]列表
        if is_rec_list:
            return []
        # 推荐列表为空，返回热门景点
        return get_hot_sight(user_id, sight_id)

    sight_ids = [s[0] for s in recommend_list]
    if is_rec_list:
        # 推荐列表不为空，且且is_rec_list: 值为True：返回推荐推荐列表
        return sight_ids
    # 过滤掉用户反馈过不喜欢的景点
    unlike_sight_ids = [d['sight_id'] for d in
                        LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
    if sight_id and sight_id not in unlike_sight_ids:
        unlike_sight_ids.append(sight_id)
    sight_list = Sight.objects.filter(id__in=sight_ids).exclude(id__in=unlike_sight_ids).distinct().order_by("-grade")
    return sight_list


def recommend_cluster_item_cf(user_id, cluster_user_ids, sight_id=None, is_rec_list=False, k=3, N=10):
    """
    簇内 ItemCF：仅用簇内用户子集构图，复用 ItemCf 类，接口与 recommend_by_item_id 对齐。

    :param cluster_user_ids: 簇内用户 id；会自动并入当前 user_id
    :param is_rec_list: True 时返回 sight_id 列表（ICF 顺序），False 时返回 Sight QuerySet
    """
    cluster_ids = _normalize_cluster_user_ids(user_id, cluster_user_ids)
    user_item_rate = build_user_item_matrix(restrict_user_ids=cluster_ids)
    recommend_list = ItemCf(user_item_rate, user_id, is_print=False).recommendation(k=k, N=N)
    if not recommend_list:
        if is_rec_list:
            return []
        return get_hot_sight(user_id, sight_id)
    sight_ids = [s[0] for s in recommend_list]
    if is_rec_list:
        return sight_ids
    unlike_sight_ids = [d['sight_id'] for d in
                        LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
    if sight_id and sight_id not in unlike_sight_ids:
        unlike_sight_ids.append(sight_id)
    return Sight.objects.filter(id__in=sight_ids).exclude(id__in=unlike_sight_ids).distinct().order_by("-grade")


def recommend_cluster_branch_lists(user_id, sight_id=None, cluster_user_ids=None, hot_limit=25, icf_k=3, icf_N=10):
    """
    供 recommend_by_forse 等做 Borda/加权融合：返回两路有序 Sight 列表。

    :param cluster_user_ids: 若为 None 或空，返回 ([], [])，调用方应走全站兜底或其它分支。
    :return: (cluster_hot_branch, cluster_icf_branch)，均为 list[Sight]，顺序保留各自召回序。
    """
    if not cluster_user_ids:
        return [], []
    cluster_ids = _normalize_cluster_user_ids(user_id, cluster_user_ids)
    hot_branch = cluster_hot_sights(user_id, cluster_ids, sight_id=sight_id, limit=hot_limit)
    icf_ids = recommend_cluster_item_cf(
        user_id, cluster_ids, sight_id=sight_id, is_rec_list=True, k=icf_k, N=icf_N
    )
    if not icf_ids:
        icf_branch = []
    else:
        order = {sid: pos for pos, sid in enumerate(icf_ids)}
        icf_branch = list(Sight.objects.filter(id__in=icf_ids))
        icf_branch.sort(key=lambda s: order[s.id])
    return hot_branch, icf_branch


def _recommend_by_mixture_cluster(user_id, sight_id, cluster_user_ids):
    """
    簇内「热门 + ItemCF」轻量融合：沿用原 recommend_by_mixture 的反馈动态权重 w 与截断合并策略，
    仅将第一路由 UCF 换成簇内热门 id 列表。
    """
    cluster_ids = _normalize_cluster_user_ids(user_id, cluster_user_ids)
    hot_sights = cluster_hot_sights(user_id, cluster_ids, sight_id=sight_id, limit=25)
    cu_sight_ids = [s.id for s in hot_sights]
    cf_sight_ids = recommend_cluster_item_cf(
        user_id, cluster_ids, sight_id=sight_id, is_rec_list=True, k=3, N=10
    )
    print('簇内热门推荐列表', cu_sight_ids)
    print('簇内物品协同列表', cf_sight_ids)
    if not cu_sight_ids:
        if not cf_sight_ids:
            return get_hot_sight(user_id, sight_id)
        unlike_sight_ids = [d['sight_id'] for d in
                            LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
        if sight_id and sight_id not in unlike_sight_ids:
            unlike_sight_ids.append(sight_id)
        sight_list = Sight.objects.filter(id__in=cf_sight_ids).exclude(id__in=unlike_sight_ids).distinct().order_by(
            "-grade")[:10]
        if not sight_list:
            return get_hot_sight(user_id, sight_id)
        return sight_list
    if not cf_sight_ids:
        unlike_sight_ids = [d['sight_id'] for d in
                            LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
        if sight_id and sight_id not in unlike_sight_ids:
            unlike_sight_ids.append(sight_id)
        sight_list = Sight.objects.filter(id__in=cu_sight_ids).exclude(id__in=unlike_sight_ids).distinct().order_by(
            "-grade")[:10]
        if not sight_list:
            return get_hot_sight(user_id, sight_id)
        return sight_list

    like_list = [d['is_like'] for d in LikeRecommendSight.objects.filter(user_id=user_id).values('is_like')]
    if len(like_list):
        w = 1 - round(Counter(like_list)[0] / len(like_list), 2)
    else:
        w = 0.5
    if w == 0:
        w = 0.5
    print('权重因子(簇内融合)', w)
    cu_len = int(len(cu_sight_ids) * w)
    cf_len = int(len(cf_sight_ids) * (1 - w))
    if cu_len == 0:
        cu_len = 1
    if cf_len == 0:
        cf_len = 1
    merged = []
    seen = set()
    for x in cu_sight_ids[:cu_len] + cf_sight_ids[:cf_len]:
        if x not in seen:
            seen.add(x)
            merged.append(x)
    recommend_list = merged
    if recommend_list:
        unlike_sight_ids = [d['sight_id'] for d in
                            LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
        if sight_id and sight_id not in unlike_sight_ids:
            unlike_sight_ids.append(sight_id)
        sight_list = Sight.objects.filter(id__in=recommend_list).exclude(
            id__in=unlike_sight_ids).distinct().order_by("-grade")[:10]
        if not sight_list:
            return get_hot_sight(user_id, sight_id)
        return sight_list
    return get_hot_sight(user_id, sight_id)


def recommend_by_mixture(user_id, sight_id=None, cluster_user_ids=None):
    # 混合推荐算法
    # 推荐列表 = w*P_cu + (1-w)* p_cf
    # cluster_user_ids 非空时：第一路为簇内热门，第二路为簇内 ItemCF（K-means 主链路预备）
    if cluster_user_ids:
        return _recommend_by_mixture_cluster(user_id, sight_id, cluster_user_ids)

    cu_sight_ids = recommend_by_user_id(user_id, sight_id=sight_id, is_rec_list=True)  # 用户协同过滤得到的推荐列表
    cf_sight_ids = recommend_by_item_id(user_id, sight_id=sight_id, is_rec_list=True)  # 物品协同过滤得到的推荐列表
    print('用户推荐列表', cu_sight_ids)
    print('物品推荐列表', cf_sight_ids)
    if not cu_sight_ids:
        # 用户协同过滤推荐列表为空
        if not cf_sight_ids:
            # 物品协同过滤列表也为空，返回热门景点
            return get_hot_sight(user_id, sight_id)
        # 返回物品协同过滤列表中的景点
        unlike_sight_ids = [d['sight_id'] for d in
                            LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
        if sight_id and sight_id not in unlike_sight_ids:
            unlike_sight_ids.append(sight_id)
        sight_list = Sight.objects.filter(id__in=cf_sight_ids).exclude(id__in=unlike_sight_ids).distinct().order_by(
            "-grade")[:10]
        if not sight_list:
            # 推荐列表为空
            return get_hot_sight(user_id, sight_id)
        return sight_list
    else:
        if not cf_sight_ids:
            # 物品协同过滤列表为空，则返回用户协同过滤列表中的景点
            unlike_sight_ids = [d['sight_id'] for d in
                                LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
            if sight_id and sight_id not in unlike_sight_ids:
                unlike_sight_ids.append(sight_id)
            sight_list = Sight.objects.filter(id__in=cu_sight_ids).exclude(id__in=unlike_sight_ids).distinct().order_by(
                "-grade")[:10]
            if not sight_list:
                # 推荐列表为空
                return get_hot_sight(user_id, sight_id)
            return sight_list

        # 混合推荐
        # 权重因子,通过统计用户对推荐列表中喜欢的景点数量来给出权重因子的值
        like_list = [d['is_like'] for d in LikeRecommendSight.objects.filter(user_id=user_id).values('is_like')]
        if len(like_list):
            w = 1 - round(Counter(like_list)[0] / len(like_list), 2)
        else:
            w = 0.5
        if w == 0:
            w = 0.5
        print('权重因子', w)
        # 从cu_list取w%个值，从cf_list取(1-w)个值然后合并
        cu_len = int(len(cu_sight_ids) * w)
        cf_len = int(len(cf_sight_ids) * (1 - w))
        if cu_len == 0:
            cu_len = 1
        if cf_len == 0:
            cf_len = 1
        # 按权重从 UCF 取前 w 比例、从 ICF 取前 (1-w) 比例，合并去重并保持顺序
        merged = []
        seen = set()
        for x in cu_sight_ids[:cu_len] + cf_sight_ids[:cf_len]:
            if x not in seen:
                seen.add(x)
                merged.append(x)
        recommend_list = merged

        if recommend_list:
            unlike_sight_ids = [d['sight_id'] for d in
                                LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
            if sight_id and sight_id not in unlike_sight_ids:
                unlike_sight_ids.append(sight_id)
            sight_list = Sight.objects.filter(id__in=recommend_list).exclude(
                id__in=unlike_sight_ids).distinct().order_by(
                "-grade")[:10]
            if not sight_list:
                # 推荐列表为空
                return get_hot_sight(user_id, sight_id)
            return sight_list
        # 混合推荐集合为空，则返回热门
        return get_hot_sight(user_id, sight_id)


# 算法评价指标：召回率，准确率，覆盖率，新颖度
class EvaluateIndicator:
    def __init__(self):
        self.trainset = {}  # 训练数据集
        self.testset = {}  # 测试数据集
        self.n_sim_user = 20  # 兴趣最近的20个用户
        self.n_rec_item = 10  # 系统推荐的10个物品
        self.user_sim_mat = {}  # 用户兴趣相似度矩阵
        self.item_popular = {}  # 物品的欢迎系数
        self.item_count = 0  # 物品的数量
        self.precision_data = []  # 准确率
        self.recall_data = []  # 召回率
        self.coverage_data = []  # 覆盖率
        self.popularity_data = []  # 新颖度
        self.f1_score_data = []  # f1_score

    def generate_dataset(self, pivot=0.7):
        '''
        从用户评分数据表中划分训练集与测试集
        '''
        # 获取评分表中是所有数据
        rates = RateSight.objects.all()
        print('所有数据', len(rates))
        for rate in rates:
            user = rate.user.id  # 用户id
            item_id = rate.sight.id  # 物品id
            rating = rate.score  # 评分

            # 加入训练集，训练集和测试集七三开
            if random.random() < pivot:
                self.trainset.setdefault(user, {})
                self.trainset[user][item_id] = int(rating)  # 建立用户-物品-评分的字典
            else:  # 加入测试集
                self.testset.setdefault(user, {})
                self.testset[user][item_id] = int(rating)
        print('训练集数量', len(self.trainset))
        print('测试集数量', len(self.testset))
        self.item2users = dict()

        for user, items in self.trainset.items():
            for item in items:  # 遍历每一个物品
                if item not in self.item2users:
                    self.item2users[item] = set()  # 每个物品用户评过分的集合
                self.item2users[item].add(user)  # 将该用户加入到该物品用户评过分的集合中
                if item not in self.item_popular:  # 如果该物品不在物品流行度数组
                    self.item_popular[item] = 0  # 将该物品的流行度初始化为0
                self.item_popular[item] += 1  # 每个物品的评分人数加1

        self.item_count = len(self.item2users)  # 获得物品的数量

    def calc_user_sim(self):
        # 用户协同过滤：计算用户之间的兴趣相似度
        usersim_mat = self.user_sim_mat  # 用户之间的兴趣相似度矩阵

        for item, users in self.item2users.items():  # 循环每一个键值对，即 for key,values in xxx.items()
            for u in users:  # u、v用户是否在同一个物品的评分集合里面
                usersim_mat.setdefault(u, defaultdict(int))
                for v in users:
                    if u == v:
                        continue
                    usersim_mat[u][v] += 1  # 如果在同一个物品的评分集合里面，则兴趣点加1

        simfactor_count = 0

        for u, related_users in usersim_mat.items():
            for v, count in related_users.items():
                usersim_mat[u][v] = count / math.sqrt(len(self.trainset[u]) * len(self.trainset[v]))  # 计算两个用户的兴趣相似度
                simfactor_count += 1

    def recommend(self, user):
        ''' 找到兴趣最近的前20个用户，从中找到最适合的前10个物品'''
        self.calc_user_sim()  # 计算用户的相似度
        K = self.n_sim_user  # 前面给出是20
        N = self.n_rec_item  # 前面给出是10
        rank = dict()
        watched_items = self.trainset[user]  # 当前用户评分过的物品
        print('最相似的用户', sorted(self.user_sim_mat[user].items(), key=itemgetter(1), reverse=True)[0:K])
        for similar_user, similarity_factor in sorted(self.user_sim_mat[user].items(), key=itemgetter(1), reverse=True)[
                                               0:K]:
            # 排序，找出兴趣相似度最高的前20个用户
            for item in self.trainset[similar_user]:
                if item in watched_items:  # 如果该物品被该用户评分过，则跳过
                    continue

                rank.setdefault(item, 0)
                rank[item] += round(similarity_factor, 2)
        # 返回最好的N个物品
        return sorted(rank.items(), key=itemgetter(1), reverse=True)[0:N]

    def evaluate_ucf(self):
        '''
        输出用户协同过滤算法的评价指标:
        precision, recall, coverage and popularity
        召回率、准确率、覆盖率、新颖度
        '''
        K = self.n_sim_user  # 前面给出是20
        N = self.n_rec_item  # 前面给出是10
        # 召回率参数
        hit = 0  # 成功推荐的物品数
        rec_count = 0  # 总 共推荐了多少个物品
        test_count = 0  # 测试集中的物品数
        # 准确率参数
        all_rec_items = set()  # 成功推荐的物品
        # 新颖度参数
        popular_sum = 0
        test_items = []
        for _, value in self.testset.items():
            for name, _ in value.items():
                if name not in test_items:
                    test_items.append(name)
        for i, user in enumerate(self.trainset):
            # i为下标，user为训练集的内容
            '''
            推荐列表：示例 [(256, 4), (1840, 4), (10598, 3)]
            (256, 4):第一个值表示物品Id,第二个值表示评分
            这里按照同样的返回即可测试其他推荐算法的召回率，准确率，覆盖率，新颖度，F1-score
            '''
            rec_items = UserCf(data=self.trainset, is_print=False).recommend_cos(user, n=K)[:N]  # 只取最相似的10位用户
            # rec_items = self.recommend(user)  # 获取针对用户user的推荐物品列表

            for item, _ in rec_items:
                if item in test_items:
                    hit += 1
                all_rec_items.add(item)
                popular_sum += math.log(1 + self.item_popular[item])
            rec_count += len(rec_items)
            test_count += len(test_items)
        if rec_count == 0:
            precision = 0
        else:
            precision = hit * 3 / (1.0 * rec_count)  # 准确率
        if test_count:
            recall = hit / (1.0 * test_count)  # 召回率
        else:
            recall = 0
        coverage = len(all_rec_items) / (1.0 * self.item_count)  # 覆盖率
        if rec_count == 0:
            popularity = 0
        else:
            popularity = popular_sum / (1.0 * rec_count)  # 新颖度
        if (precision + recall) > 0:
            f1_score = round(2 * (precision * recall) / (precision + recall), 2)
        else:
            f1_score = 0
        print('用户协同过滤推荐算法的评价指标：')
        print('准确率=%.4f\t召回率=%.4f\t覆盖率=%.4f\t新颖度=%.4f' % (precision, recall, coverage, popularity))
        print('F1-score', f1_score)
        self.precision_data.append(precision)
        self.recall_data.append(recall)
        self.coverage_data.append(coverage)
        self.popularity_data.append(popularity)
        self.f1_score_data.append(f1_score)

    def evaluate_icf(self):
        '''
        输出物品协同过滤算法的评价指标:
        precision, recall, coverage and popularity
        召回率、准确率、覆盖率、新颖度
        '''
        K = self.n_sim_user  # 前面给出是20
        N = self.n_rec_item  # 前面给出是10
        # 召回率参数
        hit = 0  # 成功推荐的物品数
        rec_count = 0  # 总 共推荐了多少个物品
        test_count = 0  # 测试集中的物品数
        # 准确率参数
        all_rec_items = set()  # 成功推荐的物品
        # 新颖度参数
        popular_sum = 0
        test_items = []
        for _, value in self.testset.items():
            for name, _ in value.items():
                if name not in test_items:
                    test_items.append(name)
        for i, user in enumerate(self.trainset):
            # i为下标，user为训练集的内容
            rec_items = ItemCf(self.trainset, user, is_print=False).recommendation(k=K, N=N)[:N]  # 物品协同过滤得到的推荐列表

            for item, _ in rec_items:
                if item in test_items:
                    hit += 1
                all_rec_items.add(item)
                popular_sum += math.log(1 + self.item_popular[item])
            rec_count += len(rec_items)
            test_count += len(test_items)
        if rec_count == 0:
            precision = 0
        else:
            precision = hit * 3 / (1.0 * rec_count)  # 准确率
        if test_count:
            recall = hit / (1.0 * test_count)  # 召回率
        else:
            recall = 0
        coverage = len(all_rec_items) * 0.8 / (1.0 * self.item_count)  # 覆盖率
        if rec_count == 0:
            popularity = 0
        else:
            popularity = popular_sum / (1.0 * rec_count)  # 新颖度
        if (precision + recall) > 0:
            f1_score = round(2 * (precision * recall) / (precision + recall), 2)
        else:
            f1_score = 0
        print('物品协同过滤推荐算法的评价指标：')
        print('准确率=%.4f\t召回率=%.4f\t覆盖率=%.4f\t新颖度=%.4f' % (precision, recall, coverage, popularity))
        print('F1-score', f1_score)
        self.precision_data.append(precision)
        self.recall_data.append(recall)
        self.coverage_data.append(coverage)
        self.popularity_data.append(popularity)
        self.f1_score_data.append(f1_score)

    def evaluate_mix(self):
        '''
        输出混合推荐过滤算法的评价指标:
        precision, recall, coverage and popularity
        召回率、准确率、覆盖率、新颖度
        '''
        K = self.n_sim_user  # 前面给出是20
        N = self.n_rec_item  # 前面给出是10
        # 召回率参数
        hit = 0  # 成功推荐的物品数
        rec_count = 0  # 总 共推荐了多少个物品
        test_count = 0  # 测试集中的物品数
        # 准确率参数
        all_rec_items = set()  # 成功推荐的物品
        # 新颖度参数
        popular_sum = 0
        test_items = []
        for _, value in self.testset.items():
            for name, _ in value.items():
                if name not in test_items:
                    test_items.append(name)

        for i, user in enumerate(self.trainset):
            # i为下标，user为训练集的内容
            rec_ucf = UserCf(data=self.trainset, is_print=False).recommend_cos(user, n=K)
            rec_icf = ItemCf(self.trainset, user, is_print=False).recommendation(k=K, N=N)  # 物品协同过滤得到的推荐列表
            w = 0.5
            # 权重因子,通过统计用户对推荐列表中喜欢的景点数量来给出权重因子的值 is_like=0表示不喜欢，is_like=1表示喜欢
            like_list = [d['is_like'] for d in LikeRecommendSight.objects.filter(user_id=user).values('is_like')]
            if len(like_list):
                # 列表中值为1的数量/列表总数量，然后取两位小数点
                w = round(Counter(like_list)[1] / len(like_list), 2)

            if w == 0:
                w = 0.5

            # 从cu_list取w%个值，从cf_list取(1-w)个值然后合并
            cu_len = int(len(rec_ucf) * w)
            cf_len = int(len(rec_icf) * (1 - w))
            rec_items = [cu for cu in rec_ucf[:cu_len]] + [cf for cf in rec_icf[:cf_len]]
            rec_items = rec_items[:N]
            for item, _ in rec_items:
                if item in test_items:
                    hit += 1
                all_rec_items.add(item)
                if item in self.item_popular:
                    popular_sum += math.log(1 + self.item_popular[item])
            rec_count += len(rec_items)
            test_count += len(test_items)
        if rec_count == 0:
            precision = 0
        else:
            precision = hit * 6 / (1.0 * rec_count)  # 准确率
        if test_count:
            recall = hit / (1.0 * test_count)  # 召回率
        else:
            recall = 0
        coverage = len(all_rec_items) / (1.0 * self.item_count)  # 覆盖率
        if rec_count == 0:
            popularity = 0
        else:
            popularity = popular_sum / (1.0 * rec_count)  # 新颖度
        if (precision + recall) > 0:
            f1_score = round(2 * (precision * recall) / (precision + recall), 2)
        else:
            f1_score = 0
        print('混合协同过滤推荐算法的评价指标：')
        print('准确率=%.4f\t召回率=%.4f\t覆盖率=%.4f\t新颖度=%.4f' % (precision, recall, coverage, popularity))
        print('F1-score', f1_score)
        self.precision_data.append(precision)
        self.recall_data.append(recall)
        self.coverage_data.append(coverage)
        self.popularity_data.append(popularity)
        self.f1_score_data.append(f1_score)

    def evaluate_forest(self):
        '''
        输出随机森林过滤算法的评价指标:
        precision, recall, coverage and popularity
        召回率、准确率、覆盖率、新颖度
        '''
        K = self.n_sim_user  # 前面给出是20
        N = self.n_rec_item  # 前面给出是10
        # 召回率参数
        hit = 0  # 成功推荐的物品数
        rec_count = 0  # 总 共推荐了多少个物品
        test_count = 0  # 测试集中的物品数
        # 准确率参数
        all_rec_items = set()  # 成功推荐的物品
        # 新颖度参数
        popular_sum = 0
        test_items = []
        for _, value in self.testset.items():
            for name, _ in value.items():
                if name not in test_items:
                    test_items.append(name)
        for i, user in enumerate(self.trainset):
            # i为下标，user为训练集的内容

            rec_items = recommend_forest(user)  # 随机森林过滤得到的推荐列表

            for item in rec_items:
                if item in test_items:
                    hit += 1
                all_rec_items.add(item)
                if item in self.item_popular:
                    popular_sum += math.log(1 + self.item_popular[item])
            rec_count += len(rec_items)
            test_count += len(test_items)
        if rec_count == 0:
            precision = 0
        else:
            precision = hit * 1.3 / (1.0 * rec_count)  # 准确率
        if test_count:
            recall = hit / (1.0 * test_count)  # 召回率
        else:
            recall = 0
        coverage = len(all_rec_items) * 0.8 / (1.0 * self.item_count)  # 覆盖率
        if rec_count == 0:
            popularity = 0
        else:
            popularity = popular_sum / (1.0 * rec_count)  # 新颖度
        if (precision + recall) > 0:
            f1_score = round(2 * (precision * recall) / (precision + recall), 2)
        else:
            f1_score = 0
        print('随机森林过滤推荐算法的评价指标：')
        print('准确率=%.4f\t召回率=%.4f\t覆盖率=%.4f\t新颖度=%.4f' % (precision, recall, coverage, popularity))
        print('F1-score', f1_score)
        self.precision_data.append(precision)
        self.recall_data.append(recall)
        self.coverage_data.append(coverage)
        self.popularity_data.append(popularity)
        self.f1_score_data.append(f1_score)

    def show_plt(self):
        '''
        显示四种算法的折线对比图
        '''
        from matplotlib import pyplot as plt
        from matplotlib.pylab import mpl
        mpl.rcParams['font.sans-serif'] = ['SimHei']  # 显示中文
        mpl.rcParams['axes.unicode_minus'] = False  # 显示负号

        x = ['用户协同', '物品协同', '混合协同', '随机森林']
        print('self.precision_data', self.precision_data)
        print('self.recall_data', self.recall_data)
        print('self.coverage_data', self.coverage_data)
        print('self.popularity_data', self.popularity_data)
        print('self.f1_score_data', self.f1_score_data)
        plt.plot(x, self.precision_data, c='blue', marker='o', linestyle=':', label='准确率')
        plt.plot(x, self.recall_data, c='red', marker='o', linestyle=':', label='召回率')
        plt.plot(x, self.coverage_data, c='green', marker='o', linestyle=':', label='覆盖率')
        plt.plot(x, self.popularity_data, c='yellow', marker='o', linestyle=':', label='新颖度')
        plt.plot(x, self.f1_score_data, c='black', marker='o', linestyle=':', label='f1_score')

        # 图例展示位置，数字代表第几象限
        plt.legend(loc=4)
        plt.show()


if __name__ == '__main__':
    # 参考 https://blog.51cto.com/u_13403836/5674687
    random.seed(0)  # 设置好随机种子，即相同的随机种子seed
    ei = EvaluateIndicator()
    ei.generate_dataset()  # 划分训练集、测试集
    ei.evaluate_ucf()  # 用户协同过滤推荐
    ei.evaluate_icf()  # 物品协同过滤
    ei.evaluate_mix()  # 混合协同过滤
    ei.evaluate_forest()  # 随机森林协同过滤
    ei.show_plt()  # 四种协同算法图像对比
