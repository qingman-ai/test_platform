from pydantic import BaseModel
from typing import List, Dict, Optional


class TestCaseCreate(BaseModel):
    name: str
    method: str
    url: str
    headers: Optional[Dict] = None
    params: Optional[Dict] = None
    body: Optional[Dict] = None #新增字段，用于接收请求体参数
    expected_status: Optional[int] = None
    expected_body: Optional[str] = None

    module: Optional[str] = "default"
    priority: Optional[int] = 1
    tags: Optional[str] = None  # 多标签用逗号分隔
    param_sets: Optional[List[Dict[str, str]]] = None  # 用于接收多组参数的字段，前端传入JSON数组，每个元素是一个字典，包含一组参数

    # 新增断言字段
    assert_keyword: Optional[str] = None        # 响应体必须包含的关键字
    assert_json_field: Optional[Dict] = None    # JSON 字段断言，如 {"code": 0}
    assert_max_time: Optional[float] = None     # 最大响应时间（秒）

    # 变量提取规则
    extract_vars: Optional[Dict] = None

class TestCaseResponse(TestCaseCreate):
    id: int

    class Config:
        from_attributes = True