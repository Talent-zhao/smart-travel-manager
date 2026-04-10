"""旅游数据爬虫（后台 xadmin / 管理命令调用）。输出写入项目根目录 travel.txt 与 offline/data/citys.txt。"""

from travel.spiders.travel_spider_data import get_hotel, main

__all__ = ['get_hotel', 'main']
