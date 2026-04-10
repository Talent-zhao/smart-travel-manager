# !/usr/bin/python
# -*- coding: utf-8 -*-

import xadmin
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from django.utils.safestring import mark_safe
from xadmin import views
from xadmin.views import ListAdminView
from xadmin.views.base import BaseAdminPlugin, filter_hook
from django.conf import settings
from .models import *
import threading
import sys
import os

# https://fontawesome.dashgame.com/  图标字体网站


class NavMenuSessionFixMixin(object):
    """xadmin 在 DEBUG=False 时把 nav_menu 缓存在 session；若曾写入空列表会长期只显示「无权修改」且无侧边栏。"""

    @filter_hook
    def get_context(self):
        import json

        from django.conf import settings

        req = getattr(self, 'request', None)
        if req is not None and not settings.DEBUG and hasattr(req, 'session'):
            if 'nav_menu' in req.session:
                try:
                    if not json.loads(req.session['nav_menu']):
                        del req.session['nav_menu']
                        req.session.modified = True
                except (ValueError, TypeError):
                    del req.session['nav_menu']
                    req.session.modified = True
        return super(NavMenuSessionFixMixin, self).get_context()


# 基础设置
class BaseSetting(object):
    enable_themes = True  # 使用主题
    use_bootswatch = True


# 全局设置
class GlobalSettings(object):
    site_title = '旅游景点推荐管理系统'  # 标题
    site_footer = mark_safe(settings.SITE_FOOTER)  # 页尾
    site_url = '/'
    menu_style = 'accordion'  # 设置左侧菜单  折叠样式
    
    def get_site_menu(self):
        """自定义菜单，添加一键爬取按钮"""
        try:
            return [
                {
                    'title': '数据管理',
                    'menus': (
                        {
                            'title': '一键爬取旅游信息',
                            'url': '/xadmin/spider_data/',
                            'icon': 'fa fa-spider',
                        },
                        {
                            'title': '算法管理（人脸实验）',
                            'url': '/xadmin/face_algorithm_manage/',
                            'icon': 'fa fa-flask',
                        },
                        {
                            'title': '人脸实验历史',
                            'url': '/xadmin/face_algorithm_history/',
                            'icon': 'fa fa-history',
                        },
                    )
                },
            ]
        except:
            return []


# 用户管理
class UserAdmin(object):
    search_fields = ['username', 'phone', 'name']  # 检索字段
    list_display = ['id', 'username', 'phone', 'gender', 'age', 'country']  # 要显示的字段
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    model_icon = 'fa fa-users'  # 左侧小图标
    list_editable = ['name', 'address']  # 可编辑字段
    # 控制是否显示书签功能，False表示关闭
    show_bookmarks = False


# 城市管理
class CityAdmin(object):
    search_fields = ['name']  # 检索字段
    list_display = ['id', 'name', 'name_en', 'person_count']
    ordering = ('id',)
    model_icon = 'fa fa-tags'  # 左侧小图标
    # # 控制是否显示书签功能，False表示关闭
    show_bookmarks = True
    
    def get_list_queryset(self):
        # 添加自定义按钮到列表页面
        return super().get_list_queryset()

# 景点管理
class SightAdmin(object):
    search_fields = ['name', 'city__name', 'detail']  # 检索字段
    list_display = ['id',  'name', 'grade',
                    'rank', 'like_num', 'collect_num', 'rate_num', 'all_score',
                    'is_show']  # 要显示的字段
    list_filter = ['is_show']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段，负号表示降序排序
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    model_icon = 'fa fa-book'  # 左侧小图标
    list_editable = ['is_show']  # 可编辑字段
    show_detail_fields = ['show_detail']  # 展示详情信息的字段
    # 控制列表页导出数据的可选格式，设置None来禁用数据导出功能
    list_export = ['xls', 'csv', 'json']
    # # 控制是否显示书签功能，False表示关闭
    show_bookmarks = True


    def save_models(self):
        flag = self.org_obj is None and 'create' or 'change'
        if flag == 'create':
            if self.new_obj.cover_pic.name:
                self.new_obj.cover_pic.name = f"{self.new_obj.name}.{self.new_obj.cover_pic.name.split('.')[1]}"
        if flag == 'change' and 'pic' in self.change_message():
            if self.org_obj.cover_pic.name:
                self.org_obj.cover_pic.name = f"{self.org_obj.name}.{self.org_obj.cover_pic.name.split('.')[1]}"

        super().save_models()

# 用户调查问卷管理
class QuestionnaireSightAdmin(object):
    model_icon = 'fa fa-wpforms'
    show_bookmarks = True
    search_fields = ['user__name', 'user__username']
    list_display = [
        'id', 'user', 'sight_type', 'travel_way', 'sight_way',
        'cost_min', 'cost_max', 'create_time',
    ]
    list_display_links = ('id',)
    list_filter = ['sight_type', 'travel_way', 'sight_way', 'create_time']
    ordering = ('-id',)
    list_per_page = 30
    list_editable = []
    fk_fields = ('user',)
    fields = (
        'user', 'sight_type', 'travel_way', 'sight_way',
        'cost_min', 'cost_max', 'create_time',
    )
    readonly_fields = ('create_time',)

    def has_view_permission(self, obj=None):
        return bool(self.user.is_active and self.user.is_staff)

    def has_add_permission(self):
        return bool(self.user.is_active and self.user.is_staff)

    def has_change_permission(self, obj=None):
        return bool(self.user.is_active and self.user.is_staff)

    def has_delete_permission(self, request=None, obj=None):
        return bool(self.user.is_active and self.user.is_staff)


# 景点预订管理
class BookingSightAdmin(object):
    search_fields = ['sight__name', 'user__name']  # 检索字段
    list_display = ['sight', 'user', 'create_time']  # 要显示的字段
    list_filter = ['create_time']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段，负号表示降序排序
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    list_editable = []  # 可编辑字段
    fk_fields = ('sight', 'user')  # 设置显示外键字段


# 景点评分管理
class RateAdmin(object):
    search_fields = ['sight__name', 'user__name', 'score']  # 检索字段
    list_display = ['sight', 'user', 'score', 'create_time']  # 要显示的字段
    list_filter = ['score', 'create_time']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段，负号表示降序排序
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    list_editable = []  # 可编辑字段
    fk_fields = ('sight', 'user')  # 设置显示外键字段


# 景点点赞管理
class LikeSightAdmin(object):
    search_fields = ['sight__name', 'user__name']  # 检索字段
    list_display = ['sight', 'user', 'is_delete', 'create_time']  # 要显示的字段
    list_filter = ['is_delete', 'create_time']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段，负号表示降序排序
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    list_editable = []  # 可编辑字段
    fk_fields = ('sight', 'user')  # 设置显示外键字段


# 景点收藏管理
class CollectSightAdmin(object):
    search_fields = ['sight__name', 'user__name']  # 检索字段
    list_display = ['sight', 'user', 'is_delete', 'create_time']  # 要显示的字段
    list_filter = ['is_delete', 'create_time']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段，负号表示降序排序
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    list_editable = []  # 可编辑字段
    fk_fields = ('sight', 'user')  # 设置显示外键字段


# 景点评论管理
class CommentAdmin(object):
    search_fields = ['sight__name', 'user__name', 'content']  # 检索字段
    list_display = ['user', 'sight', 'content', 'like_num', 'is_show', 'create_time']
    list_filter = ['sight', 'is_show', 'create_time']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段，负号表示降序排序
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    list_editable = []  # 可编辑字段
    fk_fields = ('sight', 'user')  # 设置显示外键字段


class CommentSightListDisplayPlugin(BaseAdminPlugin):
    def get_list_display(self, list_display):
        if getattr(self.admin_view, 'model', None) is not CommentSight:
            return list_display
        out = []
        has_content = False
        for col in list_display:
            c = 'content' if col == 'show_content' else col
            if c == 'content':
                if has_content:
                    continue
                has_content = True
            out.append(c)
        return out


# 用户是否喜欢推荐的景点
class LikeRecommendSightAdmin(object):
    search_fields = ['sight__name', 'user__name']  # 检索字段
    list_display = ['sight', 'user', 'is_like', 'reason', 'create_time']  # 要显示的字段
    list_filter = ['is_like', 'create_time']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段，负号表示降序排序
    list_per_page = 30  # 默认每页显示多少条记录，默认是100条
    list_editable = []  # 可编辑字段
    fk_fields = ('sight', 'user')  # 设置显示外键字段


# 酒店管理
class HotelAdmin(object):
    search_fields = ['name', 'city__name', 'address']  # 检索字段
    list_display = ['id', 'name', 'city', 'hotel_type', 'grade', 'price', 'address', 'phone']  # 要显示的字段
    list_filter = ['hotel_type', 'grade', 'city']  # 分组过滤的字段
    ordering = ('id',)  # 设置默认排序字段
    list_per_page = 30  # 默认每页显示多少条记录
    model_icon = 'fa fa-bed'  # 左侧小图标
    show_bookmarks = True
    fk_fields = ('city',)  # 设置显示外键字段


# 为城市管理添加导入酒店数据的操作
class CityAdminWithImport(CityAdmin):
    """扩展城市管理，添加导入酒店数据的功能"""
    
    def import_hotels_action(self, request, queryset):
        """为选中的城市导入酒店数据"""
        from travel.spiders import get_hotel
        from travel.models import Sight, Hotel
        import time
        
        total_saved = 0
        processed = 0
        
        for city in queryset:
            processed += 1
            # 从城市的景点URL中推断城市URL
            sight = Sight.objects.filter(city=city).first()
            if not sight or not sight.url:
                self.message_user(request, f"城市 {city.name} 没有景点数据，无法确定URL，跳过", 'warning')
                continue
            
            url_parts = sight.url.split('/')
            if len(url_parts) >= 4:
                city_slug = url_parts[3]
                if city_slug and city_slug != 'poi':
                    city_base_url = f"https://place.qyer.com/{city_slug}/"
                    hotel_url = f"{city_base_url}hotel/"
                    
                    try:
                        hotel_list = get_hotel(hotel_url, 'hotel')
                        
                        if not hotel_list:
                            self.message_user(request, f"城市 {city.name} 未找到酒店数据", 'warning')
                            continue
                        
                        saved_count = 0
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
                                saved_count += 1
                            except Exception as e:
                                continue
                        
                        total_saved += saved_count
                        self.message_user(request, f"城市 {city.name} 成功导入 {saved_count} 个酒店", 'success')
                        time.sleep(1)  # 延迟避免请求过快
                        
                    except Exception as e:
                        self.message_user(request, f"城市 {city.name} 导入酒店数据失败: {str(e)}", 'error')
                        continue
        
        if total_saved > 0:
            self.message_user(request, f"总共成功导入 {total_saved} 个酒店", 'success')
        else:
            self.message_user(request, "没有导入任何酒店数据", 'warning')
        
        return HttpResponseRedirect(request.get_full_path())
    
    import_hotels_action.short_description = '为选中的城市导入酒店数据'
    import_hotels_action.action_type = 1  # 批量操作
    import_hotels_action.action_icon = 'fa fa-download'
    
    actions = [import_hotels_action]


# 一键爬取旅游信息视图
class SpiderDataView(NavMenuSessionFixMixin, views.CommAdminView):
    """一键爬取所有旅游信息的自定义视图"""

    def get(self, request, *args, **kwargs):
        context = self.get_context()
        context.update(
            {
                'title': '一键爬取旅游信息',
                'has_permission': True,
            }
        )
        return render(request, 'xadmin/views/spider_data.html', context)
    
    def post(self, request):
        """执行爬虫任务"""
        try:
            # 在后台线程中运行爬虫，避免阻塞
            def run_spider():
                try:
                    # 检查必要的模块
                    missing_modules = []
                    try:
                        import bs4
                    except ImportError:
                        missing_modules.append('beautifulsoup4')
                    
                    try:
                        import requests
                    except ImportError:
                        missing_modules.append('requests')
                    
                    try:
                        import fake_useragent
                    except ImportError:
                        missing_modules.append('fake-useragent')
                    
                    if missing_modules:
                        error_msg = f'缺少必要的模块: {", ".join(missing_modules)}\n'
                        error_msg += f'请运行以下命令安装: pip install {" ".join(missing_modules)}'
                        print(error_msg)
                        return
                    
                    # 导入爬虫模块
                    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    sys.path.insert(0, BASE_DIR)
                    from travel.spiders import main
                    
                    # 爬取的页面地址
                    data = {
                        # '中国': 'https://place.qyer.com/china/citylist-0-0-1/',
                        # '意大利': 'https://place.qyer.com/italy/citylist-0-0-1/',
                        # '埃及': 'https://place.qyer.com/egypt/citylist-0-0-1/',
                        # '摩洛哥': 'https://place.qyer.com/morocco/citylist-0-0-1/',
                        # '泰国': 'https://place.qyer.com/thailand/citylist-0-0-1/',
                        '马来西亚': 'https://place.qyer.com/malaysia/citylist-0-0-1/',
                    }
                    city_count = 0
                    for name, url in data.items():
                        print(f'开始爬取 {name} 的数据...')
                        city_count = main(url, city_count)
                        print(f'{name} 数据爬取完成，已爬取 {city_count} 个城市')
                    
                    print('所有国家数据爬取完成！')
                    
                except Exception as e:
                    import traceback
                    print(f'爬虫执行错误: {e}')
                    print(traceback.format_exc())
            
            # 启动后台线程
            thread = threading.Thread(target=run_spider)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({
                'code': 0,
                'msg': '爬虫已在后台运行，结果写入项目根目录 travel.txt，完成后请使用「导入数据」入库。详见 offline/docs/开发文档.md。',
            })
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback_str = traceback.format_exc()
            
            if 'bs4' in error_msg or 'beautifulsoup4' in error_msg or 'No module named \'bs4\'' in traceback_str:
                error_msg = '缺少 beautifulsoup4，请执行：pip install beautifulsoup4 requests fake-useragent（详见 offline/docs/爬虫依赖安装.md）。'
            elif 'requests' in error_msg.lower() and 'No module named' in error_msg:
                error_msg = '缺少 requests，请执行：pip install requests（详见 offline/docs/爬虫依赖安装.md）。'
            elif 'fake_useragent' in error_msg or 'fake-useragent' in error_msg or 'fake_useragent' in traceback_str:
                error_msg = '缺少 fake-useragent，请执行：pip install fake-useragent（详见 offline/docs/爬虫依赖安装.md）。'
            else:
                error_msg = error_msg[:300]

            return JsonResponse({'code': 1, 'msg': '启动爬虫失败。' + error_msg})


class FaceAlgorithmManageView(NavMenuSessionFixMixin, views.CommAdminView):
    """Olivetti 数据集：朴素贝叶斯 / CNN 调参训练与结果对比。"""

    def get(self, request, *args, **kwargs):
        if not (request.user.is_active and request.user.is_staff):
            return HttpResponseForbidden("需要管理员登录")

        if request.GET.get("ajax") == "cnn_status":
            from travel.face_algo_status import (
                get_compare_state_for_template,
                read_cnn_job_status,
                read_cnn_training_progress,
            )

            return JsonResponse(
                {
                    "code": 0,
                    "cnn_job": read_cnn_job_status(),
                    "cnn_progress": read_cnn_training_progress(),
                    "compare": get_compare_state_for_template(),
                }
            )

        from travel.face_algo_status import (
            get_compare_state_for_template,
            read_cnn_job_status,
            read_cnn_training_progress,
        )
        from travel.face_algo_train import CNN_LIMITS, NB_LIMITS
        from travel.face_verify_lane import lane_label_cn, lane_read

        _lane = lane_read()
        context = self.get_context()
        context.update(
            {
                'title': '算法管理（人脸识别实验）',
                'has_permission': bool(request.user.is_active and request.user.is_staff),
                'compare': get_compare_state_for_template(),
                'nb_limits': NB_LIMITS,
                'cnn_limits': CNN_LIMITS,
                'cnn_job': read_cnn_job_status(),
                'cnn_progress': read_cnn_training_progress(),
                'login_lane': _lane,
                'login_lane_label': lane_label_cn(_lane),
            }
        )
        return render(request, 'xadmin/views/face_algorithm_manage.html', context)

    def post(self, request, *args, **kwargs):
        if not (request.user.is_active and request.user.is_staff):
            return JsonResponse({'code': 1, 'msg': '无权限'})

        action = request.POST.get('action', '')
        if action == 'set_login_lane':
            from travel.face_verify_lane import lane_label_cn, lane_write

            try:
                v = int(request.POST.get('lane', '0'))
            except (TypeError, ValueError):
                v = 0
            lane_write(1 if v == 1 else 0)
            return JsonResponse(
                {
                    'code': 0,
                    'msg': '识别策略已切换',
                    'lane': 1 if v == 1 else 0,
                    'lane_label': lane_label_cn(1 if v == 1 else 0),
                }
            )

        try:
            from django.conf import settings

            from travel.face_algo_status import (
                get_compare_state_for_template,
                launch_cnn_training_subprocess,
                read_cnn_job_status,
                read_cnn_training_progress,
            )
            from travel.face_algo_train import (
                normalize_cnn_params,
                normalize_nb_params,
                run_naive_bayes_training,
            )
        except Exception as e:
            return JsonResponse({'code': 1, 'msg': '加载训练模块失败: %s' % str(e)[:200]})

        if action == 'train_nb':
            params, err = normalize_nb_params(request.POST)
            if err:
                return JsonResponse({'code': 1, 'msg': err})
            r = run_naive_bayes_training(**params)
        elif action == 'train_cnn':
            params, err = normalize_cnn_params(request.POST)
            if err:
                return JsonResponse({'code': 1, 'msg': err})
            started, busy_msg = launch_cnn_training_subprocess(
                params, str(settings.BASE_DIR)
            )
            if not started:
                return JsonResponse({'code': 1, 'msg': busy_msg})
            return JsonResponse(
                {
                    'code': 0,
                    'async': True,
                    'msg': 'CNN 已在独立 Python 进程中启动（避免 PyTorch 拖垮网站进程）。请稍后「刷新状态」查看；离线日志：offline/data/face_models/cnn_worker.log',
                    'cnn_job': read_cnn_job_status(),
                    'cnn_progress': read_cnn_training_progress(),
                    'compare': get_compare_state_for_template(),
                }
            )
        else:
            # 空或无法识别的 action（预检、扩展组件等）不弹错误提示
            return JsonResponse({'code': 0, 'msg': ''})

        if not r.get('ok'):
            return JsonResponse({'code': 1, 'msg': r.get('error', '训练失败')})

        return JsonResponse(
            {
                'code': 0,
                'msg': '训练完成并已保存模型。',
                'result': r,
                'compare': get_compare_state_for_template(),
            }
        )


class FaceAlgorithmHistoryView(NavMenuSessionFixMixin, views.CommAdminView):
    """人脸算法实验历史：每次成功训练后自动落盘参数与指标。"""

    def get(self, request, *args, **kwargs):
        if not (request.user.is_active and request.user.is_staff):
            return HttpResponseForbidden("需要管理员登录")

        import json

        from travel.face_algo_status import MAX_EXPERIMENT_HISTORY, load_experiment_history

        labels = {
            "naive_bayes": "朴素贝叶斯（PCA+GaussianNB）",
            "cnn": "CNN（PyTorch）",
        }
        raw = load_experiment_history()
        history_rows = []
        for i, r in enumerate(raw):
            alg = r.get("algorithm") or ""
            m = r.get("metrics") or {}
            history_rows.append(
                {
                    "n": i + 1,
                    "saved_at": r.get("saved_at") or "",
                    "algorithm": alg,
                    "algorithm_label": labels.get(alg, alg or "—"),
                    "acc": m.get("test_accuracy"),
                    "f1": m.get("macro_f1"),
                    "sec": m.get("train_seconds"),
                    "best_val": m.get("best_val_accuracy"),
                    "params_json": json.dumps(
                        r.get("params") or {},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "metrics_json": json.dumps(m, ensure_ascii=False, indent=2),
                }
            )

        context = self.get_context()
        context.update(
            {
                "title": "人脸实验历史",
                "has_permission": True,
                "history_rows": history_rows,
                "history_rel_path": "offline/data/face_models/algorithm_experiment_history.json",
                "max_keep": MAX_EXPERIMENT_HISTORY,
            }
        )
        return render(request, "xadmin/views/face_algorithm_history.html", context)


# 注册自定义视图 - 一键爬取旅游信息
xadmin.site.register_view(r'^spider_data/$', SpiderDataView, name='spider_data')
xadmin.site.register_view(
    r'^face_algorithm_manage/$', FaceAlgorithmManageView, name='face_algorithm_manage'
)

xadmin.site.register(views.CommAdminView, GlobalSettings)
xadmin.site.register(views.BaseAdminView, BaseSetting)
xadmin.site.register(User, UserAdmin)
xadmin.site.register(City, CityAdminWithImport)  # 使用扩展的城市管理
xadmin.site.register(Sight, SightAdmin)
xadmin.site.register(QuestionnaireSight, QuestionnaireSightAdmin)
xadmin.site.register(BookingSight, BookingSightAdmin)
xadmin.site.register(RateSight, RateAdmin)
xadmin.site.register(LikeSight, LikeSightAdmin)
xadmin.site.register(CollectSight, CollectSightAdmin)
xadmin.site.register_plugin(CommentSightListDisplayPlugin, ListAdminView)
xadmin.site.register(CommentSight, CommentAdmin)
xadmin.site.register(LikeRecommendSight, LikeRecommendSightAdmin)
xadmin.site.register(Hotel, HotelAdmin)  # 注册酒店管理

# 美食管理
class FoodAdmin(object):
    search_fields = ['name', 'city__name', 'detail']
    list_display = ['id', 'name', 'city', 'grade', 'like_num', 'collect_num', 'is_show']
    list_filter = ['is_show', 'city']
    ordering = ('id',)
    list_per_page = 30
    model_icon = 'fa fa-cutlery'
    fk_fields = ('city',)

# 购物管理
class ShoppingAdmin(object):
    search_fields = ['name', 'city__name', 'detail']
    list_display = ['id', 'name', 'city', 'grade', 'like_num', 'collect_num', 'is_show']
    list_filter = ['is_show', 'city']
    ordering = ('id',)
    list_per_page = 30
    model_icon = 'fa fa-shopping-cart'
    fk_fields = ('city',)

# 活动管理
class ActivityAdmin(object):
    search_fields = ['name', 'city__name', 'detail']
    list_display = ['id', 'name', 'city', 'grade', 'like_num', 'collect_num', 'is_show']
    list_filter = ['is_show', 'city']
    ordering = ('id',)
    list_per_page = 30
    model_icon = 'fa fa-calendar'
    fk_fields = ('city',)

xadmin.site.register(Food, FoodAdmin)
xadmin.site.register(Shopping, ShoppingAdmin)
xadmin.site.register(Activity, ActivityAdmin)
