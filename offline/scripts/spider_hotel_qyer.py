# -*- coding: utf-8 -*-
"""
爬取 https://hotel.qyer.com/ 网站的酒店数据
保存到文件中，后续可以导入到数据库
"""
import json
import os
import time
import re
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# 项目根目录（manage.py 同级）；本脚本位于 offline/scripts/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ask_url(url, referer=None):
    """请求URL，返回HTML内容"""
    count = 0
    head = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": referer if referer else "https://hotel.qyer.com/",
        "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
    }
    time.sleep(1)  # 增加延迟，避免请求过快
    
    while count < 5:
        try:
            response = requests.get(url, headers=head, timeout=30)
            response.raise_for_status()
            html = response.text
            return html
        except requests.exceptions.Timeout as e:
            print(f'第{count+1}次请求超时: {url}')
            time.sleep(3 + count)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f'第{count+1}次请求被拦截(403): {url}')
                time.sleep(5 + count)
            else:
                print(f'第{count+1}次请求错误(HTTP {e.response.status_code}): {url}')
        except Exception as e:
            print(f'第{count+1}次请求异常: {url}, 错误: {e}')
        
        # 尝试更换User-Agent
        try:
            ua = UserAgent()
            head["User-Agent"] = ua.random
        except:
            pass
        
        count += 1
        if count < 5:
            time.sleep(2)
    
    return None


def save_img(url, name, path):
    """保存图片"""
    try:
        # 先处理名称，移除特殊字符
        clean_name = name.replace("/", "").replace("\\", "").replace(":", "")
        rel = os.path.join(path, f'{clean_name}.png').replace('\\', '/')
        filename = os.path.join(_PROJECT_ROOT, 'media', path, f'{clean_name}.png')
        dir_path = os.path.dirname(filename)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        time.sleep(0.5)
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return rel
        return ''
    except Exception as e:
        print(f'保存图片失败: {e}')
        return ''


def get_city_hotel_list(city_name, city_slug=None):
    """
    获取城市的酒店列表
    :param city_name: 城市名称（中文）
    :param city_slug: 城市URL slug（可选，如果不提供会尝试从city_name推断）
    :return: 酒店列表
    """
    # 构建搜索URL
    # hotel.qyer.com 的搜索URL格式可能是: https://hotel.qyer.com/search?city=xxx
    # 或者直接访问城市页面: https://hotel.qyer.com/xxx
    
    if not city_slug:
        # 尝试从城市名称推断slug
        # 这里需要根据实际情况调整
        city_slug = city_name.lower().replace(' ', '-')
    
    # 尝试多种URL格式
    urls_to_try = [
        f"https://hotel.qyer.com/search?city={city_name}",
        f"https://hotel.qyer.com/search?keyword={city_name}",
        f"https://hotel.qyer.com/{city_slug}",
        f"https://hotel.qyer.com/city/{city_slug}",
    ]
    
    hotel_list = []
    items = []  # 初始化items变量
    
    for url in urls_to_try:
        print(f"尝试访问: {url}")
        html = ask_url(url, referer="https://hotel.qyer.com/")
        
        if not html:
            continue
        
        soup = BeautifulSoup(html, "html.parser")
        
        # 尝试多种选择器来找到酒店列表
        # 需要根据实际页面结构调整
        items = []  # 重置items
        
        # 方法1: 查找包含酒店信息的div或li
        items = soup.find_all(['div', 'li'], class_=re.compile(r'hotel|item|card|list', re.I))
        
        # 方法2: 查找包含酒店链接的元素
        if not items:
            items = soup.find_all('a', href=re.compile(r'/hotel/|/accommodation/', re.I))
        
        # 方法3: 查找包含价格信息的元素
        if not items:
            price_elements = soup.find_all(text=re.compile(r'元|¥|RMB|USD', re.I))
            if price_elements:
                for price_elem in price_elements[:20]:  # 限制数量
                    parent = price_elem.find_parent(['div', 'li', 'article'])
                    if parent:
                        items.append(parent)
        
        if items:
            print(f"找到 {len(items)} 个可能的酒店项目")
            break
    
    # 解析酒店信息
    if not items:
        print(f"未找到 {city_name} 的酒店数据")
        return hotel_list
    
    for item in items[:50]:  # 限制最多50个
        try:
            hotel_data = parse_hotel_item(item, city_name)
            if hotel_data and hotel_data.get('name'):
                hotel_list.append(hotel_data)
        except Exception as e:
            print(f"解析酒店项目失败: {e}")
            continue
    
    return hotel_list


def parse_hotel_item(item, city_name):
    """
    解析单个酒店项目
    :param item: BeautifulSoup元素
    :param city_name: 城市名称
    :return: 酒店数据字典
    """
    hotel_data = {
        'name': '',
        'url': '',
        'cover_pic': '',
        'grade': 0,
        'price': '',
        'address': '',
        'phone': '',
        'detail': '',
        'hotel_type': '酒店',
        'city': city_name,
    }
    
    # 提取酒店名称
    name_elem = item.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|hotel', re.I))
    if not name_elem:
        name_elem = item.find('a', href=re.compile(r'/hotel/|/accommodation/', re.I))
    
    if name_elem:
        hotel_data['name'] = name_elem.get_text(strip=True)
        # 提取URL
        if name_elem.name == 'a' and name_elem.get('href'):
            href = name_elem.get('href')
            if href.startswith('http'):
                hotel_data['url'] = href
            else:
                hotel_data['url'] = f"https://hotel.qyer.com{href}"
    
    # 提取图片
    img_elem = item.find('img')
    if img_elem:
        img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
        if img_src:
            if not img_src.startswith('http'):
                img_src = f"https:{img_src}" if img_src.startswith('//') else f"https://hotel.qyer.com{img_src}"
            hotel_data['cover_pic'] = img_src
    
    # 提取评分/推荐指数
    grade_elem = item.find(['span', 'div'], class_=re.compile(r'grade|score|rating|star', re.I))
    if grade_elem:
        grade_text = grade_elem.get_text(strip=True)
        # 提取数字
        grade_match = re.search(r'(\d+\.?\d*)', grade_text)
        if grade_match:
            try:
                hotel_data['grade'] = round(float(grade_match.group(1)), 1)
            except:
                pass
    
    # 提取价格
    price_elem = item.find(['span', 'div'], class_=re.compile(r'price|cost|rate', re.I))
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        hotel_data['price'] = price_text
    
    # 提取地址
    address_elem = item.find(['span', 'div', 'p'], class_=re.compile(r'address|location|addr', re.I))
    if address_elem:
        hotel_data['address'] = address_elem.get_text(strip=True)
    
    # 提取详情/简介
    detail_elem = item.find(['p', 'div'], class_=re.compile(r'desc|detail|intro|summary', re.I))
    if detail_elem:
        hotel_data['detail'] = detail_elem.get_text(strip=True)
    
    return hotel_data


def get_hotel_detail(url):
    """
    获取酒店详细信息
    :param url: 酒店详情页URL
    :return: 酒店详细信息字典
    """
    html = ask_url(url, referer="https://hotel.qyer.com/")
    if not html:
        return {}
    
    soup = BeautifulSoup(html, "html.parser")
    detail_data = {
        'detail': '',
        'address': '',
        'phone': '',
        'price': '',
        'hotel_type': '酒店',
    }
    
    # 提取详细信息
    # 这里需要根据实际页面结构调整选择器
    
    # 提取简介
    detail_elem = soup.find(['div', 'section'], class_=re.compile(r'desc|detail|intro|about', re.I))
    if detail_elem:
        detail_data['detail'] = detail_elem.get_text(strip=True)
    
    # 提取地址
    address_elem = soup.find(['div', 'span'], class_=re.compile(r'address|location', re.I))
    if address_elem:
        detail_data['address'] = address_elem.get_text(strip=True)
    
    # 提取电话
    phone_elem = soup.find(text=re.compile(r'电话|Tel|Phone'))
    if phone_elem:
        phone_parent = phone_elem.find_parent(['div', 'span', 'p'])
        if phone_parent:
            detail_data['phone'] = phone_parent.get_text(strip=True)
    
    # 提取价格
    price_elem = soup.find(['span', 'div'], class_=re.compile(r'price|rate', re.I))
    if price_elem:
        detail_data['price'] = price_elem.get_text(strip=True)
    
    return detail_data


def crawl_city_hotels(city_name, city_slug=None, max_hotels=50):
    """
    爬取指定城市的酒店数据
    :param city_name: 城市名称
    :param city_slug: 城市URL slug
    :param max_hotels: 最多爬取酒店数量
    :return: 酒店列表
    """
    print(f"\n开始爬取城市: {city_name}")
    print("=" * 60)
    
    hotel_list = get_city_hotel_list(city_name, city_slug)
    
    if not hotel_list:
        print(f"未找到 {city_name} 的酒店数据")
        return []
    
    print(f"找到 {len(hotel_list)} 个酒店，开始获取详细信息...")
    
    # 获取每个酒店的详细信息
    detailed_hotels = []
    for i, hotel in enumerate(hotel_list[:max_hotels], 1):
        print(f"[{i}/{min(len(hotel_list), max_hotels)}] 处理: {hotel.get('name', 'Unknown')}")
        
        if hotel.get('url'):
            try:
                detail = get_hotel_detail(hotel['url'])
                # 合并详细信息
                hotel.update({
                    'detail': detail.get('detail', hotel.get('detail', '')),
                    'address': detail.get('address', hotel.get('address', '')),
                    'phone': detail.get('phone', hotel.get('phone', '')),
                    'price': detail.get('price', hotel.get('price', '')),
                    'hotel_type': detail.get('hotel_type', hotel.get('hotel_type', '酒店')),
                })
            except Exception as e:
                print(f"  获取详情失败: {e}")
        
        # 保存图片
        if hotel.get('cover_pic'):
            try:
                img_filename = save_img(hotel['cover_pic'], hotel['name'], 'hotel_photo')
                if img_filename:
                    hotel['cover_pic'] = img_filename
                    print(f"  保存图片成功: {img_filename}")
            except Exception as e:
                print(f"  保存图片失败: {e}")
        
        detailed_hotels.append(hotel)
        time.sleep(1)  # 延迟避免请求过快
    
    print(f"\n完成！共爬取 {len(detailed_hotels)} 个酒店")
    return detailed_hotels


def save_to_file(hotel_data, filename='hotels_qyer.json'):
    """
    保存酒店数据到文件
    :param hotel_data: 酒店数据列表或字典
    :param filename: 文件名
    """
    # 如果是列表，追加到文件（每行一个JSON）
    if isinstance(hotel_data, list):
        with open(filename, 'a', encoding='utf-8') as f:
            for hotel in hotel_data:
                f.write(json.dumps(hotel, ensure_ascii=False) + '\n')
    else:
        # 如果是字典，追加到文件
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(json.dumps(hotel_data, ensure_ascii=False) + '\n')


def main():
    """主函数"""
    print("=" * 60)
    print("开始爬取 hotel.qyer.com 的酒店数据")
    print("=" * 60)
    
    # 城市列表（可以根据需要修改）
    cities = [
        {'name': '北京', 'slug': 'beijing'},
        {'name': '上海', 'slug': 'shanghai'},
        {'name': '广州', 'slug': 'guangzhou'},
        {'name': '深圳', 'slug': 'shenzhen'},
        {'name': '杭州', 'slug': 'hangzhou'},
        {'name': '成都', 'slug': 'chengdu'},
        {'name': '西安', 'slug': 'xian'},
        {'name': '南京', 'slug': 'nanjing'},
        {'name': '厦门', 'slug': 'xiamen'},
        {'name': '三亚', 'slug': 'sanya'},
        # 可以添加更多城市
    ]
    
    output_file = os.path.join(_PROJECT_ROOT, 'offline', 'data', 'hotels_qyer_data.json')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 清空或创建文件
    if os.path.exists(output_file):
        os.remove(output_file)
    
    total_hotels = 0
    
    for city in cities:
        try:
            hotels = crawl_city_hotels(city['name'], city.get('slug'), max_hotels=30)
            if hotels:
                save_to_file(hotels, output_file)
                total_hotels += len(hotels)
                print(f"已保存 {len(hotels)} 个酒店到文件")
        except Exception as e:
            print(f"处理城市 {city['name']} 时出错: {e}")
            continue
        
        time.sleep(3)  # 城市之间延迟
    
    print("\n" + "=" * 60)
    print(f"爬取完成！")
    print(f"共爬取 {total_hotels} 个酒店")
    print(f"数据已保存到: {output_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()

