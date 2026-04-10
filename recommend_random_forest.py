# -*- coding: utf-8 -*-
"""
线上入口 recommend_by_forse：K-means 分群（user_cluster.pkl）→ 簇内热门 + 簇内 ItemCF → Borda 融合；
失败时全站热门兜底。随机森林训练与 recommend() 保留作旁路/实验与离线评估。

K-means 与 pkl 读写见 user_cluster_kmeans.py。
"""
import os
import django

os.environ["DJANGO_SETTINGS_MODULE"] = "travel_manager.settings"
django.setup()
from travel.models import User, Sight, RateSight, LikeSight, CollectSight, CommentSight, BookingSight, \
    LikeRecommendSight, QuestionnaireSight
import joblib
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from user_cluster_kmeans import load_cluster_user_ids_for_user

# 簇内两路 Borda 权重（在 recommend_by_forse 内归一化）
WEIGHT_CLUSTER_HOT = 0.45
WEIGHT_CLUSTER_ICF = 0.55
# 兼容旧名称（外部若 import 旧常量仍可用）
WEIGHT_RANDOM_FOREST = WEIGHT_CLUSTER_HOT
WEIGHT_HYBRID_CF = WEIGHT_CLUSTER_ICF

# 模型文件固定在项目根目录（与 manage.py 同级），不依赖进程当前工作目录
_RF_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'randomforest.joblib')


def get_hot_sight(user_id, sight_id=None):
    # 获取热门景点
    unlike_sight_ids = [d['sight_id'] for d in
                        LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values('sight_id')]
    if sight_id and sight_id not in unlike_sight_ids:
        unlike_sight_ids.append(sight_id)
    return Sight.objects.exclude(id__in=unlike_sight_ids).order_by('-grade')[:10]


def get_all_data():
    '''
    从数据库中获取所有物品评分数据
    [用户特征(点赞，收藏，评论，预订,最喜欢的景点类型,最喜欢的出行方式,最喜欢的旅行方式,最低预算,最高预算),
    物品特征(推荐指数，收藏人数,点赞人数,浏览量,评分人数,平均评分)
    ]
    '''
    X = []
    y = []
    # 从评分表中获取所有景点数据
    for rate in RateSight.objects.all():
        user = rate.user
        sight = rate.sight
        # 获取用户对这个物品的点赞，收藏，评论，预订信息,反馈
        if LikeSight.objects.filter(user=user, sight=sight):
            is_like = 1
        else:
            is_like = 0
        if CollectSight.objects.filter(user=user, sight=sight):
            is_collect = 1
        else:
            is_collect = 0
        comment_count = CommentSight.objects.filter(user=user, sight=sight).count()
        if BookingSight.objects.filter(user=user, sight=sight):
            is_booking = 1
        else:
            is_booking = 0
        if LikeRecommendSight.objects.filter(user=user, sight=sight, is_like=0):
            # 用户反馈不喜欢则值为0
            is_like_recommend = 0
        else:
            is_like_recommend = 1
        qs = QuestionnaireSight.objects.get(user=user)
        X.append([is_like, is_collect, comment_count, is_booking,is_like_recommend,
                  int(qs.sight_type), int(qs.travel_way), int(qs.sight_way),
                  sight.collect_num, sight.like_num, sight.look_num, sight.rate_num, sight.all_score,
                  ])
        score = int(rate.score)
        # 评分大于等于6分就把标签置为1，否则置为0
        y.append(1 if score >=6 else 0)
    return X, y


def split_data(X, y):
    '''
    划分数据集
    '''
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    return X_train, X_test, y_train, y_test


def train_model(X_train, y_train):
    '''
    训练模型
    '''

    # 创建随机森林分类器
    rf = RandomForestClassifier(n_estimators=100)

    # 在训练集上训练模型
    rf.fit(X_train, y_train)
    joblib.dump(rf, _RF_MODEL_PATH)  # 保存模型


def predict(data):
    '''
    预测
    '''
    try:
        model = joblib.load(_RF_MODEL_PATH)
        return model.predict(data)
    except (KeyError, ValueError, EOFError, ImportError, Exception) as e:
        # 模型文件损坏或版本不兼容，返回默认值
        print(f"模型加载失败: {e}")
        # 尝试删除损坏的模型文件
        try:
            if os.path.exists(_RF_MODEL_PATH):
                os.remove(_RF_MODEL_PATH)
                print("已删除损坏的模型文件，下次访问时将使用热门景点推荐")
        except:
            pass
        # 返回与输入数据长度相同的零数组
        import numpy as np
        if isinstance(data, list) and len(data) > 0:
            return np.array([0] * len(data))
        return np.array([0])

def evaluation(y_test, y_predict):
    accuracy = classification_report(y_test, y_predict, output_dict=True)['accuracy']
    s = classification_report(y_test, y_predict, output_dict=True)['weighted avg']
    precision = s['precision']
    recall = s['recall']
    f1_score = s['f1-score']
    return accuracy, precision, recall, f1_score


def accuracy(y_test, y_pred):
    '''
    评分
    '''
    # accuracy = accuracy_score(y_test, y_pred)
    accuracy, precision, recall, f1_score = evaluation(y_test, y_pred)
    print("随机森林预测准确率:", accuracy)
    print("随机森林预测精确度:", precision)
    print("随机森林预测召回率:", recall)
    print("随机森林预测F1值:", f1_score)


def run_train():
    '''
    训练模型
    '''
    # 1、获取数据
    X, y = get_all_data()
    if len(y) < 10:
        return
    print('x', X)
    print('y', y)
    # 2、划分数据集
    X_train, X_test, y_train, y_test = split_data(X, y)
    # 3、训练模型
    train_model(X_train, y_train)
    # 4、在测试集上进行预测
    y_pred = predict(X_test)

    # 5、计算准确率
    accuracy(y_test, y_pred)


def recommend(user_id):
    '''
    推荐
    '''
    try:
        user = User.objects.get(id=user_id)

        # 检查用户是否有调查问卷
        try:
            qs = QuestionnaireSight.objects.get(user=user)
        except QuestionnaireSight.DoesNotExist:
            # 如果用户没有调查问卷，返回空列表，让系统使用热门景点推荐
            print(f"用户 {user_id} 没有调查问卷，无法使用随机森林推荐")
            return []

        recommend_ret = {}
        for rate in RateSight.objects.all():
            # 获取用户对这个物品的点赞，收藏，评论，预订信息
            data = []
            sight = rate.sight
            if LikeSight.objects.filter(user=user, sight=sight):
                is_like = 1
            else:
                is_like = 0
            if CollectSight.objects.filter(user=user, sight=sight):
                is_collect = 1
            else:
                is_collect = 0
            comment_count = CommentSight.objects.filter(user=user, sight=sight).count()
            if BookingSight.objects.filter(user=user, sight=sight):
                is_booking = 1
            else:
                is_booking = 0
            if LikeRecommendSight.objects.filter(user=user, sight=sight, is_like=0):
                # 用户反馈不喜欢则值为0
                is_like_recommend = 0
            else:
                is_like_recommend = 1

            data.append([is_like, is_collect, comment_count, is_booking, is_like_recommend,
                         int(qs.sight_type), int(qs.travel_way), int(qs.sight_way),
                         sight.collect_num, sight.like_num, sight.look_num, sight.rate_num, sight.all_score,
                         ])
            predict_result = predict(data)
            # predict 返回的是数组，取第一个值
            if hasattr(predict_result, '__len__') and len(predict_result) > 0:
                recommend_ret[sight.id] = predict_result[0]
            else:
                recommend_ret[sight.id] = predict_result

        # 按评分对物品字典进行降序排序
        recommend_sorted = sorted(recommend_ret.items(), key=lambda item: item[1], reverse=True)[:25]
        print('recommend_sorted', recommend_sorted)
        return [item[0] for item in recommend_sorted if item[1] != 0]
    except Exception as e:
        print(f"推荐函数出错: {e}")
        return []


def _rf_sight_list(user_id, sight_id=None):
    """
    随机森林分支：返回有序 Sight 列表（最多 10 条）。
    无模型、无问卷或预测为空时与原先一致，退化为热门推荐列表。
    """
    try:
        if not os.path.exists(_RF_MODEL_PATH):
            return list(get_hot_sight(user_id, sight_id))
        recommend_ids = recommend(user_id)
        rated_ids = {r.sight_id for r in RateSight.objects.filter(user_id=user_id)}
        unlike_ids = {u.sight_id for u in LikeRecommendSight.objects.filter(user_id=user_id, is_like=0)}
        filtered = []
        for sid in recommend_ids:
            if sid in rated_ids or sid in unlike_ids:
                continue
            if sight_id and sid == sight_id:
                continue
            filtered.append(sid)
        print('随机森林分支候选 id 列表', filtered)
        if not filtered:
            return list(get_hot_sight(user_id, sight_id))
        return list(Sight.objects.filter(id__in=filtered).order_by('-grade')[:10])
    except Exception as e:
        print(f"随机森林分支出错: {e}")
        return list(get_hot_sight(user_id, sight_id))


def _borda_merge_scores(list_a, list_b, w_a, w_b):
    """
    按列表位次做 Borda 加权，同景点分值累加。
    list_a / list_b：两路有序 Sight 列表（如簇内热门、簇内 ItemCF）；w_a / w_b 为对应权重。
    """
    scores = {}
    n_a, n_b = len(list_a), len(list_b)
    for i, s in enumerate(list_a):
        scores[s.id] = scores.get(s.id, 0) + w_a * (n_a - i) / max(n_a, 1)
    for i, s in enumerate(list_b):
        scores[s.id] = scores.get(s.id, 0) + w_b * (n_b - i) / max(n_b, 1)
    return scores


def recommend_by_forse(user_id, sight_id=None):
    """
    线上融合入口：K-means 簇 → recommend_cluster_branch_lists（簇内热门 + 簇内 ItemCF）→ Borda；
    簇不可用或融合无分时用 get_hot_sight。视图层仍用 recommend_by_forse(user_id, sight_id=...)。
    """
    w_hot = WEIGHT_CLUSTER_HOT
    w_icf = WEIGHT_CLUSTER_ICF
    total_w = w_hot + w_icf
    if total_w > 0:
        w_hot, w_icf = w_hot / total_w, w_icf / total_w

    hot_list = []
    icf_list = []
    cluster_user_ids = load_cluster_user_ids_for_user(user_id)
    if cluster_user_ids:
        try:
            from recommend_sights import recommend_cluster_branch_lists
            hot_list, icf_list = recommend_cluster_branch_lists(
                user_id, sight_id=sight_id, cluster_user_ids=cluster_user_ids
            )
        except Exception as e:
            print(f"簇内召回分支不可用，降级热门: {e}")

    scores = _borda_merge_scores(hot_list, icf_list, w_hot, w_icf)
    if not scores:
        return get_hot_sight(user_id, sight_id)

    rated_ids = set(RateSight.objects.filter(user_id=user_id).values_list('sight_id', flat=True))
    unlike_ids = set(LikeRecommendSight.objects.filter(user_id=user_id, is_like=0).values_list('sight_id', flat=True))

    ranked_ids = sorted(scores.keys(), key=lambda sid: (-scores[sid],))
    ranked_ids = [
        sid for sid in ranked_ids
        if sid not in rated_ids and sid not in unlike_ids and (not sight_id or sid != sight_id)
    ]
    if not ranked_ids:
        return get_hot_sight(user_id, sight_id)

    top_ids = ranked_ids[:10]
    print('融合后推荐 id（Borda，簇内热门+簇内ICF）', top_ids)

    from django.db.models import Case, When
    order_case = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(top_ids)])
    return Sight.objects.filter(pk__in=top_ids).order_by(order_case)


if __name__ == '__main__':
    run_train()
    recommend(1)
