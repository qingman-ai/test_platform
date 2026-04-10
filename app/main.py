#启动FastAPI应用，访问http://localhost:8000
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import engine, get_db
from . import crud, schemas
from typing import Optional

from fastapi import BackgroundTasks
from . import models

from fastapi.templating import Jinja2Templates
from fastapi import Request
import json
from fastapi import Body
from fastapi.security import APIKeyHeader
from fastapi import Depends

from .auth import hash_password, verify_password, create_access_token, get_current_user
from fastapi.responses import RedirectResponse, JSONResponse

from .scheduler import init_scheduler, shutdown_scheduler, add_job_to_scheduler, remove_job_from_scheduler, parse_cron_expr
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi.responses import StreamingResponse
from fastapi import UploadFile, File
from .export_import import export_to_excel, export_to_yaml, import_from_excel, import_from_yaml
from io import BytesIO

templates = Jinja2Templates(directory="templates")
templates.env.cache = {}

@asynccontextmanager
async def lifespan(app):
    """FastAPI 生命周期管理：启动时初始化调度器，关闭时清理"""
    init_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(title="测试平台", lifespan=lifespan)


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS value"))
        row = result.fetchone()
        return {
            "message": "数据库连接成功",
            "result": row[0]
        }


@app.post("/cases/", response_model=schemas.TestCaseResponse)
def create_case(
    case: schemas.TestCaseCreate, 
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    return crud.create_test_case(db, case)


@app.get("/cases/", response_model=list[schemas.TestCaseResponse])
def list_cases(module: Optional[str] = None, priority: Optional[int] = None, tag: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_test_cases(db, module, priority, tag)

@app.post("/run/{case_id}")
def run_case(case_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return crud.run_test_case(db, case_id)

@app.post("/run/")
def run_cases_batch(
    background_tasks: BackgroundTasks,
    module: Optional[str] = None,
    priority: Optional[int] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    
    # 先创建批量任务记录，拿到 batch_id
    batch = crud.create_batch_record(db, module, priority, tag)
    # 后台异步执行
    background_tasks.add_task(crud.run_test_cases_batch, db, batch.id, module, priority, tag)
    return {"message": "测试任务已启动，后台执行中","batch_id": batch.id}

@app.get("/run/status/{batch_id}")
def batch_status(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(models.BatchRun).filter(models.BatchRun.id == batch_id).first()
    if not batch:
        return {"error": "批量任务不存在"}
    return {
        "batch_id": batch.id,
        "status": batch.status,
        "total_cases": batch.total_cases,
        "finished_cases": batch.finished_cases,
        "module": batch.module,
        "priority": batch.priority,
        "tag": batch.tag,
        "created_at": batch.created_at,
        "finished_at": batch.finished_at
    }

@app.get("/run/report/{batch_id}")
def batch_report(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(models.BatchRun).filter(models.BatchRun.id == batch_id).first()
    if not batch:
        return {"error": "批量任务不存在"}

# ✅ 按时间范围查：只查本次批量任务期间产生的结果
    results = db.query(models.TestResult).filter(
        models.TestResult.run_time >= batch.created_at,
        models.TestResult.run_time <= batch.finished_at
    ).all()

    failed_cases = [r for r in results if r.result == "FAIL"]

    report = {
        "batch_id": batch.id,
        "status": batch.status,
        "total_cases": batch.total_cases,
        "finished_cases": batch.finished_cases,
        "failed_count": len(failed_cases),
        "passed_count": len([r for r in results if r.result == "PASS"]),
        "failed_cases": [{"case_id": r.case_id, "error_message": r.error_message} for r in failed_cases]
    }

    return report

@app.get("/demo_login")
def demo_login(user: str = None):
    if user:
        return {"message": f"{user} 登录成功"}
    return {"message": "缺少用户名"}

#新增接口：返回HTML格式的测试报告，访问http://localhost:8000/run/report/html/{batch_id}
@app.get("/run/report/html/{batch_id}")
def batch_report_html(batch_id: int, request: Request, db: Session = Depends(get_db)):
    batch = db.query(models.BatchRun).filter(models.BatchRun.id == batch_id).first()
    if not batch:
        return {"error": "批量任务不存在"}

    # 查询结果
    results = db.query(models.TestResult).filter(
        models.TestResult.run_time >= batch.created_at,
        models.TestResult.run_time <= batch.finished_at
    ).all()

    # 处理为列表字典，包含参数
    result_list = []
    for r in results:
        case = db.query(models.TestCase).filter(models.TestCase.id == r.case_id).first()
        result_list.append({
                "case_id": r.case_id,
                "params": r.actual_body,
                "result": r.result,
                "error_message": r.error_message,
                "module": case.module if case else "default"
            })

    failed_cases = [r for r in result_list if r["result"] == "FAIL"]

    report_data = {
        "batch_id": batch.id,
        "module": batch.module,
        "priority": batch.priority,
        "tag": batch.tag,
        "total_cases": batch.total_cases,
        "finished_cases": batch.finished_cases,
        "failed_count": len(failed_cases),
        "failed_cases": failed_cases,
        "results": result_list,
        "results_json": json.dumps(result_list)
    }

    return templates.TemplateResponse(
        request=request,
        name="report.html",
        context={"batch": report_data}
)
#更新/编辑用例接口
@app.put("/cases/{case_id}", response_model=schemas.TestCaseResponse)
def update_case(
    case_id: int, 
    case: schemas.TestCaseCreate, 
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    result = crud.update_test_case(db, case_id, case)
    if not result:
        return {"error": "用例不存在"}
    return result

 #删除用例接口
@app.delete("/cases/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    result = crud.delete_test_case(db, case_id)
    if not result:
        return {"error": "用例不存在"}
    return result

#新增接口：演示接收 JSON 请求体参数，访问 http://localhost:8000/demo_register，POST 请求，Body 传入 {"username": "test", "password
@app.post("/demo_register")
def demo_register(data: dict = Body(...)):
    username = data.get("username", "")
    password = data.get("password", "")
    if username and password:
        return {"message": f"{username} 注册成功", "code": 0}
    return {"message": "缺少用户名或密码", "code": 1}

#新增接口：演示接收 JSON 请求体参数和请求头，访问 http://localhost:8000/demo_token_login，POST 请求，Body 传入 {"username": "test
@app.post("/demo_token_login")
def demo_token_login(data: dict = Body(...)):
    username = data.get("username")
    password = data.get("password")

    if username == "test" and password == "123456":
        return {
            "code": 0,
            "message": "登录成功",
            "token": "abc123token"
        }
    return {
        "code": 1,
        "message": "用户名或密码错误"
    }
#新增接口：演示接收请求头中的 token，访问 http://localhost:8000/demo_user_info，GET 请求，Header 传入 Authorization

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

@app.get("/demo_user_info")
def demo_user_info(authorization: str = Depends(api_key_header)):
    authorization = authorization.strip() if authorization else None

    if authorization == "Bearer abc123token":
        return {
            "code": 0,
            "message": "查询成功",
            "data": {
                "name": "test_user"
            }
        }

    return {
        "code": 401,
        "message": "未授权",
        "received_authorization": authorization
    }

#测试接收请求头中的 token，直接返回接收到的值
# api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

# @app.get("/demo_user_info")
# def demo_user_info(authorization: str = Depends(api_key_header)):
#     return {
#         "received_authorization": authorization,
#         "received_repr": repr(authorization),
#         "expected": "Bearer abc123token",
#         "is_equal": authorization == "Bearer abc123token"
#     } 

# ===== 登录页面 =====
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")
 
 
# ===== 用户注册接口 =====
@app.post("/api/register")
def register(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
 
    if not username or not password:
        return JSONResponse(status_code=400, content={"detail": "用户名和密码不能为空"})
 
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"detail": "密码长度不能少于6位"})
 
    # 检查用户名是否已存在
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        return JSONResponse(status_code=400, content={"detail": "用户名已存在"})
 
    # 创建用户
    user = models.User(
        username=username,
        password_hash=hash_password(password),
        role="user"  # 默认普通用户
    )
    db.add(user)
    db.commit()
    db.refresh(user)
 
    return {"message": "注册成功", "username": user.username}
 
 
# ===== 用户登录接口 =====
@app.post("/api/login")
def login(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
 
    if not username or not password:
        return JSONResponse(status_code=400, content={"detail": "用户名和密码不能为空"})
 
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return JSONResponse(status_code=401, content={"detail": "用户名或密码错误"})
 
    # 生成 JWT token
    token = create_access_token({"sub": user.username, "role": user.role})
 
    # 同时设置 Cookie（前端页面用）和返回 token（API 调用用）
    response = JSONResponse(content={
        "message": "登录成功",
        "token": token,
        "username": user.username,
        "role": user.role
    })
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return response
 
 
# ===== 退出登录 =====
@app.post("/api/logout")
def logout():
    response = JSONResponse(content={"message": "已退出登录"})
    response.delete_cookie("access_token")
    return response
 
 
# ===== 获取当前用户信息 =====
@app.get("/api/me")
def get_me(user: models.User = Depends(get_current_user)):
    return {
        "username": user.username,
        "role": user.role,
        "created_at": str(user.created_at)
    }

# ===== 定时任务管理 API =====

@app.get("/api/jobs", response_model=list[schemas.ScheduleJobResponse])
def list_jobs(db: Session = Depends(get_db)):
    """查询所有定时任务"""
    jobs = db.query(models.ScheduleJob).order_by(models.ScheduleJob.id.desc()).all()
    return jobs


@app.post("/api/jobs", response_model=schemas.ScheduleJobResponse)
def create_job(
    data: schemas.ScheduleJobCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """创建定时任务"""
    # 先验证 cron 表达式格式
    try:
        parse_cron_expr(data.cron_expr)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

    job = models.ScheduleJob(
        name=data.name,
        cron_expr=data.cron_expr,
        module=data.module,
        enabled=data.enabled,
        created_by=user.username
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # 如果启用状态，立即加入调度器
    if job.enabled == 1:
        add_job_to_scheduler(job.id, job.cron_expr)

    return job


@app.put("/api/jobs/{job_id}", response_model=schemas.ScheduleJobResponse)
def update_job(
    job_id: int,
    data: schemas.ScheduleJobCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """编辑定时任务"""
    job = db.query(models.ScheduleJob).filter(models.ScheduleJob.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"detail": "任务不存在"})

    try:
        parse_cron_expr(data.cron_expr)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"detail": str(e)})

    job.name = data.name
    job.cron_expr = data.cron_expr
    job.module = data.module
    job.enabled = data.enabled
    db.commit()
    db.refresh(job)

    # 更新调度器
    remove_job_from_scheduler(job_id)
    if job.enabled == 1:
        add_job_to_scheduler(job.id, job.cron_expr)

    return job


@app.delete("/api/jobs/{job_id}")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """删除定时任务"""
    job = db.query(models.ScheduleJob).filter(models.ScheduleJob.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"detail": "任务不存在"})

    remove_job_from_scheduler(job_id)
    db.delete(job)
    db.commit()
    return {"message": f"定时任务 {job_id} 已删除"}


@app.post("/api/jobs/{job_id}/toggle")
def toggle_job(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """启用/禁用定时任务"""
    job = db.query(models.ScheduleJob).filter(models.ScheduleJob.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"detail": "任务不存在"})

    # 切换状态
    job.enabled = 0 if job.enabled == 1 else 1
    db.commit()
    db.refresh(job)

    # 更新调度器
    if job.enabled == 1:
        add_job_to_scheduler(job.id, job.cron_expr)
    else:
        remove_job_from_scheduler(job_id)

    return {"message": f"任务已{'启用' if job.enabled == 1 else '禁用'}", "enabled": job.enabled}


@app.post("/api/jobs/{job_id}/run")
def run_job_now(
    job_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """立即执行一次定时任务（手动触发）"""
    job = db.query(models.ScheduleJob).filter(models.ScheduleJob.id == job_id).first()
    if not job:
        return JSONResponse(status_code=404, content={"detail": "任务不存在"})

    # 创建批量执行记录
    batch = crud.create_batch_record(db, module=job.module)

    # 同步执行（手动触发不放后台，直接返回结果）
    report = crud.run_test_cases_batch(db, batch.id, module=job.module)

    # 更新任务状态
    job.last_run_at = datetime.now()
    job.last_batch_id = batch.id
    if isinstance(report, dict) and report.get("failed_count", 0) == 0:
        job.last_run_status = "success"
    else:
        job.last_run_status = "failed"
    db.commit()

    return {"message": "手动执行完成", "batch_id": batch.id, "status": job.last_run_status}

# ===== 用例导入导出 API =====

@app.get("/api/export/excel")
def export_excel(module: Optional[str] = None, db: Session = Depends(get_db)):
    """导出用例为 Excel 文件"""
    output = export_to_excel(db, module)
    filename = f"test_cases_{module or 'all'}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/export/yaml")
def export_yaml(module: Optional[str] = None, db: Session = Depends(get_db)):
    """导出用例为 YAML 文件"""
    yaml_content = export_to_yaml(db, module)
    filename = f"test_cases_{module or 'all'}.yaml"
    return StreamingResponse(
        BytesIO(yaml_content.encode("utf-8")),
        media_type="application/x-yaml",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/api/import/excel")
async def import_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """从 Excel 导入用例"""
    if not file.filename.endswith((".xlsx", ".xls")):
        return JSONResponse(status_code=400, content={"detail": "请上传 .xlsx 格式的文件"})

    content = await file.read()
    result = import_from_excel(db, content, created_by=user.username)
    return result


@app.post("/api/import/yaml")
async def import_yaml_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    """从 YAML 导入用例"""
    if not file.filename.endswith((".yaml", ".yml")):
        return JSONResponse(status_code=400, content={"detail": "请上传 .yaml 格式的文件"})

    content = await file.read()
    result = import_from_yaml(db, content.decode("utf-8"), created_by=user.username)
    return result