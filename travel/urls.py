# -*- coding: utf-8 -*-
from django.urls import path, re_path

from travel import views

urlpatterns = [
    path('import_data/', views.import_data, name='import_data'),  # 导入数据
    path("", views.index, name='index'),  # 首页
    path("home", views.home, name='home'),  # 首页
    path('login/', views.login, name='login'),  # 账号密码登录
    path('login_face/', views.login_face, name='login_face'),  # 人脸识别登录/切换入口
    path('register/', views.register, name='register'),  # 注册
    path('register_face/', views.register_face, name='register_face'),  # 人脸识别注册
    path('logout/', views.logout, name='logout'),  # 退出
    path('modify_pwd/', views.modify_pwd, name='modify_pwd'),  # 修改密码
    path('search/<str:selected>/', views.search, name='search'),  # 搜索
    path('all_city/', views.all_city, name='all_city'),  # 所有城市
    path('city/<int:city_id>/', views.city, name='city'),  # 具体的城市
    path('all_sight/', views.all_sight, name='all_sight'),  # 所有景点
    path('sight/<int:sight_id>/', views.sight, name='sight'),  # 具体的景点
    path('recommend_sight/', views.recommend_sight, name='recommend_sight'),  # 推荐景点
    path('all_hotel/', views.all_hotel, name='all_hotel'),  # 所有酒店-民宿
    path('hotel/<int:hotel_id>/book/', views.book_hotel, name='book_hotel'),  # 酒店预订
    path('hotel-booking/<int:booking_id>/update/', views.update_hotel_booking, name='update_hotel_booking'),  # 修改酒店预订
    path('hotel-booking/<int:booking_id>/cancel/', views.cancel_hotel_booking, name='cancel_hotel_booking'),  # 取消酒店预订
    path('all_food_shopping/', views.all_food_shopping, name='all_food_shopping'),  # 美食购物活动
    path('like_recommend_sight/', views.like_recommend_sight, name='like_recommend_sight'),  # 用户对推荐进行反馈
    path("booking/<int:sight_id>/", views.booking, name="booking"),  # 预订出行
    path("score/<int:sight_id>/", views.score, name="score"),  # 评分
    path("comment/<int:sight_id>/", views.comment, name="comment"),  # 评论
    path("comment_like/<int:comment_id>/", views.comment_like, name="comment_like"),  # 给评论点赞
    path("collect/<int:sight_id>/", views.collect, name="collect"),  # 收藏
    path("like/<int:sight_id>/", views.like, name="like"),  # 点赞
    path('personal/', views.personal, name='personal'),  # 个人中心
    path("my_questionnaire/", views.my_questionnaire, name="my_questionnaire"),  # 获取我的旅游调查问卷
    path("my_booking/", views.my_booking, name="my_booking"),  # 获取我的预订
    path("my_like/", views.my_like, name="my_like"),  # 获取我的点赞
    path("my_collect/", views.my_collect, name="my_collect"),  # 获取我的收藏
    path("my_rate/", views.my_rate, name="my_rate"),  # 我打分过的景点
    path("my_comments/", views.my_comments, name="my_comments"),  # 我的评论
    path("delete_rate/<int:rate_id>", views.delete_rate, name="delete_rate"),  # 取消评分
    path("delete_comment/<int:comment_id>", views.delete_comment, name="delete_comment"),  # 取消评论
    path('update_pic/', views.update_pic, name='update_pic'),  # 更新
    path('recognize_id_card/', views.recognize_id_card, name='recognize_id_card'),  # 身份证识别
    path('import_hotels/', views.import_hotels, name='import_hotels'),  # 导入酒店数据
]
