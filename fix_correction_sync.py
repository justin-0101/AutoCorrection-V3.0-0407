#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
批改结果同步修复工具
用于解决corrections表和essays表之间的数据同步问题
"""

# 在导入任何其他模块之前应用eventlet猴子补丁
import os
import sys

try:
    import eventlet
    eventlet.monkey_patch(os=True, select=True, socket=True, thread=True, time=True)
    os.environ['EVENTLET_PATCHED'] = 'true'
    print("eventlet猴子补丁已提前应用于修复工具")
except ImportError:
    print("警告: 未安装eventlet，某些功能可能无法正常工作")

import json
import sqlite3
import logging
from datetime import datetime
import argparse
import time
import threading

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = 'instance/essay_correction.db'

def connect_db():
    """连接数据库"""
    try:
        if not os.path.exists(DB_PATH):
            logger.error(f"数据库文件不存在: {DB_PATH}")
            return None
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        logger.info(f"成功连接到数据库: {DB_PATH}")
        return conn
    except Exception as e:
        logger.error(f"连接数据库时出错: {str(e)}")
        return None

def fix_all_corrections():
    """修复所有批改记录"""
    conn = connect_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 查找状态为'completed'但essay中未同步的记录
        sql = """
        SELECT c.id, c.essay_id, c.status, c.results, c.score, c.comments, c.error_analysis, c.improvement_suggestions,
               e.status as essay_status, e.score as essay_score, e.comments as essay_comments, e.error_analysis as essay_error_analysis
        FROM corrections c
        JOIN essays e ON c.essay_id = e.id
        WHERE c.status = 'completed' AND c.results IS NOT NULL
        AND (e.status != 'completed' OR e.score IS NULL OR e.score = 0 OR e.comments IS NULL OR e.comments = '' OR e.error_analysis IS NULL OR e.error_analysis = '')
        """
        
        cursor.execute(sql)
        records = cursor.fetchall()
        logger.info(f"找到 {len(records)} 条需要同步的记录")
        
        fixed_count = 0
        
        for rec in records:
            try:
                logger.info(f"正在处理: correction_id={rec['id']}, essay_id={rec['essay_id']}")
                
                # 解析results JSON数据
                results = None
                if rec['results']:
                    try:
                        results = json.loads(rec['results']) if isinstance(rec['results'], str) else rec['results']
                    except json.JSONDecodeError:
                        logger.warning(f"JSON解析失败: correction_id={rec['id']}")
                        continue
                else:
                    logger.warning(f"无有效results数据: correction_id={rec['id']}")
                    continue
                
                # 同步关键字段
                update_sql = """
                UPDATE essays 
                SET status = 'completed', 
                """
                
                params = []
                update_fields = []
                
                # 判断数据来源优先级：优先使用单独字段值，其次使用results字段中的值
                # 分数
                if rec['score'] is not None and rec['score'] > 0:
                    update_fields.append("score = ?")
                    params.append(rec['score'])
                elif results and 'score' in results and results['score'] is not None:
                    update_fields.append("score = ?")
                    params.append(results['score'])
                elif results and 'total_score' in results and results['total_score'] is not None:
                    update_fields.append("score = ?")
                    params.append(results['total_score'])
                
                # 评语
                if rec['comments'] and rec['comments'].strip():
                    update_fields.append("comments = ?")
                    params.append(rec['comments'])
                elif results and 'comments' in results and results['comments']:
                    update_fields.append("comments = ?")
                    params.append(results['comments'])
                elif results and 'feedback' in results and results['feedback']:
                    update_fields.append("comments = ?")
                    params.append(results['feedback'])
                
                # 错误分析
                if rec['error_analysis'] and rec['error_analysis'] != '{}':
                    update_fields.append("error_analysis = ?")
                    params.append(rec['error_analysis'])
                elif results and 'error_analysis' in results and results['error_analysis']:
                    error_analysis = results['error_analysis']
                    if isinstance(error_analysis, dict):
                        update_fields.append("error_analysis = ?")
                        params.append(json.dumps(error_analysis, ensure_ascii=False))
                    elif isinstance(error_analysis, str):
                        update_fields.append("error_analysis = ?")
                        params.append(error_analysis)
                
                # 改进建议
                if rec['improvement_suggestions'] and rec['improvement_suggestions'].strip():
                    update_fields.append("improvement_suggestions = ?")
                    params.append(rec['improvement_suggestions'])
                elif results and 'improvement_suggestions' in results and results['improvement_suggestions']:
                    update_fields.append("improvement_suggestions = ?")
                    params.append(results['improvement_suggestions'])
                
                # 更新时间
                update_fields.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                
                # 添加essay_id
                params.append(rec['essay_id'])
                
                # 构建并执行SQL
                if update_fields:
                    final_sql = update_sql + ", ".join(update_fields) + " WHERE id = ?"
                    cursor.execute(final_sql, params)
                    conn.commit()
                    fixed_count += 1
                    logger.info(f"成功同步: essay_id={rec['essay_id']}")
                else:
                    logger.warning(f"无需同步的字段: essay_id={rec['essay_id']}")
                
            except Exception as e:
                logger.error(f"同步记录时出错: correction_id={rec['id']}, error={str(e)}")
                conn.rollback()
        
        logger.info(f"成功修复 {fixed_count} 条记录，总计 {len(records)} 条")
        
    except Exception as e:
        logger.error(f"查询或处理记录时出错: {str(e)}")
    finally:
        conn.close()

def fix_specific_essay(essay_id):
    """修复特定文章的批改记录"""
    conn = connect_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 查询该文章的批改记录
        sql = """
        SELECT c.id, c.essay_id, c.status, c.results, c.score, c.comments, c.error_analysis, c.improvement_suggestions,
               e.status as essay_status, e.score as essay_score, e.comments as essay_comments, e.error_analysis as essay_error_analysis
        FROM corrections c
        JOIN essays e ON c.essay_id = e.id
        WHERE c.essay_id = ?
        """
        
        cursor.execute(sql, (essay_id,))
        rec = cursor.fetchone()
        
        if not rec:
            logger.error(f"未找到essay_id={essay_id}的批改记录")
            return
        
        logger.info(f"找到记录: correction_id={rec['id']}, essay_id={rec['essay_id']}")
        logger.info(f"批改状态: {rec['status']}, 文章状态: {rec['essay_status']}")
        
        # 解析results JSON数据
        results = None
        if rec['results']:
            try:
                results = json.loads(rec['results']) if isinstance(rec['results'], str) else rec['results']
                logger.info(f"成功解析results数据，包含字段: {', '.join(results.keys())}")
            except json.JSONDecodeError:
                logger.warning(f"JSON解析失败: correction_id={rec['id']}")
        else:
            logger.warning(f"无results数据: correction_id={rec['id']}")
        
        # 检查并同步状态
        if rec['status'] == 'completed' and rec['essay_status'] != 'completed':
            cursor.execute("UPDATE essays SET status = 'completed', updated_at = ? WHERE id = ?", 
                         (datetime.now().isoformat(), essay_id))
            conn.commit()
            logger.info(f"已同步状态: essay_id={essay_id}, 从 {rec['essay_status']} 更新为 completed")
        
        # 同步其他字段
        update_fields = []
        params = []
        need_update = False
        
        # 分数
        if (rec['score'] is not None and rec['score'] > 0 and rec['essay_score'] != rec['score']) or \
           (rec['essay_score'] is None or rec['essay_score'] == 0):
            if rec['score'] is not None and rec['score'] > 0:
                update_fields.append("score = ?")
                params.append(rec['score'])
                need_update = True
                logger.info(f"将同步分数: {rec['score']}")
            elif results and 'score' in results and results['score'] is not None:
                update_fields.append("score = ?")
                params.append(results['score'])
                need_update = True
                logger.info(f"将同步分数(从results): {results['score']}")
        
        # 评语
        if (rec['comments'] and rec['comments'].strip() and rec['essay_comments'] != rec['comments']) or \
           (not rec['essay_comments'] or not rec['essay_comments'].strip()):
            if rec['comments'] and rec['comments'].strip():
                update_fields.append("comments = ?")
                params.append(rec['comments'])
                need_update = True
                logger.info(f"将同步评语: {rec['comments'][:30]}...")
            elif results and 'comments' in results and results['comments']:
                update_fields.append("comments = ?")
                params.append(results['comments'])
                need_update = True
                logger.info(f"将同步评语(从results): {results['comments'][:30]}...")
        
        # 错误分析
        if (rec['error_analysis'] and rec['error_analysis'] != '{}' and rec['essay_error_analysis'] != rec['error_analysis']) or \
           (not rec['essay_error_analysis'] or rec['essay_error_analysis'] == '{}'):
            if rec['error_analysis'] and rec['error_analysis'] != '{}':
                update_fields.append("error_analysis = ?")
                params.append(rec['error_analysis'])
                need_update = True
                logger.info(f"将同步错误分析")
            elif results and 'error_analysis' in results and results['error_analysis']:
                error_analysis = results['error_analysis']
                if isinstance(error_analysis, dict):
                    update_fields.append("error_analysis = ?")
                    params.append(json.dumps(error_analysis, ensure_ascii=False))
                    need_update = True
                    logger.info(f"将同步错误分析(从results)")
                elif isinstance(error_analysis, str):
                    update_fields.append("error_analysis = ?")
                    params.append(error_analysis)
                    need_update = True
                    logger.info(f"将同步错误分析(从results-字符串)")
        
        # 如果需要更新
        if need_update:
            # 更新时间
            update_fields.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            # 添加essay_id
            params.append(essay_id)
            
            # 构建并执行SQL
            update_sql = "UPDATE essays SET " + ", ".join(update_fields) + " WHERE id = ?"
            cursor.execute(update_sql, params)
            conn.commit()
            logger.info(f"已成功同步数据至essay_id={essay_id}")
        else:
            logger.info(f"essay_id={essay_id}不需要同步数据")
        
        # 如果correction状态不是完成但已有results，则更新状态
        if rec['status'] != 'completed' and results:
            cursor.execute("UPDATE corrections SET status = 'completed', updated_at = ? WHERE id = ?",
                         (datetime.now().isoformat(), rec['id']))
            conn.commit()
            logger.info(f"已将correction_id={rec['id']}的状态更新为completed")
        
    except Exception as e:
        logger.error(f"处理essay_id={essay_id}时出错: {str(e)}")
    finally:
        conn.close()

def fix_batch_sync(start_id, end_id):
    """批量同步一个范围内的文章记录"""
    conn = connect_db()
    if not conn:
        return
    
    try:
        for essay_id in range(start_id, end_id + 1):
            fix_specific_essay(essay_id)
    finally:
        conn.close()

def check_database_consistency():
    """检查数据库中批改记录与文章的一致性"""
    conn = connect_db()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 检查所有状态为'completed'的批改记录
        sql = """
        SELECT c.id, c.essay_id, c.status, e.status as essay_status,
               (c.score IS NOT NULL AND c.score > 0) as has_correction_score,
               (e.score IS NOT NULL AND e.score > 0) as has_essay_score,
               (c.comments IS NOT NULL AND c.comments != '') as has_correction_comments,
               (e.comments IS NOT NULL AND e.comments != '') as has_essay_comments
        FROM corrections c
        JOIN essays e ON c.essay_id = e.id
        WHERE c.status = 'completed'
        """
        
        cursor.execute(sql)
        records = cursor.fetchall()
        
        inconsistent_records = []
        for rec in records:
            # 检查状态不一致
            if rec['status'] != rec['essay_status']:
                inconsistent_records.append((rec['essay_id'], '状态不一致', f"{rec['status']} vs {rec['essay_status']}"))
                continue
            
            # 检查分数不一致
            if rec['has_correction_score'] != rec['has_essay_score']:
                inconsistent_records.append((rec['essay_id'], '分数不一致', f"correction: {rec['has_correction_score']}, essay: {rec['has_essay_score']}"))
                continue
            
            # 检查评语不一致
            if rec['has_correction_comments'] != rec['has_essay_comments']:
                inconsistent_records.append((rec['essay_id'], '评语不一致', f"correction: {rec['has_correction_comments']}, essay: {rec['has_essay_comments']}"))
                continue
        
        if inconsistent_records:
            logger.info(f"找到 {len(inconsistent_records)} 条不一致记录:")
            for essay_id, issue, details in inconsistent_records:
                logger.info(f"- essay_id={essay_id}, 问题: {issue}, 详情: {details}")
        else:
            logger.info("所有completed状态的批改记录数据一致性良好")
        
    except Exception as e:
        logger.error(f"检查数据一致性时出错: {str(e)}")
    finally:
        conn.close()

def background_monitor(interval=300):
    """
    后台监控服务，定期检查并修复数据不一致的记录
    
    Args:
        interval: 检查间隔时间(秒)，默认5分钟
    """
    logger.info(f"启动后台监控服务，检查间隔: {interval}秒")
    
    while True:
        try:
            logger.info("执行定期检查...")
            
            # 检查数据库一致性
            check_database_consistency()
            
            # 修复所有需要同步的记录
            fix_all_corrections()
            
            logger.info(f"检查完成，等待{interval}秒后再次检查...")
        except Exception as e:
            logger.error(f"后台监控服务出错: {str(e)}")
        
        # 等待下一次检查
        time.sleep(interval)

def start_monitor_service(interval=300, daemon=True):
    """
    启动后台监控服务
    
    Args:
        interval: 检查间隔时间(秒)
        daemon: 是否作为守护线程运行
    """
    monitor_thread = threading.Thread(
        target=background_monitor,
        args=(interval,),
        daemon=daemon
    )
    monitor_thread.start()
    logger.info(f"后台监控服务已启动，检查间隔: {interval}秒")
    return monitor_thread
        
def main():
    # 添加命令行参数支持
    parser = argparse.ArgumentParser(description='批改结果同步修复工具')
    parser.add_argument('-a', '--auto', action='store_true', help='自动修复模式，不需交互')
    parser.add_argument('-c', '--check', action='store_true', help='检查数据库一致性')
    parser.add_argument('-f', '--fix-all', action='store_true', help='修复所有需要同步的记录')
    parser.add_argument('-e', '--essay-id', type=int, help='指定要修复的文章ID')
    parser.add_argument('-b', '--batch', type=str, help='批量修复范围，格式：开始ID-结束ID，例如：1-100')
    parser.add_argument('-m', '--monitor', action='store_true', help='启动后台监控服务')
    parser.add_argument('-i', '--interval', type=int, default=300, help='监控服务检查间隔(秒)，默认300秒')
    args = parser.parse_args()
    
    logger.info("===== 批改结果同步修复工具 =====")
    
    # 启动监控服务
    if args.monitor:
        logger.info(f"启动后台监控服务，间隔: {args.interval}秒")
        monitor_thread = start_monitor_service(interval=args.interval, daemon=False)
        try:
            # 保持主线程运行
            while monitor_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到中断信号，退出监控服务")
        return
    
    # 自动模式
    if args.auto:
        logger.info("启动自动修复模式")
        check_database_consistency()
        fix_all_corrections()
        logger.info("自动修复完成，程序结束")
        return
    
    # 根据参数执行相应操作
    if args.check:
        check_database_consistency()
    
    if args.fix_all:
        fix_all_corrections()
    
    if args.essay_id:
        fix_specific_essay(args.essay_id)
    
    if args.batch:
        try:
            start_id, end_id = map(int, args.batch.split('-'))
            if start_id <= end_id:
                fix_batch_sync(start_id, end_id)
            else:
                logger.error("结束ID必须大于或等于起始ID")
        except ValueError:
            logger.error("批量修复范围格式错误，正确格式：开始ID-结束ID，例如：1-100")
    
    # 如果没有提供任何参数，则进入交互模式
    if not (args.auto or args.check or args.fix_all or args.essay_id or args.batch or args.monitor):
        while True:
            print("\n请选择操作：")
            print("1. 修复所有需要同步的批改记录")
            print("2. 修复特定文章的批改记录")
            print("3. 批量修复一个范围内的文章记录")
            print("4. 检查数据库中批改记录的一致性")
            print("5. 启动后台监控服务")
            print("0. 退出")
            
            choice = input("\n请输入选项 (0-5): ")
            
            if choice == '1':
                fix_all_corrections()
            elif choice == '2':
                essay_id = input("请输入文章ID: ")
                try:
                    essay_id = int(essay_id)
                    fix_specific_essay(essay_id)
                except ValueError:
                    logger.error("请输入有效的文章ID(整数)")
            elif choice == '3':
                start_id = input("请输入起始文章ID: ")
                end_id = input("请输入结束文章ID: ")
                try:
                    start_id = int(start_id)
                    end_id = int(end_id)
                    if start_id <= end_id:
                        fix_batch_sync(start_id, end_id)
                    else:
                        logger.error("结束ID必须大于或等于起始ID")
                except ValueError:
                    logger.error("请输入有效的文章ID(整数)")
            elif choice == '4':
                check_database_consistency()
            elif choice == '5':
                interval = input("请输入检查间隔时间(秒)，默认300秒: ")
                try:
                    if interval.strip():
                        interval = int(interval)
                    else:
                        interval = 300
                    print(f"启动后台监控服务，间隔: {interval}秒")
                    print("监控服务已在后台启动，请按Ctrl+C退出程序...")
                    start_monitor_service(interval=interval, daemon=False)
                    # 注意：此处程序将继续运行，直到用户中断
                    while True:
                        time.sleep(1)
                except ValueError:
                    logger.error("请输入有效的时间间隔(整数)")
                except KeyboardInterrupt:
                    logger.info("接收到中断信号，退出程序")
                    break
            elif choice == '0':
                logger.info("程序结束")
                break
            else:
                logger.warning("无效选项，请重新输入")

if __name__ == "__main__":
    main() 