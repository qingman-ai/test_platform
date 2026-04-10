# tests/test_api.py
# 自动化测试：用 pytest + httpx + allure 测试平台自身的接口
# GitHub Actions 会自动运行这些测试并生成 Allure 报告

import pytest
import allure
from fastapi.testclient import TestClient
from app.main import app
import time

client = TestClient(app)


@allure.epic("接口自动化测试平台")
@allure.feature("基础健康检查")
class TestHealthCheck:
    """基础健康检查"""

    @allure.story("数据库连接")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("验证数据库连接正常")
    def test_db_connection(self):
        with allure.step("发送数据库连接测试请求"):
            resp = client.get("/db-test")

        with allure.step("验证连接成功"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["result"] == 1
            allure.attach(str(data), name="响应数据", attachment_type=allure.attachment_type.JSON)


@allure.epic("接口自动化测试平台")
@allure.feature("用户认证")
class TestAuth:
    """用户认证测试"""

    @allure.story("用户注册")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("注册新用户-成功")
    def test_register(self):
        with allure.step("发送注册请求"):
            username = f"testuser_ci_{int(time.time())}"  # 确保用户名唯一
            resp = client.post("/api/register", json={
                "username": username,
                "password": "test123456"
            })

        with allure.step("验证注册成功"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["message"] == "注册成功"
            allure.attach(str(data), name="响应数据", attachment_type=allure.attachment_type.JSON)

    @allure.story("用户注册")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("重复注册同名用户-失败")
    def test_register_duplicate(self):
        with allure.step("第一次注册"):
            client.post("/api/register", json={
                "username": "testuser_dup",
                "password": "test123456"
            })

        with allure.step("使用相同用户名再次注册"):
            resp = client.post("/api/register", json={
                "username": "testuser_dup",
                "password": "test123456"
            })

        with allure.step("验证返回400错误"):
            assert resp.status_code == 400
            allure.attach(str(resp.json()), name="错误响应", attachment_type=allure.attachment_type.JSON)

    @allure.story("用户登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("使用正确密码登录-成功")
    def test_login_success(self):
        with allure.step("先注册一个用户"):
            client.post("/api/register", json={
                "username": "testuser_login",
                "password": "test123456"
            })

        with allure.step("使用正确密码登录"):
            resp = client.post("/api/login", json={
                "username": "testuser_login",
                "password": "test123456"
            })

        with allure.step("验证登录成功并返回token"):
            assert resp.status_code == 200
            data = resp.json()
            assert "token" in data
            assert data["username"] == "testuser_login"
            allure.attach(str(data), name="登录响应", attachment_type=allure.attachment_type.JSON)

    @allure.story("用户登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("使用错误密码登录-失败")
    def test_login_wrong_password(self):
        with allure.step("先注册用户"):
            client.post("/api/register", json={
                "username": "testuser_wp",
                "password": "test123456"
            })

        with allure.step("使用错误密码登录"):
            resp = client.post("/api/login", json={
                "username": "testuser_wp",
                "password": "wrongpassword"
            })

        with allure.step("验证返回401未授权"):
            assert resp.status_code == 401
            allure.attach(str(resp.json()), name="错误响应", attachment_type=allure.attachment_type.JSON)


@allure.epic("接口自动化测试平台")
@allure.feature("用例管理")
class TestCases:
    """用例管理测试"""

    def _get_token(self):
        """辅助方法：注册并登录，返回 token"""
        client.post("/api/register", json={
            "username": "testuser_cases",
            "password": "test123456"
        })
        resp = client.post("/api/login", json={
            "username": "testuser_cases",
            "password": "test123456"
        })
        return resp.json()["token"]

    @allure.story("创建用例")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("创建GET请求用例")
    def test_create_case(self):
        with allure.step("获取认证token"):
            token = self._get_token()

        with allure.step("构造用例数据并发送创建请求"):
            payload = {
                "name": "CI测试用例",
                "method": "GET",
                "url": "http://localhost:8000/db-test",
                "expected_status": 200,
                "module": "ci_test",
                "priority": 1
            }
            allure.attach(str(payload), name="请求数据", attachment_type=allure.attachment_type.JSON)
            resp = client.post("/cases/", json=payload,
                               headers={"Authorization": f"Bearer {token}"})

        with allure.step("验证创建成功"):
            assert resp.status_code == 200
            data = resp.json()
            assert data["name"] == "CI测试用例"
            assert data["id"] is not None
            allure.attach(str(data), name="响应数据", attachment_type=allure.attachment_type.JSON)

    @allure.story("查询用例")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("查询用例列表")
    def test_list_cases(self):
        with allure.step("发送查询请求"):
            resp = client.get("/cases/")

        with allure.step("验证返回列表格式"):
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            allure.attach(f"共{len(data)}条用例", name="用例数量", attachment_type=allure.attachment_type.TEXT)

    @allure.story("删除用例")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("创建用例后删除")
    def test_create_and_delete_case(self):
        with allure.step("获取认证token"):
            token = self._get_token()

        with allure.step("创建一条测试用例"):
            resp = client.post("/cases/", json={
                "name": "待删除用例",
                "method": "GET",
                "url": "http://localhost:8000/db-test",
                "expected_status": 200
            }, headers={"Authorization": f"Bearer {token}"})
            case_id = resp.json()["id"]
            allure.attach(f"用例ID: {case_id}", name="创建结果", attachment_type=allure.attachment_type.TEXT)

        with allure.step(f"删除用例 ID={case_id}"):
            resp = client.delete(f"/cases/{case_id}",
                                 headers={"Authorization": f"Bearer {token}"})

        with allure.step("验证删除成功"):
            assert resp.status_code == 200
            allure.attach(str(resp.json()), name="删除响应", attachment_type=allure.attachment_type.JSON)

    @allure.story("权限控制")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("未登录用户创建用例-被拒绝")
    def test_unauthorized_create(self):
        with allure.step("不携带token直接创建用例"):
            fresh_client = TestClient(app, cookies={})
            resp = fresh_client.post("/cases/", json={
                "name": "未授权用例",
                "method": "GET",
                "url": "http://localhost:8000/db-test"
            })

        with allure.step("验证返回401或403"):
            assert resp.status_code in [401, 403]
            allure.attach(f"状态码: {resp.status_code}", name="拒绝结果", attachment_type=allure.attachment_type.TEXT)
