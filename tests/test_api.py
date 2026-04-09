# tests/test_api.py
# 自动化测试：用 pytest + httpx 测试平台自身的接口
# GitHub Actions 会自动运行这些测试

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """基础健康检查"""

    def test_db_connection(self):
        """测试数据库连接"""
        resp = client.get("/db-test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"] == 1


class TestAuth:
    """用户认证测试"""

    def test_register(self):
        """测试用户注册"""
        resp = client.post("/api/register", json={
            "username": "testuser_ci",
            "password": "test123456"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "注册成功"

    def test_register_duplicate(self):
        """测试重复注册"""
        # 先注册一次
        client.post("/api/register", json={
            "username": "testuser_dup",
            "password": "test123456"
        })
        # 再注册同名用户
        resp = client.post("/api/register", json={
            "username": "testuser_dup",
            "password": "test123456"
        })
        assert resp.status_code == 400

    def test_login_success(self):
        """测试登录成功"""
        # 先注册
        client.post("/api/register", json={
            "username": "testuser_login",
            "password": "test123456"
        })
        # 再登录
        resp = client.post("/api/login", json={
            "username": "testuser_login",
            "password": "test123456"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["username"] == "testuser_login"

    def test_login_wrong_password(self):
        """测试密码错误"""
        client.post("/api/register", json={
            "username": "testuser_wp",
            "password": "test123456"
        })
        resp = client.post("/api/login", json={
            "username": "testuser_wp",
            "password": "wrongpassword"
        })
        assert resp.status_code == 401


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

    def test_create_case(self):
        """测试创建用例"""
        token = self._get_token()
        resp = client.post("/cases/", json={
            "name": "CI测试用例",
            "method": "GET",
            "url": "http://localhost:8000/db-test",
            "expected_status": 200,
            "module": "ci_test",
            "priority": 1
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "CI测试用例"
        assert data["id"] is not None

    def test_list_cases(self):
        """测试查询用例列表"""
        resp = client.get("/cases/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_delete_case(self):
        """测试创建后删除用例"""
        token = self._get_token()
        # 创建
        resp = client.post("/cases/", json={
            "name": "待删除用例",
            "method": "GET",
            "url": "http://localhost:8000/db-test",
            "expected_status": 200
        }, headers={"Authorization": f"Bearer {token}"})
        case_id = resp.json()["id"]

        # 删除
        resp = client.delete(f"/cases/{case_id}",
                             headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_unauthorized_create(self):
        """测试未登录创建用例（应该被拒绝）"""
        fresh_client = TestClient(app, cookies={})
        resp = fresh_client.post("/cases/", json={
            "name": "未授权用例",
            "method": "GET",
            "url": "http://localhost:8000/db-test"
        })
        assert resp.status_code in [401, 403]
