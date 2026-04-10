# -*- coding: utf-8 -*-

"""
@contact: 微信:
@file: travel_spider_data.py
@time: 2026/1/11 21:08
@author: FYY
"""
import json
import os
import time
import gzip
import urllib.request, urllib.error  # 制定url，获取网页数据

import requests as requests
from bs4 import BeautifulSoup  # 网页解析，获取数据
from fake_useragent import UserAgent  # 随机请求头

# 项目根目录（manage.py 所在目录）；travel.txt 仍在根目录供 Web「导入数据」使用
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TRAVEL_TXT = os.path.join(_PROJECT_ROOT, 'travel.txt')
_CITYS_TXT = os.path.join(_PROJECT_ROOT, 'offline', 'data', 'citys.txt')

'''
爬虫内容：
1、国家：名称、图片、去过人数
2、城市：名称、图片、去过人数、轮播图
3、景点：名称、图片、推荐指数、简介、地址、到达方式、开放时间、电话、网址
4、美食：名称、图片、推荐指数、简介、地址、到达方式、网址
5、购物：名称、图片、推荐指数、简介、到达方式
6、活动：名称、推荐指数、简介、地址、到达方式、开放时间、电话、网址
7、酒店-民宿：名称、图片、推荐指数、简介、地址、电话、价格、类型
'''


# URL的网页内容
def ask_url(url, referer=None):  # 模拟浏览器头部信息，向服务器发送消息
    count = 0
    # 使用真实的浏览器请求头，模拟Chrome浏览器
    head = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": referer if referer else "https://place.qyer.com/",
        "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Priority": "u=0, i",
        "Connection": "keep-alive",
    }  # 用户代理：表示告诉目标服务器，我们是什么类型的机器；浏览器：本质上告诉服务器，我们能够接收什么水平的内容
    time.sleep(0.5)  # 增加延迟，避免请求过快被识别为爬虫
    while count < 10:
        try:
            # 使用requests库，它会自动处理gzip解压，增加超时时间到60秒
            response = requests.get(url, headers=head, timeout=60)
            response.raise_for_status()  # 如果状态码不是200会抛出异常
            # requests会自动处理gzip解压
            html = response.text
            return html
        except requests.exceptions.Timeout as e:
            print('第{}次请求超时（Read timeout）'.format(count), url)
            time.sleep(3 + count)  # 超时后等待更长时间再重试
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print('第{}次请求报错（403 Forbidden，可能被反爬虫拦截）'.format(count), url)
                # 403错误时等待更长时间
                time.sleep(2 + count)  # 递增等待时间
            else:
                print('第{}次请求报错（HTTP {}）'.format(count, e.response.status_code), url, e)
        except Exception as e:
            print('第{}次请求报错'.format(count), url, e)
        
        # 尝试更换User-Agent，但保持其他真实请求头
        try:
            ua = UserAgent()
            random_ua = ua.random
            head["User-Agent"] = random_ua
        except:
            head["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
        count += 1
        if count < 10:
            time.sleep(1)  # 重试前等待

    return None


def save_img(url, name, path):
    # 保存图片
    filename = 'media/{}/{}.png'.format(path, name.replace('/', ''))
    
    # 确保目录存在
    dir_path = os.path.dirname(filename)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print('创建目录：{}'.format(dir_path))
    
    time.sleep(0.3)  # 增加延迟，避免请求过快
    if os.path.isfile(filename):
        # 文件已经存在
        return filename
    count = 0
    # 使用真实的浏览器请求头下载图片
    head = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://place.qyer.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "cross-site",
        "Connection": "keep-alive",
    }
    while count < 10:
        try:
            response = requests.get(url, headers=head, timeout=30)  # 对图片发送请求
            response.raise_for_status()  # 如果状态码不是200会抛出异常

            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
        except Exception as e:
            try:
                ua = UserAgent()
                random_ua = ua.random
                head = {
                    "User-Agent": random_ua,
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": "https://place.qyer.com/",
                }
            except:
                head = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Referer": "https://place.qyer.com/",
                }
            print('第{}次爬取【{}】图片出错'.format(count, name), url, e)
            time.sleep(1)  # 出错后等待更长时间
            count += 1
    return filename


def save_txt(country_city_name, data):
    # 保存为txt文件
    os.makedirs(os.path.dirname(_CITYS_TXT) or '.', exist_ok=True)
    with open(_TRAVEL_TXT, 'a', encoding='utf-8', errors='replace') as f:
        f.write(json.dumps(data, ensure_ascii=False))
        f.write('\r\n')
    with open(_CITYS_TXT, 'a', encoding='utf-8', errors='replace') as f:
        f.write(',{}'.format(country_city_name))

    print('保存成功', country_city_name)


def get_carousel_pic(name, url):
    # TODO 获取轮播图
    html = ask_url(url, referer=url)
    if not html:
        return

    soup = BeautifulSoup(html, "html.parser")
    carousel_pic = []
    if soup.find('div', class_='photo-list'):
        li_list = soup.find('div', class_='photo-list').find_all('li')
    else:
        return carousel_pic

    for i, li in enumerate(li_list):
        src = li.find('img')['data-src']
        file_name = save_img(src, '{}_carousel_{}'.format(name, i), 'city_photo')
        carousel_pic.append(file_name)
    return carousel_pic


def get_x_detail(url):
    # 获取详情：排名、简介、地址、到达方式、开放时间、电话、网址
    html = ask_url(url, referer="https://place.qyer.com/")
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    div = soup.find('div', class_='infos')
    if div:
        div_rank = div.find('li', class_='rank')
        if div_rank:
            rank = div_rank.text.replace('\n', '').replace(' ', '')  # 排名
        else:
            rank = ''
    else:
        rank = ''
    try:
        detail = soup.find('div', class_='compo-detail-info').find('div', class_='poi-detail').text  # 简介
    except:
        detail = ''
    tips = []  # 地址、到达方式、开放时间、电话、网址
    if soup.find('div', class_='compo-detail-info'):
        ul = soup.find('div', class_='compo-detail-info').find('ul', class_='poi-tips')

        for li in ul.find_all('li'):
            tips.append(li.text.replace('\n', '').replace(' ', ''))

    sight_detail = {
        'rank': rank,
        'detail': detail,
        'tips': tips
    }
    return sight_detail


def get_x(url, x_type):
    '''
    获取详情 景点：名称、图片、推荐指数、简介、地址、到达方式、开放时间、电话、网址
    :param url:
    :return:
    '''
    print(url)
    # 从URL中提取城市URL作为referer
    city_url = '/'.join(url.split('/')[:4]) + '/'
    html = ask_url(url, referer=city_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.find('ul', id='poiLists')
    if not ul:
        return []
    sight_list = []
    for li in ul.find_all('li'):
        if not li.find('h3', class_='title'):
            sight_list.append({
                'url': '',
                'name': '',
                'filename': '',
                'grade': '',
                'detail': [],
            })
            continue
        name = li.find('h3', class_='title').a.text.replace('\n', '').replace(' ', '').replace('\xa0', ' ')  # 名称
        img_src = li.find('p', class_='pics').img['src']
        if 'http' not in img_src:
            img_src = 'https:{}'.format(img_src)

        filename = save_img(img_src, name.split('\xa0')[0].split(' ')[0].split('\n')[0].split('|')[0],
                            '{}_photo'.format(x_type))  # 保存封面
        li_grade = li.find('span', class_='grade')
        if li_grade:
            grade = round(float(li_grade.text), 1)  # 推荐指数
        else:
            grade = 2
        detail_url = 'https:{}'.format(li.find('h3', class_='title').a['href'])
        detail = get_x_detail(detail_url)  # 景点详情
        sight_list.append({
            'url': detail_url,
            'name': name,
            'filename': filename,
            'grade': grade,
            'detail': detail,
        })
    return sight_list


def get_hotel_detail(url):
    # 获取酒店详情：简介、地址、电话、价格、类型
    html = ask_url(url, referer="https://place.qyer.com/")
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    
    detail = ''
    address = ''
    phone = ''
    price = ''
    hotel_type = ''
    
    # 获取简介
    try:
        detail_div = soup.find('div', class_='compo-detail-info')
        if detail_div:
            detail_p = detail_div.find('div', class_='poi-detail')
            if detail_p:
                detail = detail_p.text.strip()
    except:
        pass
    
    # 获取地址、电话等信息
    tips = []
    if soup.find('div', class_='compo-detail-info'):
        ul = soup.find('div', class_='compo-detail-info').find('ul', class_='poi-tips')
        if ul:
            for li in ul.find_all('li'):
                tip_text = li.text.replace('\n', '').replace(' ', '').strip()
                tips.append(tip_text)
                # 判断是地址、电话等
                if '地址' in tip_text or 'Address' in tip_text:
                    address = tip_text.split('：')[-1] if '：' in tip_text else tip_text.split(':')[-1]
                elif '电话' in tip_text or 'Phone' in tip_text or 'Tel' in tip_text:
                    phone = tip_text.split('：')[-1] if '：' in tip_text else tip_text.split(':')[-1]
                elif '价格' in tip_text or 'Price' in tip_text:
                    price = tip_text.split('：')[-1] if '：' in tip_text else tip_text.split(':')[-1]
    
    # 尝试从页面其他位置获取价格信息
    try:
        price_elem = soup.find('span', class_='price') or soup.find('div', class_='price')
        if price_elem:
            price = price_elem.text.strip()
    except:
        pass
    
    # 判断类型（酒店或民宿）
    try:
        type_elem = soup.find('span', class_='type') or soup.find('div', class_='hotel-type')
        if type_elem:
            hotel_type = type_elem.text.strip()
        else:
            # 从URL或标题判断
            if 'hotel' in url.lower():
                hotel_type = '酒店'
            elif 'hostel' in url.lower() or '民宿' in url.lower():
                hotel_type = '民宿'
            else:
                hotel_type = '酒店'
    except:
        hotel_type = '酒店'
    
    hotel_detail = {
        'detail': detail,
        'address': address,
        'phone': phone,
        'price': price,
        'hotel_type': hotel_type,
        'tips': tips
    }
    return hotel_detail


def get_hotel(url, x_type):
    '''
    获取酒店详情：名称、图片、推荐指数、简介、地址、电话、价格、类型
    :param url:
    :param x_type:
    :return:
    '''
    print(url)
    # 从URL中提取城市URL作为referer
    city_url = '/'.join(url.split('/')[:4]) + '/'
    html = ask_url(url, referer=city_url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.find('ul', id='poiLists')
    if not ul:
        return []
    hotel_list = []
    for li in ul.find_all('li'):
        if not li.find('h3', class_='title'):
            hotel_list.append({
                'url': '',
                'name': '',
                'filename': '',
                'grade': '',
                'detail': {},
            })
            continue
        name = li.find('h3', class_='title').a.text.replace('\n', '').replace(' ', '').replace('\xa0', ' ')  # 名称
        img_src = li.find('p', class_='pics').img['src']
        if 'http' not in img_src:
            img_src = 'https:{}'.format(img_src)

        filename = save_img(img_src, name.split('\xa0')[0].split(' ')[0].split('\n')[0].split('|')[0],
                            '{}_photo'.format(x_type))  # 保存封面
        li_grade = li.find('span', class_='grade')
        if li_grade:
            grade = round(float(li_grade.text), 1)  # 推荐指数
        else:
            grade = 2
        detail_url = 'https:{}'.format(li.find('h3', class_='title').a['href'])
        detail = get_hotel_detail(detail_url)  # 酒店详情
        hotel_list.append({
            'url': detail_url,
            'name': name,
            'filename': filename,
            'grade': grade,
            'detail': detail,
        })
    return hotel_list


def is_save(country_city_name):
    if not os.path.isfile(_CITYS_TXT):
        return True
    with open(_CITYS_TXT, 'r', encoding='utf-8', errors='replace') as f:
        city = f.read()
        if country_city_name in city:
            print('{}已存在，无须保存'.format(country_city_name))
            return False
    return True


def get_city(country_zn, country_en, url, city_count):
    '''
    获取城市:名称、图片、去过人数、轮播图、景点、美食、购物、活动
    :param url:
    :return:
    '''
    # 使用国家列表页作为referer
    country_url = '/'.join(url.split('/')[:4]) + '/citylist-0-0-1/'
    html = ask_url(url, referer=country_url)
    if not html:
        return city_count

    soup = BeautifulSoup(html, "html.parser")

    city_list = []
    # 添加空值检查，防止解析失败
    ul_citylist = soup.find('ul', class_='plcCitylist')
    if not ul_citylist:
        print('无法找到城市列表，URL:', url)
        print('页面内容预览（前500字符）:', html[:500] if html else 'None')
        return city_count
    
    li_list = ul_citylist.find_all('li')
    if not li_list:
        print('城市列表为空，URL:', url)
        return city_count
    
    country_city_name = ''
    for li in li_list:
        # 城市列表
        start_time = time.perf_counter()
        # 获取城市图片，url，保存图片，添加空值检查
        try:
            pics_elem = li.find('p', 'pics')
            if not pics_elem:
                print('跳过：无法找到pics元素')
                continue
            
            a_elem = pics_elem.find('a')
            if not a_elem or 'href' not in a_elem.attrs:
                print('跳过：无法找到城市链接')
                continue
            
            url_href = 'https:{}'.format(a_elem['href'])
            
            img_elem = a_elem.find('img')
            if not img_elem or 'src' not in img_elem.attrs:
                print('跳过：无法找到城市封面图片')
                continue
            
            cover_src = img_elem['src']
            
            title_elem = li.find('h3', class_='title')
            if not title_elem:
                print('跳过：无法找到标题元素')
                continue
            
            title_a = title_elem.find('a')
            if not title_a:
                print('跳过：无法找到标题链接')
                continue
            
            name_en = title_a.text.replace('\n', '').replace('\xa0', ' ')
            name = title_a.text.split('\xa0')[0].split(' ')[0].split('\n')[0].split('|')[0]
        except Exception as e:
            print('解析城市信息时出错，跳过该城市:', e)
            continue
        country_city_name = '{}-{}'.format(country_zn, name)
        if not city_count:
            city_count = 1
        city_count += 1
        if not is_save(country_city_name):
            continue
        print('正在爬取：', name_en)
        file_name = save_img(cover_src, name, 'city_photo')  # 保存封面
        
        # 获取去过人数，添加空值检查
        beento_elem = li.find('p', class_='beento')
        if beento_elem:
            person_count = beento_elem.text  # 统计去过的人数
        else:
            person_count = '0人去'
        # 获取封面景点
        # a_p = li.find('p', class_='pois').find_all('a')

        # cover_scenic_spots_dict = {}
        # for a in a_p:
        #     href = 'https:{}'.format(a['href'])
        #     text = a.text.replace('\n', '').replace(' ', '')
        #     cover_scenic_spots_dict[text] = href


        # 获取轮播图
        carousel_pic = get_carousel_pic(name, url_href)
        #  TODO 获取景点详情
        sight_list = get_x('{}sight/'.format(url_href), 'sight')  # 景点
        food_list = get_x('{}food/'.format(url_href), 'food')  # 美食
        shopping_list = get_x('{}shopping/'.format(url_href), 'shopping')  # 购物
        activity_list = get_x('{}activity/'.format(url_href), 'activity')  # 活动
        hotel_list = get_hotel('{}hotel/'.format(url_href), 'hotel')  # 酒店
        city_info = {
            'name': name,
            'url': url,
            'name_en': name_en,
            'cover_pic': file_name,
            'carousel_pic': carousel_pic,
            'person_count': person_count,
            'sight_list': sight_list,
            'food_list': food_list,
            'shopping_list': shopping_list,
            'activity_list': activity_list,
            'hotel_list': hotel_list,
        }

        city_list.append(city_info)
        save_txt(country_city_name, {
            'country_zn': country_zn,
            'country_en': country_en,
            'city_info': city_info,
        })
        print('用时', time.perf_counter() - start_time, '秒')
        print('已爬取{}个城市'.format(city_count))
    return city_count


def get_country(url):
    # 获取国家
    html = ask_url(url, referer="https://place.qyer.com/")
    if not html:
        print('无法获取国家信息，URL:', url)
        return None
    soup = BeautifulSoup(html, "html.parser")
    
    # 添加空值检查
    plc_top_bar = soup.find('div', class_='plcTopBarL')
    if not plc_top_bar:
        print('无法找到plcTopBarL元素，URL:', url)
        return None
    
    # 获取英文名
    p_elem = plc_top_bar.find('p')
    if not p_elem:
        print('无法找到p元素，URL:', url)
        return None
    a_elem = p_elem.find('a')
    if not a_elem:
        print('无法找到a元素（英文名），URL:', url)
        return None
    name_en = a_elem.text  # 英文名
    
    # 获取中文名
    div_elem = plc_top_bar.find('div')
    if not div_elem:
        print('无法找到div元素，URL:', url)
        return None
    a_zn_elem = div_elem.find('a')
    if not a_zn_elem:
        print('无法找到a元素（中文名），URL:', url)
        return None
    name_zn = a_zn_elem.text  # 中文名
    
    # 获取地图图片
    mapbox = soup.find('div', class_='mapbox')
    if not mapbox:
        print('无法找到mapbox元素，URL:', url)
        return None
    img_elem = mapbox.find('img')
    if not img_elem or 'src' not in img_elem.attrs:
        print('无法找到地图图片，URL:', url)
        return None
    map_src = img_elem['src']

    save_img(map_src, name_zn, 'country_photo')

    # 获取分页信息
    ui_page = soup.find('div', class_='ui_page')
    if not ui_page:
        print('无法找到分页信息，URL:', url)
        pages = 1  # 默认1页
    else:
        page_links = ui_page.find_all('a')
        if not page_links:
            pages = 1
        else:
            pages = page_links[-1].text
            if pages == '下一页':
                if len(page_links) > 1:
                    pages = page_links[-2].text
                else:
                    pages = 1
            if '...' in str(pages):
                pages = str(pages).replace('...', '')
            try:
                pages = int(pages)
            except:
                pages = 1
    
    country_dict = {
        'name_en': name_en,
        'name_zn': name_zn,
        'pages': pages
    }
    return country_dict


def main(baseurl, city_count):
    '''
    :param baseurl:
    :return:
    '''

    country_dict = get_country(baseurl)  # 获取国家
    if not country_dict:
        print('无法获取国家信息，跳过URL:', baseurl)
        return city_count

    for page in range(1, country_dict['pages'] + 1):  # 修正：range(1, pages+1)才能包含最后一页
        # 获取一页城市
        url = '{}{}/'.format(baseurl[:-2], page)
        city_count = get_city(country_dict['name_zn'], country_dict['name_en'], url, city_count)


if __name__ == '__main__':
    # 爬取的页面地址
    data = {
            # '中国': 'https://place.qyer.com/china/citylist-0-0-1/',
            # '意大利': 'https://place.qyer.com/italy/citylist-0-0-1/',
            '埃及': 'https://place.qyer.com/egypt/citylist-0-0-1/',
            '摩洛哥': 'https://place.qyer.com/morocco/citylist-0-0-1/',
            '泰国': 'https://place.qyer.com/thailand/citylist-0-0-1/',
            '马来西亚': 'https://place.qyer.com/malaysia/citylist-0-0-1/',
            }
    city_count = 0
    for name, url in data.items():
        city_count = main(url, city_count)
