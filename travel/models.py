from django.db import models


# 用户
GENDER = ((0, '男'), (1, '女'))

# 证件类型
ID_TYPE = (
    ('身份证', '身份证'),
    ('护照', '护照'),
    ('港澳通行证', '港澳通行证'),
    ('台胞证', '台胞证'),
    ('其他', '其他'),
)

# 全球国家和地区列表（包含主要国家和地区）
COUNTRIES = (
    ('中国', '中国 (China)'),
    ('美国', '美国 (United States)'),
    ('日本', '日本 (Japan)'),
    ('韩国', '韩国 (South Korea)'),
    ('英国', '英国 (United Kingdom)'),
    ('法国', '法国 (France)'),
    ('德国', '德国 (Germany)'),
    ('意大利', '意大利 (Italy)'),
    ('西班牙', '西班牙 (Spain)'),
    ('俄罗斯', '俄罗斯 (Russia)'),
    ('加拿大', '加拿大 (Canada)'),
    ('澳大利亚', '澳大利亚 (Australia)'),
    ('新西兰', '新西兰 (New Zealand)'),
    ('印度', '印度 (India)'),
    ('巴西', '巴西 (Brazil)'),
    ('阿根廷', '阿根廷 (Argentina)'),
    ('墨西哥', '墨西哥 (Mexico)'),
    ('泰国', '泰国 (Thailand)'),
    ('新加坡', '新加坡 (Singapore)'),
    ('马来西亚', '马来西亚 (Malaysia)'),
    ('印度尼西亚', '印度尼西亚 (Indonesia)'),
    ('菲律宾', '菲律宾 (Philippines)'),
    ('越南', '越南 (Vietnam)'),
    ('缅甸', '缅甸 (Myanmar)'),
    ('柬埔寨', '柬埔寨 (Cambodia)'),
    ('老挝', '老挝 (Laos)'),
    ('文莱', '文莱 (Brunei)'),
    ('东帝汶', '东帝汶 (Timor-Leste)'),
    ('蒙古', '蒙古 (Mongolia)'),
    ('朝鲜', '朝鲜 (North Korea)'),
    ('阿富汗', '阿富汗 (Afghanistan)'),
    ('巴基斯坦', '巴基斯坦 (Pakistan)'),
    ('孟加拉国', '孟加拉国 (Bangladesh)'),
    ('斯里兰卡', '斯里兰卡 (Sri Lanka)'),
    ('尼泊尔', '尼泊尔 (Nepal)'),
    ('不丹', '不丹 (Bhutan)'),
    ('马尔代夫', '马尔代夫 (Maldives)'),
    ('伊朗', '伊朗 (Iran)'),
    ('伊拉克', '伊拉克 (Iraq)'),
    ('沙特阿拉伯', '沙特阿拉伯 (Saudi Arabia)'),
    ('阿联酋', '阿联酋 (United Arab Emirates)'),
    ('卡塔尔', '卡塔尔 (Qatar)'),
    ('科威特', '科威特 (Kuwait)'),
    ('巴林', '巴林 (Bahrain)'),
    ('阿曼', '阿曼 (Oman)'),
    ('也门', '也门 (Yemen)'),
    ('约旦', '约旦 (Jordan)'),
    ('黎巴嫩', '黎巴嫩 (Lebanon)'),
    ('叙利亚', '叙利亚 (Syria)'),
    ('以色列', '以色列 (Israel)'),
    ('巴勒斯坦', '巴勒斯坦 (Palestine)'),
    ('土耳其', '土耳其 (Turkey)'),
    ('塞浦路斯', '塞浦路斯 (Cyprus)'),
    ('格鲁吉亚', '格鲁吉亚 (Georgia)'),
    ('亚美尼亚', '亚美尼亚 (Armenia)'),
    ('阿塞拜疆', '阿塞拜疆 (Azerbaijan)'),
    ('哈萨克斯坦', '哈萨克斯坦 (Kazakhstan)'),
    ('乌兹别克斯坦', '乌兹别克斯坦 (Uzbekistan)'),
    ('土库曼斯坦', '土库曼斯坦 (Turkmenistan)'),
    ('塔吉克斯坦', '塔吉克斯坦 (Tajikistan)'),
    ('吉尔吉斯斯坦', '吉尔吉斯斯坦 (Kyrgyzstan)'),
    ('波兰', '波兰 (Poland)'),
    ('捷克', '捷克 (Czech Republic)'),
    ('斯洛伐克', '斯洛伐克 (Slovakia)'),
    ('匈牙利', '匈牙利 (Hungary)'),
    ('罗马尼亚', '罗马尼亚 (Romania)'),
    ('保加利亚', '保加利亚 (Bulgaria)'),
    ('希腊', '希腊 (Greece)'),
    ('克罗地亚', '克罗地亚 (Croatia)'),
    ('塞尔维亚', '塞尔维亚 (Serbia)'),
    ('波黑', '波黑 (Bosnia and Herzegovina)'),
    ('斯洛文尼亚', '斯洛文尼亚 (Slovenia)'),
    ('阿尔巴尼亚', '阿尔巴尼亚 (Albania)'),
    ('北马其顿', '北马其顿 (North Macedonia)'),
    ('黑山', '黑山 (Montenegro)'),
    ('科索沃', '科索沃 (Kosovo)'),
    ('乌克兰', '乌克兰 (Ukraine)'),
    ('白俄罗斯', '白俄罗斯 (Belarus)'),
    ('摩尔多瓦', '摩尔多瓦 (Moldova)'),
    ('立陶宛', '立陶宛 (Lithuania)'),
    ('拉脱维亚', '拉脱维亚 (Latvia)'),
    ('爱沙尼亚', '爱沙尼亚 (Estonia)'),
    ('芬兰', '芬兰 (Finland)'),
    ('瑞典', '瑞典 (Sweden)'),
    ('挪威', '挪威 (Norway)'),
    ('丹麦', '丹麦 (Denmark)'),
    ('冰岛', '冰岛 (Iceland)'),
    ('爱尔兰', '爱尔兰 (Ireland)'),
    ('荷兰', '荷兰 (Netherlands)'),
    ('比利时', '比利时 (Belgium)'),
    ('卢森堡', '卢森堡 (Luxembourg)'),
    ('瑞士', '瑞士 (Switzerland)'),
    ('奥地利', '奥地利 (Austria)'),
    ('葡萄牙', '葡萄牙 (Portugal)'),
    ('摩纳哥', '摩纳哥 (Monaco)'),
    ('列支敦士登', '列支敦士登 (Liechtenstein)'),
    ('圣马力诺', '圣马力诺 (San Marino)'),
    ('梵蒂冈', '梵蒂冈 (Vatican City)'),
    ('马耳他', '马耳他 (Malta)'),
    ('安道尔', '安道尔 (Andorra)'),
    ('埃及', '埃及 (Egypt)'),
    ('利比亚', '利比亚 (Libya)'),
    ('突尼斯', '突尼斯 (Tunisia)'),
    ('阿尔及利亚', '阿尔及利亚 (Algeria)'),
    ('摩洛哥', '摩洛哥 (Morocco)'),
    ('苏丹', '苏丹 (Sudan)'),
    ('南苏丹', '南苏丹 (South Sudan)'),
    ('埃塞俄比亚', '埃塞俄比亚 (Ethiopia)'),
    ('肯尼亚', '肯尼亚 (Kenya)'),
    ('坦桑尼亚', '坦桑尼亚 (Tanzania)'),
    ('乌干达', '乌干达 (Uganda)'),
    ('卢旺达', '卢旺达 (Rwanda)'),
    ('加纳', '加纳 (Ghana)'),
    ('尼日利亚', '尼日利亚 (Nigeria)'),
    ('南非', '南非 (South Africa)'),
    ('马达加斯加', '马达加斯加 (Madagascar)'),
    ('毛里求斯', '毛里求斯 (Mauritius)'),
    ('塞舌尔', '塞舌尔 (Seychelles)'),
    ('智利', '智利 (Chile)'),
    ('秘鲁', '秘鲁 (Peru)'),
    ('哥伦比亚', '哥伦比亚 (Colombia)'),
    ('委内瑞拉', '委内瑞拉 (Venezuela)'),
    ('厄瓜多尔', '厄瓜多尔 (Ecuador)'),
    ('玻利维亚', '玻利维亚 (Bolivia)'),
    ('巴拉圭', '巴拉圭 (Paraguay)'),
    ('乌拉圭', '乌拉圭 (Uruguay)'),
    ('圭亚那', '圭亚那 (Guyana)'),
    ('苏里南', '苏里南 (Suriname)'),
    ('法属圭亚那', '法属圭亚那 (French Guiana)'),
    ('古巴', '古巴 (Cuba)'),
    ('牙买加', '牙买加 (Jamaica)'),
    ('海地', '海地 (Haiti)'),
    ('多米尼加', '多米尼加 (Dominican Republic)'),
    ('波多黎各', '波多黎各 (Puerto Rico)'),
    ('巴哈马', '巴哈马 (Bahamas)'),
    ('巴巴多斯', '巴巴多斯 (Barbados)'),
    ('特立尼达和多巴哥', '特立尼达和多巴哥 (Trinidad and Tobago)'),
    ('哥斯达黎加', '哥斯达黎加 (Costa Rica)'),
    ('巴拿马', '巴拿马 (Panama)'),
    ('尼加拉瓜', '尼加拉瓜 (Nicaragua)'),
    ('洪都拉斯', '洪都拉斯 (Honduras)'),
    ('危地马拉', '危地马拉 (Guatemala)'),
    ('伯利兹', '伯利兹 (Belize)'),
    ('萨尔瓦多', '萨尔瓦多 (El Salvador)'),
    ('斐济', '斐济 (Fiji)'),
    ('巴布亚新几内亚', '巴布亚新几内亚 (Papua New Guinea)'),
    ('所罗门群岛', '所罗门群岛 (Solomon Islands)'),
    ('瓦努阿图', '瓦努阿图 (Vanuatu)'),
    ('新喀里多尼亚', '新喀里多尼亚 (New Caledonia)'),
    ('法属波利尼西亚', '法属波利尼西亚 (French Polynesia)'),
    ('关岛', '关岛 (Guam)'),
    ('北马里亚纳群岛', '北马里亚纳群岛 (Northern Mariana Islands)'),
    ('美属萨摩亚', '美属萨摩亚 (American Samoa)'),
    ('库克群岛', '库克群岛 (Cook Islands)'),
    ('汤加', '汤加 (Tonga)'),
    ('萨摩亚', '萨摩亚 (Samoa)'),
    ('密克罗尼西亚', '密克罗尼西亚 (Micronesia)'),
    ('马绍尔群岛', '马绍尔群岛 (Marshall Islands)'),
    ('帕劳', '帕劳 (Palau)'),
    ('基里巴斯', '基里巴斯 (Kiribati)'),
    ('图瓦卢', '图瓦卢 (Tuvalu)'),
    ('瑙鲁', '瑙鲁 (Nauru)'),
    ('其他', '其他 (Other)'),
    )


class User(models.Model):
    username = models.CharField(max_length=32, unique=True, verbose_name='账号')
    password = models.CharField(max_length=32, verbose_name='密码')
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='姓名')  # 保留用于向后兼容
    first_name = models.CharField(max_length=128, null=True, blank=True, verbose_name='姓氏')
    last_name = models.CharField(max_length=128, null=True, blank=True, verbose_name='名字')
    gender = models.BooleanField(default=0, choices=GENDER, verbose_name='性别')
    age = models.IntegerField(verbose_name='年龄', default=20)
    phone = models.CharField(max_length=32, verbose_name='手机号码')
    country = models.CharField(max_length=64, verbose_name='国籍', default='中国', choices=COUNTRIES)
    address = models.CharField(max_length=32, verbose_name='地址')
    email = models.EmailField(max_length=32, null=True, blank=True, verbose_name='邮箱')
    icon = models.ImageField(upload_to='user_icon', default=r'user_icon/default_icon.jpeg', null=True, blank=True, verbose_name='头像')

    # 证件信息
    id_type = models.CharField(max_length=32, null=True, blank=True, choices=ID_TYPE, verbose_name='证件类型')
    id_number = models.CharField(max_length=64, null=True, blank=True, verbose_name='证件号')
    id_expiry_date = models.DateField(null=True, blank=True, verbose_name='证件有效期')

    # 人脸识别特征向量（face_recognition.face_encodings 的 128 维数组，JSON 序列化后存储）
    icon_feature = models.TextField(null=True, blank=True, default=None, verbose_name='人脸特征')
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        db_table = 'user'
        verbose_name = '用户管理'
        verbose_name_plural = '用户管理'

    def __str__(self):
        return self.username


# 国家
class Country(models.Model):
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='名称')
    name_en = models.CharField(max_length=256, null=True, blank=True, verbose_name='英文名称')
    photo = models.ImageField(upload_to='country_photo', null=True, blank=True, verbose_name='封面')
    travel_num = models.IntegerField(default=0, verbose_name='去过人数')

    class Meta:
        db_table = 'country'
        verbose_name_plural = '国家'
        verbose_name = '国家'

    def __str__(self):
        return self.name


# 城市
class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, blank=True, null=True, verbose_name='国家')
    url = models.TextField(null=True, blank=True, verbose_name='链接')
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='名称')
    name_en = models.CharField(max_length=256, null=True, blank=True, verbose_name='带英文名称')
    cover_pic = models.ImageField(upload_to='city_photo', null=True, blank=True, verbose_name='封面')
    person_count = models.IntegerField(default=0, verbose_name='去过人数')

    class Meta:
        db_table = 'city'
        verbose_name = '城市管理'
        verbose_name_plural = '城市管理'

    def __str__(self):
        return self.name

    def sight(self):
        return ' '.join([s['name'].split(' ')[0] for s in Sight.objects.filter(city=self).values('name')][:8])

    def get_like_num(self):
        like_num = 0
        for s in Sight.objects.filter(city=self).values('like_num'):
            like_num += s['like_num']
        return like_num

    def get_collect_num(self):
        collect_num = 0
        for s in Sight.objects.filter(city=self).values('collect_num'):
            collect_num += s['collect_num']
        return collect_num
    def get_look_num(self):
        look_num = 0
        for s in Sight.objects.filter(city=self).values('look_num'):
            look_num += s['look_num']
        return look_num


# 轮播图
class Carousel(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True, verbose_name='城市')
    photo = models.ImageField(upload_to='city_photo', null=True, blank=True, verbose_name='图片')

    class Meta:
        db_table = 'carousel'
        verbose_name_plural = '轮播图'
        verbose_name = '轮播图'

    def __str__(self):
        return self.city


# 景点：城市、链接、名称、图片、排名、简介、提示（地址、到达方式、开放时间、电话、网址）
class Sight(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True, verbose_name='城市')
    url = models.TextField(null=True, blank=True, verbose_name='链接')
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='名称')
    cover_pic = models.ImageField(upload_to='sight_photo', null=True, blank=True, verbose_name='封面')
    grade = models.FloatField(default=0, verbose_name='推荐指数')
    rank = models.TextField(null=True, blank=True, verbose_name='排名')
    detail = models.TextField(null=True, blank=True, verbose_name='简介')
    tips = models.TextField(null=True, blank=True, verbose_name='提示')
    collect_num = models.IntegerField(verbose_name='收藏人数', default=0)
    rate_num = models.IntegerField(verbose_name='评分人数', default=0)
    all_score = models.FloatField(default=0, verbose_name='平均评分')
    like_num = models.IntegerField(verbose_name='点赞人数', default=0)
    look_num = models.IntegerField(verbose_name='浏览量', default=0)
    is_show = models.BooleanField(default=True, verbose_name='是否显示')


    class Meta:
        db_table = 'sight'
        verbose_name = '景点管理'
        verbose_name_plural = '景点管理'

    def __str__(self):
        return self.name

    def is_booked_by_user(self, user_id):
        """当前登录用户是否已预订该景点（勿用全站任意用户预订判断，否则会与「我的预订」不一致）"""
        if user_id is None:
            return False
        return BookingSight.objects.filter(sight=self, user_id=user_id).exists()

# 评分
class RateSight(models.Model):
    sight = models.ForeignKey(Sight, related_name='rate_sight', on_delete=models.CASCADE, blank=True, null=True, verbose_name='景点')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    score = models.FloatField(verbose_name='评分')
    create_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        db_table = 'rate_sight'
        verbose_name = '评分管理'
        verbose_name_plural = '评分管理'


# 点赞
class LikeSight(models.Model):
    sight = models.ForeignKey(Sight, on_delete=models.CASCADE, related_name='like_sight', blank=True, null=True, verbose_name='景点')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    is_delete = models.BooleanField(default=False, verbose_name='是否取消')
    create_time = models.DateTimeField(verbose_name='点赞时间', auto_now_add=True)

    class Meta:
        db_table = 'like_sight'
        verbose_name = '点赞管理'
        verbose_name_plural = '点赞管理'


# 用户收藏表
class CollectSight(models.Model):
    sight = models.ForeignKey(Sight, on_delete=models.CASCADE, related_name='collect_sight',
                              blank=True, null=True, verbose_name='景点')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    is_delete = models.BooleanField(default=False, verbose_name='是否取消')
    create_time = models.DateTimeField(verbose_name='收藏时间', auto_now_add=True)

    class Meta:
        db_table = 'collect_sight'
        verbose_name = '收藏管理'
        verbose_name_plural = '收藏管理'


# 用户评论表
class CommentSight(models.Model):
    sight = models.ForeignKey(Sight, on_delete=models.CASCADE, blank=True, null=True, verbose_name='景点')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    content = models.TextField(verbose_name='评论内容')
    create_time = models.DateTimeField(verbose_name='评论时间', auto_now_add=True)
    like_num = models.IntegerField(verbose_name='点赞数', default=0)
    like_users = models.TextField(null=True, blank=True, default=None, verbose_name='点赞用户id列表')
    is_show = models.BooleanField(default=True, verbose_name='是否显示')

    class Meta:
        db_table = 'comment_sight'
        verbose_name = '评论管理'
        verbose_name_plural = '评论管理'


# 预订出行
class BookingSight(models.Model):
    sight = models.ForeignKey(Sight, on_delete=models.CASCADE, related_name='booking_sight',
                              blank=True, null=True, verbose_name='景点')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    create_time = models.DateTimeField(verbose_name='预订时间', auto_now_add=True)

    class Meta:
        db_table = 'booking_sight'
        verbose_name = '预订管理'
        verbose_name_plural = '预订管理'


# 用户调查问卷：目标旅行地点、旅行类型（文化、冒险、自然等）、预算范围、出行方式偏好（独自旅行、与家人、与朋友等）
# 旅行类型
SightType = (('0', '文化类'),
            ('1', '自然类'),
            ('2', '冒险类'),
            ('3', '古城类'),
            ('4', '村落类'),
            )

TravelWay = (('0', '单人行'),
            ('1', '与家人'),
            ('2', '与朋友'),
            ('3', '与搭子'),
            )

SightWay = (('0', '自驾去'),
            ('1', '包车去'),
            ('2', '徒步去'),
            ('3', '跟团去')
            )

# 用户调查问卷
class QuestionnaireSight(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    sight_type = models.CharField(max_length=20, choices=SightType, default='0', verbose_name='景点类型')
    cost_min = models.IntegerField(default=1, verbose_name='最低预算')
    cost_max = models.IntegerField(default=10, verbose_name='最高预算')
    travel_way = models.CharField(max_length=20, choices=TravelWay, default='0', verbose_name='出行方式')
    sight_way = models.CharField(max_length=20, choices=SightWay, default='0', verbose_name='旅行方式')
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        db_table = 'questionnaire_sight'
        verbose_name = '用户调查问卷管理'
        verbose_name_plural = '用户调查问卷管理'


# 用户对推荐列表的反馈
class LikeRecommendSight(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    sight = models.ForeignKey(Sight, on_delete=models.CASCADE, blank=True, null=True, verbose_name='景点')
    is_like = models.BooleanField(default=True, verbose_name='是否喜欢')
    reason = models.TextField(null=True, blank=True, default=None, verbose_name='原因')
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        db_table = 'like_recommend_sight'
        verbose_name = '用户是否喜欢推荐的景点管理'
        verbose_name_plural = '用户是否喜欢推荐的景点管理'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'sight'),
                name='uniq_likerecommend_user_sight',
            ),
        ]


# 美食：城市、链接、名称、图片、推荐指数、简介、地址、到达方式、网址
class Food(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True, verbose_name='城市')
    url = models.TextField(null=True, blank=True, verbose_name='链接')
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='名称')
    cover_pic = models.ImageField(upload_to='food_photo', null=True, blank=True, verbose_name='封面')
    grade = models.FloatField(default=0, verbose_name='推荐指数')
    rank = models.TextField(null=True, blank=True, verbose_name='排名')
    detail = models.TextField(null=True, blank=True, verbose_name='简介')
    tips = models.TextField(null=True, blank=True, verbose_name='提示')
    collect_num = models.IntegerField(verbose_name='收藏人数', default=0)
    rate_num = models.IntegerField(verbose_name='评分人数', default=0)
    all_score = models.FloatField(default=0, verbose_name='平均评分')
    like_num = models.IntegerField(verbose_name='点赞人数', default=0)
    look_num = models.IntegerField(verbose_name='浏览量', default=0)
    is_show = models.BooleanField(default=True, verbose_name='是否显示')

    class Meta:
        db_table = 'food'
        verbose_name = '美食管理'
        verbose_name_plural = '美食管理'

    def __str__(self):
        return self.name


# 购物：城市、链接、名称、图片、推荐指数、简介、到达方式
class Shopping(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True, verbose_name='城市')
    url = models.TextField(null=True, blank=True, verbose_name='链接')
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='名称')
    cover_pic = models.ImageField(upload_to='shopping_photo', null=True, blank=True, verbose_name='封面')
    grade = models.FloatField(default=0, verbose_name='推荐指数')
    rank = models.TextField(null=True, blank=True, verbose_name='排名')
    detail = models.TextField(null=True, blank=True, verbose_name='简介')
    tips = models.TextField(null=True, blank=True, verbose_name='提示')
    collect_num = models.IntegerField(verbose_name='收藏人数', default=0)
    rate_num = models.IntegerField(verbose_name='评分人数', default=0)
    all_score = models.FloatField(default=0, verbose_name='平均评分')
    like_num = models.IntegerField(verbose_name='点赞人数', default=0)
    look_num = models.IntegerField(verbose_name='浏览量', default=0)
    is_show = models.BooleanField(default=True, verbose_name='是否显示')

    class Meta:
        db_table = 'shopping'
        verbose_name = '购物管理'
        verbose_name_plural = '购物管理'

    def __str__(self):
        return self.name


# 活动：城市、链接、名称、推荐指数、简介、地址、到达方式、开放时间、电话、网址
class Activity(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True, verbose_name='城市')
    url = models.TextField(null=True, blank=True, verbose_name='链接')
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='名称')
    cover_pic = models.ImageField(upload_to='activity_photo', null=True, blank=True, verbose_name='封面')
    grade = models.FloatField(default=0, verbose_name='推荐指数')
    rank = models.TextField(null=True, blank=True, verbose_name='排名')
    detail = models.TextField(null=True, blank=True, verbose_name='简介')
    tips = models.TextField(null=True, blank=True, verbose_name='提示')
    collect_num = models.IntegerField(verbose_name='收藏人数', default=0)
    rate_num = models.IntegerField(verbose_name='评分人数', default=0)
    all_score = models.FloatField(default=0, verbose_name='平均评分')
    like_num = models.IntegerField(verbose_name='点赞人数', default=0)
    look_num = models.IntegerField(verbose_name='浏览量', default=0)
    is_show = models.BooleanField(default=True, verbose_name='是否显示')

    class Meta:
        db_table = 'activity'
        verbose_name = '活动管理'
        verbose_name_plural = '活动管理'

    def __str__(self):
        return self.name


# 搜索关键字
class SearchKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    key = models.TextField(verbose_name='搜索关键字', null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        db_table = 'search_key'
        verbose_name = '用户搜索关键字'
        verbose_name_plural = verbose_name


# 酒店-民宿：城市、链接、名称、图片、推荐指数、简介、地址、电话、价格、类型
class Hotel(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True, verbose_name='城市')
    url = models.TextField(null=True, blank=True, verbose_name='链接')
    name = models.CharField(max_length=256, null=True, blank=True, verbose_name='名称')
    cover_pic = models.ImageField(upload_to='hotel_photo', null=True, blank=True, verbose_name='封面')
    grade = models.FloatField(default=0, verbose_name='推荐指数')
    detail = models.TextField(null=True, blank=True, verbose_name='简介')
    address = models.TextField(null=True, blank=True, verbose_name='地址')
    phone = models.CharField(max_length=128, null=True, blank=True, verbose_name='电话')
    price = models.CharField(max_length=128, null=True, blank=True, verbose_name='价格')
    hotel_type = models.CharField(max_length=64, null=True, blank=True, verbose_name='类型')  # 酒店/民宿
    collect_num = models.IntegerField(verbose_name='收藏人数', default=0)
    rate_num = models.IntegerField(verbose_name='评分人数', default=0)
    all_score = models.FloatField(default=0, verbose_name='平均评分')
    like_num = models.IntegerField(verbose_name='点赞人数', default=0)
    look_num = models.IntegerField(verbose_name='浏览量', default=0)
    is_show = models.BooleanField(default=True, verbose_name='是否显示')

    class Meta:
        db_table = 'hotel'
        verbose_name = '酒店-民宿管理'
        verbose_name_plural = '酒店-民宿管理'

    def __str__(self):
        return self.name

    def is_booked_by_user(self, user_id):
        if user_id is None:
            return False
        return BookingHotel.objects.filter(hotel=self, user_id=user_id).exists()


# 酒店评分
class RateHotel(models.Model):
    hotel = models.ForeignKey(Hotel, related_name='rate_hotel', on_delete=models.CASCADE, blank=True, null=True, verbose_name='酒店')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    score = models.FloatField(verbose_name='评分')
    create_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        db_table = 'rate_hotel'
        verbose_name = '酒店评分表'
        verbose_name_plural = '酒店评分表'


# 酒店点赞
class LikeHotel(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='like_hotel', blank=True, null=True, verbose_name='酒店')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    is_delete = models.BooleanField(default=False, verbose_name='是否取消')
    create_time = models.DateTimeField(verbose_name='点赞时间', auto_now_add=True)

    class Meta:
        db_table = 'like_hotel'
        verbose_name = '酒店点赞表'
        verbose_name_plural = '酒店点赞表'


# 酒店收藏表
class CollectHotel(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='collect_hotel',
                              blank=True, null=True, verbose_name='酒店')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    is_delete = models.BooleanField(default=False, verbose_name='是否取消')
    create_time = models.DateTimeField(verbose_name='收藏时间', auto_now_add=True)

    class Meta:
        db_table = 'collect_hotel'
        verbose_name = '酒店收藏表'
        verbose_name_plural = '酒店收藏表'


# 酒店评论表
class CommentHotel(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, blank=True, null=True, verbose_name='酒店')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    content = models.TextField(verbose_name='评论内容')
    create_time = models.DateTimeField(verbose_name='评论时间', auto_now_add=True)
    like_num = models.IntegerField(verbose_name='点赞数', default=0)
    like_users = models.TextField(null=True, blank=True, default=None, verbose_name='点赞用户id列表')
    is_show = models.BooleanField(default=True, verbose_name='是否显示')

    class Meta:
        db_table = 'comment_hotel'
        verbose_name = '酒店评论表'
        verbose_name_plural = '酒店评论表'


# 酒店预订表
class BookingHotel(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='booking_hotel',
                              blank=True, null=True, verbose_name='酒店')
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='用户')
    check_in = models.DateField(null=True, blank=True, verbose_name='入住日期')
    check_out = models.DateField(null=True, blank=True, verbose_name='退房日期')
    guest_name = models.CharField(max_length=128, null=True, blank=True, verbose_name='入住人姓名')
    guest_phone = models.CharField(max_length=32, null=True, blank=True, verbose_name='联系电话')
    remark = models.TextField(null=True, blank=True, verbose_name='备注')
    create_time = models.DateTimeField(verbose_name='预订时间', auto_now_add=True)

    class Meta:
        db_table = 'booking_hotel'
        verbose_name = '酒店预订表'
        verbose_name_plural = '酒店预订表'