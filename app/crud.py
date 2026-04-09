from sqlalchemy.orm import Session
from . import models, schemas

from sqlalchemy.sql import func
import json
import requests
from datetime import datetime

import re
import copy

#创建测试用例
def create_test_case(db: Session, case: schemas.TestCaseCreate):
    db_case = models.TestCase(
        name=case.name,
        method=case.method,
        url=case.url,
        expected_status=case.expected_status,
        expected_body=case.expected_body,
        module=case.module,
        priority=case.priority,
        tags=case.tags,
    )
    # 直接赋值，setter 会自动转成 JSON 字符串存入数据库
    db_case.headers = case.headers
    db_case.params = case.params
    db_case.param_sets = case.param_sets
    db_case.body = case.body #新增请求体参数

    db_case.assert_keyword = case.assert_keyword
    db_case.assert_json_field = case.assert_json_field
    db_case.assert_max_time = case.assert_max_time

    db_case.extract_vars = case.extract_vars

    db.add(db_case) #将行数据加入“代保存”列表
    db.commit()   # 真正保存到数据库
    db.refresh(db_case)  # 从数据库重新读取这条记录（获取自动生成的 ID 和时间）
    return db_case

  # 1. 执行单个用例
def run_test_case(db: Session, case_id: int, context=None):

    if context is None:  #上下文变量字典，用于变量替换和提取，第一次调用时传 None，函数内部会创建一个空字典
        context = {}

    case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    #db:操作数据库的工具对象，case_id:要执行的用例ID
    #db.query（）：用数据库对象查询某张表，filter（）：添加过滤条件，first（）：获取第一条结果

    if not case:
        return {"error": "用例不存在"}
    # 直接用 property，不需要 json.loads
    headers = replace_variables(case.headers, context)
    param_sets = case.param_sets if case.param_sets else [case.params or {}]
    param_sets = [replace_variables(p, context) for p in param_sets]
    request_body = replace_variables(case.body, context)

    results = []
    for params in param_sets:

        # 2. 发送HTTP请求
        try:
            import time
            start_time = time.time()

            if case.method.upper() in ["POST", "PUT", "PATCH"]:
                # POST/PUT/PATCH 用 json 参数发送请求体
                response = requests.request(
                    method=case.method,
                    url=case.url,
                    headers=headers,
                    json=request_body if request_body else params  #如果请求体参数存在就用请求体参数，否则用查询参数
                )
            else:
                # GET/DELETE 用 params 发送查询参数
                response = requests.request(
                    method=case.method,
                    url=case.url,
                    headers=headers,
                    params=params
                )

            elapsed_time = time.time() - start_time
            actual_status = response.status_code  #获取相应状态码
            actual_body = response.text   #获取响应体文本内容

             # 多重断言
            errors = []

            # 1. 状态码断言
            if case.expected_status and actual_status != case.expected_status:
                errors.append(f"状态码不匹配: 预期{case.expected_status}, 实际{actual_status}")

            # 2. 关键字断言
            if case.assert_keyword and case.assert_keyword not in actual_body:
                errors.append(f"响应体不包含关键字: {case.assert_keyword}")

            # 3. JSON 字段断言
            if case.assert_json_field:
                try:
                    response_json = response.json()
                    for key, expected_value in case.assert_json_field.items():
                        actual_value = response_json.get(key)
                        if str(actual_value) != str(expected_value):
                            errors.append(f"JSON字段不匹配: {key} 预期{expected_value}, 实际{actual_value}")
                except Exception:
                    errors.append("响应体不是有效的JSON格式")

            # 4. 响应时间断言
            if case.assert_max_time:
                max_time = float(case.assert_max_time)
                if elapsed_time > max_time:
                    errors.append(f"响应超时: 限制{max_time}秒, 实际{elapsed_time:.3f}秒")

            # 综合判断
            result = "PASS" if len(errors) == 0 else "FAIL"
            error_message = "; ".join(errors) if errors else None

            # 变量提取
            if case.extract_vars:
                try:
                    response_json = response.json()
                    extract_variables_from_response(response_json, case.extract_vars, context)
                except Exception:
                    pass


        except Exception as e:
            actual_status = None
            actual_body = None
            result = "FAIL"
            error_message = str(e)

        
        # 4. 保存结果
        db_result = models.TestResult(
            case_id=case.id,
            actual_status=actual_status,
            actual_body=actual_body,
            result=result,
            run_time=datetime.now(),  #获取当前时间作为执行时间
            error_message=error_message 
        )

        db.add(db_result) #将结果对象添加到数据库会话中
        db.commit()   #提交会话，保存结果到数据库，主要就是保存测试结果到test_result表中

        # 保存每组参数执行结果
        results.append({
            "case_id": case.id,
            "params": params,
            "result": result,
            "error_message": error_message
        })

    return results

# 2. 查询用例列表
def get_test_cases(db: Session, module: str = None, priority: int = None, tag: str = None):
    query = db.query(models.TestCase)
    if module:
        query = query.filter(models.TestCase.module == module)
    if priority:
        query = query.filter(models.TestCase.priority == priority)
    if tag:
        query = query.filter(models.TestCase.tags.like(f"%{tag}%"))

    return query.all()

 # 批量执行用例
def run_test_cases(db: Session, module: str = None, priority: int = None, tag: str = None):
    # 查询符合条件的用例
    cases = db.query(models.TestCase)
    if module:
        cases = cases.filter(models.TestCase.module == module)
    if priority:
        cases = cases.filter(models.TestCase.priority == priority)
    if tag:
        cases = cases.filter(models.TestCase.tags.like(f"%{tag}%"))
    cases = cases.all()

    results = []
    context = {} #批量执行时共享一个上下文变量字典，所有用例都可以从中读取和写入变量，实现用例间的关联
    for case in cases:
        res_list = run_test_case(db, case.id, context)
        results.extend(res_list)
    return results

#批量执行用例并生成报告
def run_test_cases_batch(db: Session, batch_id: int, module=None, priority=None, tag=None):
    batch = db.query(models.BatchRun).filter(models.BatchRun.id == batch_id).first()
    if not batch:
        return {"error": "批量任务不存在"}

    cases = get_test_cases(db, module, priority, tag)

    finished = 0
    results = []
    failed_cases = []

    context = {}  # 批量执行时共享一个上下文变量字典，实现用例间关联

    for case in cases:
        res_list = run_test_case(db, case.id, context)
        results.extend(res_list)
        finished += 1
        batch.finished_cases = finished
        db.commit()

        for res in res_list:
            if res["result"] == "FAIL":
                failed_cases.append(res)

    batch.status = "finished"
    batch.finished_at = func.now()
    db.commit()

    report = {
        "batch_id": batch.id,
        "total_cases": batch.total_cases,
        "finished_cases": batch.finished_cases,
        "failed_count": len(failed_cases),
        "failed_cases": failed_cases,
        "results": results
    }

    return report

# 编辑用例
def update_test_case(db: Session, case_id: int, case: schemas.TestCaseCreate):
    db_case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    if not db_case:
        return None

    db_case.name = case.name
    db_case.method = case.method
    db_case.url = case.url
    db_case.headers = case.headers
    db_case.params = case.params
    db_case.param_sets = case.param_sets
    db_case.body = case.body #新增请求体参数
    db_case.expected_status = case.expected_status
    db_case.expected_body = case.expected_body
    db_case.module = case.module
    db_case.priority = case.priority
    db_case.tags = case.tags

    db_case.extract_vars = case.extract_vars

    # 更新断言字段
    db_case.assert_keyword = case.assert_keyword  
    db_case.assert_json_field = case.assert_json_field  
    db_case.assert_max_time = case.assert_max_time

    db.commit()
    db.refresh(db_case)
    return db_case


# 删除用例
def delete_test_case(db: Session, case_id: int):
    db_case = db.query(models.TestCase).filter(models.TestCase.id == case_id).first()
    if not db_case:
        return None

    db.delete(db_case)
    db.commit()
    return {"message": f"用例 {case_id} 已删除"}

# 变量替换函数
def replace_variables(data, context):
    """
    递归替换 data 中的 ${var} 变量
    data 可以是 dict / list / str / 其他类型
    """
    if isinstance(data, dict):
        return {k: replace_variables(v, context) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_variables(item, context) for item in data]
    elif isinstance(data, str):
        pattern = r"\$\{(\w+)\}"

        def repl(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        return re.sub(pattern, repl, data)
    else:
        return data
    
def extract_variables_from_response(response_json, extract_rules, context):
    """
    根据提取规则，从响应 JSON 中提取变量并保存到 context
    extract_rules 例子:
    {
        "token": "token",
        "user_id": "user_id"
    }
    含义：
    从 response_json["token"] 提取，保存成 context["token"]
    从 response_json["user_id"] 提取，保存成 context["user_id"]
    """
    if not extract_rules:
        return

    for var_name, json_key in extract_rules.items():
        if json_key in response_json:
            context[var_name] = response_json[json_key]

def create_batch_run(db: Session, module=None, priority=None, tag=None):
    cases = get_test_cases(db, module, priority, tag)
    batch = models.BatchRun(
        module=module,
        priority=priority,
        tag=tag,
        status="pending",
        total_cases=len(cases),
        finished_cases=0
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch

def create_batch_record(db: Session, module=None, priority=None, tag=None):
    cases = get_test_cases(db, module, priority, tag)
    batch = models.BatchRun(
        module=module,
        priority=priority,
        tag=tag,
        status="running",
        total_cases=len(cases),
        finished_cases=0
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch