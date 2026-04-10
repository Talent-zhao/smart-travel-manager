# !/usr/bin/python
# -*- coding: utf-8 -*-
import json

from django.template import Library

register = Library()


@register.filter(name="split")  # 注册一个split模板标记
def split(value, key):
    """
    Returns the value turned into a list.
    """
    return value.split(key)  # 字符串按key进行分割，值返回一个列表


@register.filter(name="to_str")  # 注册一个to_str模板标记
def to_str(value):
    """
    Returns the value turned into a list.
    """
    return str(value)  # 数字转字符串

@register.filter(name="to_list")  # 注册一个to_list模板标记
def to_list(value):
    """
    Returns the value turned into a list.
    """
    if value:
        return json.loads(value)  # 数字转字符串
    return ''


@register.filter(name="count")  # 注册一个count模板标记
def count(value):
    """
    Returns the value turned into a list.
    """
    return value.filter(is_show=True).count() # 计算数据条数

@register.filter(name="replace")  # 注册一个count模板标记
def replace(value):
    """
    Returns the value turned into a list.
    """

    return value.replace('<p>', '').replace('</p>', '') # 替换


@register.filter(name="sight_booked_by_user")
def sight_booked_by_user(sight, user_id):
    """景点详情页：是否由当前 session 用户预订（与 booking 接口、我的预订一致）"""
    return sight.is_booked_by_user(user_id)


@register.filter(name="dict_get")
def dict_get(mapping, key):
    """模板中 dict[key]，key 多为景点 id（int）。"""
    if not mapping:
        return None
    try:
        return mapping.get(int(key))
    except (TypeError, ValueError):
        return mapping.get(key)
