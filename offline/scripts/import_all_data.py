# -*- coding: utf-8 -*-
"""
完整的数据导入脚本
从travel.txt读取所有数据并导入到数据库
"""
import os
import sys
import django

# 设置Django环境（本脚本位于 offline/scripts/，项目根目录为上两级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_manager.settings')
django.setup()

import json
from travel.models import *


def check_travel_txt():
    """检查项目根目录 travel.txt 的 JSON 行结构与酒店等字段（不写入数据库）。"""
    travel_txt = os.path.join(BASE_DIR, 'travel.txt')
    if not os.path.exists(travel_txt):
        print(f'未找到 {travel_txt}')
        return
    with open(travel_txt, 'r', encoding='utf-8', errors='replace') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    print(f'总行数: {len(lines)}')
    print('\n检查前3行的数据结构:')
    for i, line in enumerate(lines[:3], 1):
        try:
            data = json.loads(line)
            print(f'\n第{i}行:')
            print(f"  国家: {data.get('country_zn', 'N/A')}")
            city_info = data.get('city_info', {})
            print(f"  城市: {city_info.get('name', 'N/A')}")
            print(f"  城市信息包含的键: {list(city_info.keys())}")
            if 'hotel_list' in city_info:
                hotel_list = city_info['hotel_list']
                print(f"  酒店列表: {len(hotel_list) if hotel_list else 0} 个酒店")
                if hotel_list:
                    print(f"  示例酒店: {hotel_list[0]}")
            else:
                print('  没有hotel_list字段')
        except Exception as e:
            print(f'第{i}行解析错误: {e}')


def main():
    print("=" * 60)
    print("开始导入travel.txt中的所有数据")
    print("=" * 60)
    
    # 统计信息
    stats = {
        'countries': 0,
        'cities': 0,
        'sights': 0,
        'foods': 0,
        'shoppings': 0,
        'activities': 0,
        'hotels': 0,
        'carousels': 0,
    }
    
    # 读取文件
    travel_txt = os.path.join(BASE_DIR, 'travel.txt')
    if not os.path.exists(travel_txt):
        print(f"错误：找不到文件 {travel_txt}")
        return
    
    data_list = []
    with open(travel_txt, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f.readlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                data_list.append(data)
            except json.JSONDecodeError as e:
                print(f'第{line_num}行JSON解析错误: {e}')
                continue
    
    print(f"成功读取 {len(data_list)} 条数据\n")
    
    # 导入数据
    for i, data in enumerate(data_list, 1):
        try:
            # 处理国家
            country_zn = data.get('country_zn', '')
            country_en = data.get('country_en', '')
            
            country, created = Country.objects.get_or_create(
                name=country_zn,
                defaults={'name_en': country_en, 'photo': f'media/country_photo/{country_zn}.png'}
            )
            if created:
                stats['countries'] += 1
            
            # 处理城市
            city_info = data.get('city_info', {})
            city_name = city_info.get('name', '')
            
            if city_name == '台湾' or not city_name:
                continue
            
            city, created = City.objects.get_or_create(
                name=city_name,
                defaults={
                    'country': country,
                    'url': city_info.get('url', ''),
                    'name_en': city_info.get('name_en', ''),
                    'cover_pic': city_info.get('cover_pic', ''),
                    'person_count': int(city_info.get('person_count', '0人去').split('人')[0]) if '人' in str(city_info.get('person_count', '')) else 0
                }
            )
            if created:
                stats['cities'] += 1
            
            # 处理轮播图
            carousel_pics = city_info.get('carousel_pic', [])
            for pic in carousel_pics:
                if pic and not Carousel.objects.filter(city=city, photo=pic).exists():
                    Carousel.objects.create(city=city, photo=pic)
                    stats['carousels'] += 1
            
            # 处理景点
            sight_list = city_info.get('sight_list', [])
            for sight in sight_list:
                if not sight.get('name'):
                    continue
                if not Sight.objects.filter(city=city, name=sight['name']).exists():
                    detail = sight.get('detail', {})
                    Sight.objects.create(
                        city=city,
                        url=sight.get('url', ''),
                        name=sight['name'],
                        cover_pic=sight.get('filename', ''),
                        grade=sight.get('grade', 0) or 0,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False)
                    )
                    stats['sights'] += 1
            
            # 处理美食
            food_list = city_info.get('food_list', [])
            for food in food_list:
                if not food.get('name'):
                    continue
                if not Food.objects.filter(city=city, name=food['name']).exists():
                    detail = food.get('detail', {})
                    Food.objects.create(
                        city=city,
                        url=food.get('url', ''),
                        name=food['name'],
                        cover_pic=food.get('filename', ''),
                        grade=food.get('grade', 0) or 0,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False)
                    )
                    stats['foods'] += 1
            
            # 处理购物
            shopping_list = city_info.get('shopping_list', [])
            for shopping in shopping_list:
                if not shopping.get('name'):
                    continue
                if not Shopping.objects.filter(city=city, name=shopping['name']).exists():
                    detail = shopping.get('detail', {})
                    Shopping.objects.create(
                        city=city,
                        url=shopping.get('url', ''),
                        name=shopping['name'],
                        cover_pic=shopping.get('filename', ''),
                        grade=shopping.get('grade', 0) or 0,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False)
                    )
                    stats['shoppings'] += 1
            
            # 处理活动
            activity_list = city_info.get('activity_list', [])
            for activity in activity_list:
                if not activity.get('name'):
                    continue
                if not Activity.objects.filter(city=city, name=activity['name']).exists():
                    detail = activity.get('detail', {})
                    Activity.objects.create(
                        city=city,
                        url=activity.get('url', ''),
                        name=activity['name'],
                        cover_pic=activity.get('filename', ''),
                        grade=activity.get('grade', 0) or 0,
                        rank=detail.get('rank', ''),
                        detail=detail.get('detail', ''),
                        tips=json.dumps(detail.get('tips', []), ensure_ascii=False)
                    )
                    stats['activities'] += 1
            
            # 处理酒店
            hotel_list = city_info.get('hotel_list', [])
            for hotel in hotel_list:
                if not hotel.get('name'):
                    continue
                if not Hotel.objects.filter(city=city, name=hotel['name']).exists():
                    detail = hotel.get('detail', {})
                    Hotel.objects.create(
                        city=city,
                        url=hotel.get('url', ''),
                        name=hotel['name'],
                        cover_pic=hotel.get('filename', ''),
                        grade=hotel.get('grade', 0) or 0,
                        detail=detail.get('detail', ''),
                        address=detail.get('address', ''),
                        phone=detail.get('phone', ''),
                        price=detail.get('price', ''),
                        hotel_type=detail.get('hotel_type', '酒店')
                    )
                    stats['hotels'] += 1
            
            if i % 100 == 0:
                print(f"已处理 {i}/{len(data_list)} 条数据...")
                
        except Exception as e:
            print(f"处理第{i}条数据时出错: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # 显示统计信息
    print("\n" + "=" * 60)
    print("导入完成！统计信息：")
    print("=" * 60)
    print(f"新增国家: {stats['countries']}")
    print(f"新增城市: {stats['cities']}")
    print(f"新增景点: {stats['sights']}")
    print(f"新增美食: {stats['foods']}")
    print(f"新增购物: {stats['shoppings']}")
    print(f"新增活动: {stats['activities']}")
    print(f"新增酒店: {stats['hotels']}")
    print(f"新增轮播图: {stats['carousels']}")
    print("=" * 60)
    
    # 显示数据库中的总数
    print("\n数据库中的总数：")
    print(f"国家: {Country.objects.count()}")
    print(f"城市: {City.objects.count()}")
    print(f"景点: {Sight.objects.count()}")
    print(f"美食: {Food.objects.count()}")
    print(f"购物: {Shopping.objects.count()}")
    print(f"活动: {Activity.objects.count()}")
    print(f"酒店: {Hotel.objects.count()}")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        check_travel_txt()
    else:
        main()








