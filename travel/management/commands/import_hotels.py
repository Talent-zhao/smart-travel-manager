# -*- coding: utf-8 -*-
"""
Django管理命令：为现有城市补充爬取酒店数据
使用方法: python manage.py import_hotels
"""
from django.core.management.base import BaseCommand
from travel.models import City, Hotel, Sight
import sys
import os

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, BASE_DIR)

from travel.spiders import get_hotel
import time


class Command(BaseCommand):
    help = '为现有城市补充爬取酒店数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='处理的城市数量限制（默认5个）',
        )

    def get_city_url_from_sight(self, city):
        """从城市的景点URL中推断城市URL"""
        sight = Sight.objects.filter(city=city).first()
        if sight and sight.url:
            url_parts = sight.url.split('/')
            if len(url_parts) >= 4:
                city_slug = url_parts[3]
                if city_slug and city_slug != 'poi':
                    return f"https://place.qyer.com/{city_slug}/"
        return None

    def update_hotels_for_city(self, city, max_hotels=20):
        """为单个城市爬取酒店数据"""
        city_base_url = self.get_city_url_from_sight(city)
        
        if not city_base_url and city.name_en:
            name_parts = city.name_en.split()
            if len(name_parts) > 1:
                city_slug = name_parts[-1].lower().replace(' ', '-')
                city_base_url = f"https://place.qyer.com/{city_slug}/"
        
        if not city_base_url:
            self.stdout.write(self.style.WARNING(f"城市 {city.name} 无法确定URL，跳过"))
            return 0
        
        hotel_url = f"{city_base_url}hotel/"
        self.stdout.write(f"正在为城市 {city.name} 爬取酒店数据...")
        self.stdout.write(f"酒店URL: {hotel_url}")
        
        try:
            hotel_list = get_hotel(hotel_url, 'hotel')
            
            if not hotel_list:
                self.stdout.write(self.style.WARNING(f"  未找到酒店数据"))
                return 0
            
            self.stdout.write(f"  找到 {len(hotel_list)} 个酒店")
            
            saved_count = 0
            for hotel_data in hotel_list[:max_hotels]:
                try:
                    hotel_name = hotel_data.get('name', '')
                    if not hotel_name:
                        continue
                    
                    if Hotel.objects.filter(city=city, name=hotel_name).exists():
                        continue
                    
                    detail = hotel_data.get('detail', {})
                    grade = hotel_data.get('grade', 0)
                    if not grade:
                        grade = 0
                    if not detail:
                        detail = {'detail': '', 'address': '', 'phone': '', 'price': '', 'hotel_type': '酒店', 'tips': []}
                    
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
                    saved_count += 1
                    self.stdout.write(self.style.SUCCESS(f"    ✓ 保存酒店: {hotel_name}"))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ✗ 保存酒店失败: {e}"))
                    continue
            
            self.stdout.write(self.style.SUCCESS(f"  成功保存 {saved_count} 个酒店"))
            return saved_count
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  爬取酒店数据时出错: {e}"))
            return 0

    def handle(self, *args, **options):
        limit = options['limit']
        
        self.stdout.write("=" * 60)
        self.stdout.write("开始为现有城市补充酒店数据")
        self.stdout.write("=" * 60)
        
        cities = City.objects.all().order_by('id')
        total_cities = cities.count()
        existing_hotels = Hotel.objects.count()
        
        self.stdout.write(f"共有 {total_cities} 个城市需要处理")
        self.stdout.write(f"当前数据库中已有 {existing_hotels} 个酒店\n")
        
        total_saved = 0
        processed = 0
        
        test_cities = cities[:limit]
        
        for city in test_cities:
            processed += 1
            self.stdout.write(f"\n[{processed}/{len(test_cities)}] 处理城市: {city.name}")
            
            saved = self.update_hotels_for_city(city)
            total_saved += saved
            
            time.sleep(2)
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"处理完成！"))
        self.stdout.write(f"处理了 {processed} 个城市")
        self.stdout.write(f"新增了 {total_saved} 个酒店")
        self.stdout.write(f"数据库中现在共有 {Hotel.objects.count()} 个酒店")
        self.stdout.write("=" * 60)

