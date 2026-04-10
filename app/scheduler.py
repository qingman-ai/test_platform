"""
定时任务调度模块
使用 APScheduler 实现 cron 定时执行测试用例
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

from .database import SessionLocal
from . import models, crud

# 全局调度器实例
scheduler = BackgroundScheduler()


def execute_schedule_job(job_id: int):
    """
    定时任务的实际执行函数
    每次执行时创建独立的数据库 session（避免线程安全问题）
    """
    db = SessionLocal()
    try:
        # 1. 查询任务配置
        job = db.query(models.ScheduleJob).filter(models.ScheduleJob.id == job_id).first()
        if not job:
            return

        # 2. 创建批量执行记录
        batch = crud.create_batch_record(db, module=job.module)

        # 3. 执行批量测试
        report = crud.run_test_cases_batch(db, batch.id, module=job.module)

        # 4. 更新任务状态
        job.last_run_at = datetime.now()
        job.last_batch_id = batch.id

        if isinstance(report, dict) and report.get("failed_count", 0) == 0:
            job.last_run_status = "success"
        else:
            job.last_run_status = "failed"

        db.commit()

    except Exception as e:
        # 执行出错也记录状态
        try:
            job = db.query(models.ScheduleJob).filter(models.ScheduleJob.id == job_id).first()
            if job:
                job.last_run_at = datetime.now()
                job.last_run_status = f"error: {str(e)[:100]}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def parse_cron_expr(cron_expr: str) -> dict:
    """
    解析 cron 表达式为 APScheduler CronTrigger 参数
    支持标准5段格式：分 时 日 月 星期
    示例：
      "0 2 * * *"    -> 每天凌晨2:00
      "30 8 * * 1-5" -> 每周一到周五 8:30
      "*/10 * * * *" -> 每10分钟
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"cron表达式格式错误，需要5段（分 时 日 月 星期），实际{len(parts)}段: {cron_expr}")

    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def add_job_to_scheduler(job_id: int, cron_expr: str):
    """把一个定时任务添加到调度器"""
    cron_params = parse_cron_expr(cron_expr)
    scheduler.add_job(
        execute_schedule_job,
        trigger=CronTrigger(**cron_params),
        args=[job_id],
        id=f"schedule_job_{job_id}",  # 唯一ID，方便后续管理
        replace_existing=True,
        misfire_grace_time=60  # 错过执行时间后60秒内仍可补执行
    )


def remove_job_from_scheduler(job_id: int):
    """从调度器移除一个定时任务"""
    job_key = f"schedule_job_{job_id}"
    try:
        scheduler.remove_job(job_key)
    except Exception:
        pass  # 任务不存在时忽略


def init_scheduler():
    """
    初始化调度器：从数据库加载所有启用的任务
    在 FastAPI 启动时调用
    """
    db = SessionLocal()
    try:
        jobs = db.query(models.ScheduleJob).filter(models.ScheduleJob.enabled == 1).all()
        for job in jobs:
            try:
                add_job_to_scheduler(job.id, job.cron_expr)
            except Exception as e:
                print(f"[调度器] 加载任务 {job.id}({job.name}) 失败: {e}")

        scheduler.start()
        print(f"[调度器] 已启动，加载了 {len(jobs)} 个定时任务")
    finally:
        db.close()


def shutdown_scheduler():
    """关闭调度器，在 FastAPI 关闭时调用"""
    scheduler.shutdown(wait=False)
    print("[调度器] 已关闭")