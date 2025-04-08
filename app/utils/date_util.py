#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日期工具模块
提供日期格式化和日期计算功能
"""

import datetime
from typing import Optional, Union


def format_date(date_obj: Optional[Union[datetime.datetime, datetime.date]],
                format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[str]:
    """
    格式化日期对象为字符串
    
    Args:
        date_obj: 日期对象
        format_str: 日期格式化字符串
        
    Returns:
        str: 格式化后的日期字符串，如果date_obj为None则返回None
    """
    if date_obj is None:
        return None
        
    return date_obj.strftime(format_str)


def parse_date(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime.datetime]:
    """
    解析日期字符串为日期对象
    
    Args:
        date_str: 日期字符串
        format_str: 日期格式化字符串
        
    Returns:
        datetime: 解析后的日期对象，解析失败则返回None
    """
    try:
        return datetime.datetime.strptime(date_str, format_str)
    except ValueError:
        return None


def add_days(date_obj: Union[datetime.datetime, datetime.date], days: int) -> datetime.datetime:
    """
    日期加上指定天数
    
    Args:
        date_obj: 日期对象
        days: 要添加的天数
        
    Returns:
        datetime: 计算后的日期对象
    """
    if isinstance(date_obj, datetime.date) and not isinstance(date_obj, datetime.datetime):
        date_obj = datetime.datetime.combine(date_obj, datetime.time())
        
    return date_obj + datetime.timedelta(days=days)


def add_months(date_obj: Union[datetime.datetime, datetime.date], months: int) -> datetime.datetime:
    """
    日期加上指定月数
    
    Args:
        date_obj: 日期对象
        months: 要添加的月数
        
    Returns:
        datetime: 计算后的日期对象
    """
    if isinstance(date_obj, datetime.date) and not isinstance(date_obj, datetime.datetime):
        date_obj = datetime.datetime.combine(date_obj, datetime.time())
        
    # 获取原始日期的年、月、日
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    
    # 计算新的年和月
    month += months
    year += (month - 1) // 12
    month = ((month - 1) % 12) + 1
    
    # 处理月末日期问题（例如1月31日加一个月应该是2月28/29日）
    last_day_of_month = get_last_day_of_month(year, month)
    day = min(day, last_day_of_month.day)
    
    # 创建新的日期
    new_date = datetime.datetime(year, month, day, 
                               date_obj.hour, date_obj.minute, 
                               date_obj.second, date_obj.microsecond)
    
    return new_date


def get_last_day_of_month(year: int, month: int) -> datetime.date:
    """
    获取指定年月的最后一天
    
    Args:
        year: 年份
        month: 月份
        
    Returns:
        date: 当月最后一天的日期
    """
    # 如果是12月，则下个月是下一年的1月
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    
    # 下个月第一天减去一天就是当月最后一天
    return next_month - datetime.timedelta(days=1)


def date_diff_in_days(date1: Union[datetime.datetime, datetime.date],
                      date2: Union[datetime.datetime, datetime.date]) -> int:
    """
    计算两个日期之间相差的天数
    
    Args:
        date1: 第一个日期
        date2: 第二个日期
        
    Returns:
        int: 相差的天数（绝对值）
    """
    if isinstance(date1, datetime.datetime):
        date1 = date1.date()
        
    if isinstance(date2, datetime.datetime):
        date2 = date2.date()
        
    delta = date2 - date1
    return abs(delta.days)


def is_same_day(date1: Union[datetime.datetime, datetime.date],
                date2: Union[datetime.datetime, datetime.date]) -> bool:
    """
    判断两个日期是否是同一天
    
    Args:
        date1: 第一个日期
        date2: 第二个日期
        
    Returns:
        bool: 是否是同一天
    """
    if isinstance(date1, datetime.datetime):
        date1 = date1.date()
        
    if isinstance(date2, datetime.datetime):
        date2 = date2.date()
        
    return date1 == date2


def get_start_of_day(date_obj: Union[datetime.datetime, datetime.date]) -> datetime.datetime:
    """
    获取指定日期的开始时间（0点0分0秒）
    
    Args:
        date_obj: 日期对象
        
    Returns:
        datetime: 当天开始时间
    """
    if isinstance(date_obj, datetime.date) and not isinstance(date_obj, datetime.datetime):
        return datetime.datetime.combine(date_obj, datetime.time.min)
    
    return datetime.datetime.combine(date_obj.date(), datetime.time.min)


def get_end_of_day(date_obj: Union[datetime.datetime, datetime.date]) -> datetime.datetime:
    """
    获取指定日期的结束时间（23点59分59秒）
    
    Args:
        date_obj: 日期对象
        
    Returns:
        datetime: 当天结束时间
    """
    if isinstance(date_obj, datetime.date) and not isinstance(date_obj, datetime.datetime):
        return datetime.datetime.combine(date_obj, datetime.time.max)
    
    return datetime.datetime.combine(date_obj.date(), datetime.time.max)


def get_start_of_month(date_obj: Union[datetime.datetime, datetime.date]) -> datetime.datetime:
    """
    获取指定日期所在月的第一天
    
    Args:
        date_obj: 日期对象
        
    Returns:
        datetime: 当月第一天
    """
    if isinstance(date_obj, datetime.datetime):
        return datetime.datetime(date_obj.year, date_obj.month, 1)
    
    return datetime.datetime(date_obj.year, date_obj.month, 1)


def get_end_of_month(date_obj: Union[datetime.datetime, datetime.date]) -> datetime.datetime:
    """
    获取指定日期所在月的最后一天
    
    Args:
        date_obj: 日期对象
        
    Returns:
        datetime: 当月最后一天
    """
    last_day = get_last_day_of_month(date_obj.year, date_obj.month)
    return get_end_of_day(last_day)


def get_date_range(start_date: Union[datetime.datetime, datetime.date],
                   end_date: Union[datetime.datetime, datetime.date]) -> list:
    """
    获取两个日期之间的所有日期列表
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        list: 日期列表
    """
    if isinstance(start_date, datetime.datetime):
        start_date = start_date.date()
        
    if isinstance(end_date, datetime.datetime):
        end_date = end_date.date()
    
    date_list = []
    current_date = start_date
    
    while current_date <= end_date:
        date_list.append(current_date)
        current_date = current_date + datetime.timedelta(days=1)
    
    return date_list 