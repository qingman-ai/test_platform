from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
import json

Base = declarative_base()  # ✅ 这里自己创建 Base

class TestCase(Base):
    __tablename__ = "test_case"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    method = Column(String(10), nullable=False)
    url = Column(String(255), nullable=False)
    headers_raw = Column("headers", Text)  #请求头，存储为 JSON 字符串
    params_raw = Column("params", Text)   #请求参数，存储为 JSON 字符串
    param_sets_raw = Column("param_sets", Text, nullable=True)  # 用于存储多组参数的字段，存储为 JSON 字符串，格式示例：[{"param1": "value1"}, {"param1": "value2"}]
    expected_status = Column(Integer)
    expected_body = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    body_raw = Column("body", Text, nullable=True)  #请求体参数，存储为 JSON 字符串

    assert_keyword = Column(String(255), nullable=True)
    assert_json_field_raw = Column("assert_json_field", Text, nullable=True)
    assert_max_time = Column(String(20), nullable=True)

    extract_vars_raw = Column("extract_vars", Text, nullable=True)

    module = Column(String(50), default="default")   # 用例所属模块
    priority = Column(Integer, default=1)           # 优先级，1-10，数字越小优先级越高
    tags = Column(Text)                              # 用例标签，多个标签用逗号分隔
    # 自动转换的 property
    @property
    def headers(self):
        return json.loads(self.headers_raw) if self.headers_raw else {}

    @headers.setter
    def headers(self, value):
        self.headers_raw = json.dumps(value) if value else None

    @property
    def params(self):
        return json.loads(self.params_raw) if self.params_raw else {}

    @params.setter
    def params(self, value):
        self.params_raw = json.dumps(value) if value else None

    @property
    def param_sets(self):
        return json.loads(self.param_sets_raw) if self.param_sets_raw else []

    @param_sets.setter
    def param_sets(self, value):
        self.param_sets_raw = json.dumps(value) if value else None

    @property
    def body(self):
        return json.loads(self.body_raw) if self.body_raw else {}

    @body.setter
    def body(self, value):
        self.body_raw = json.dumps(value) if value else None

    @property
    def assert_json_field(self):
        return json.loads(self.assert_json_field_raw) if self.assert_json_field_raw else {}

    @assert_json_field.setter
    def assert_json_field(self, value):
        self.assert_json_field_raw = json.dumps(value) if value else None

    @property
    def extract_vars(self):
        return json.loads(self.extract_vars_raw) if self.extract_vars_raw else {}

    @extract_vars.setter
    def extract_vars(self, value):
        self.extract_vars_raw = json.dumps(value) if value else None


class TestResult(Base):
    __tablename__ = "test_result"

    id = Column(Integer, primary_key=True, index=True) #主键，以为唯一标识每条测试结果记录，整张表中不会重复
    case_id = Column(Integer, nullable=False)  #不能为空
    actual_status = Column(Integer)
    actual_body = Column(Text)
    result = Column(String(20))
    run_time = Column(DateTime, server_default=func.now())
    error_message = Column(Text, nullable=True)  # 保存执行失败时的错误信息

class BatchRun(Base):
    __tablename__ = "batch_run"

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(50))
    priority = Column(Integer)
    tag = Column(String(255))
    status = Column(String(20), default="pending")  # pending, running, finished，批量任务的执行状态
    total_cases = Column(Integer, default=0)  #总共有多少个用例符合条件
    finished_cases = Column(Integer, default=0)  #已经执行了多少个用例
    created_at = Column(DateTime, server_default=func.now())  #创建时间
    finished_at = Column(DateTime, nullable=True)  #批量任务完成时间，初始为null，任务完成后更新这个字段

class User(Base):
    """用户表：存储平台的注册用户"""
    __tablename__ = "user"
 
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # 存储加密后的密码
    role = Column(String(20), default="user")  # 角色：admin / user
    created_at = Column(DateTime, server_default=func.now())