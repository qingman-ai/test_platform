# 接口自动化测试平台

基于 FastAPI 构建的接口自动化测试平台，支持用例管理、批量执行、多维度断言、测试报告生成。

## 功能特性

- **用例管理**：支持 CRUD 操作，按模块/优先级/标签筛选
- **多种请求方式**：GET / POST / PUT / DELETE，支持 Headers、Params、Body
- **参数化驱动**：支持多组参数批量执行同一用例
- **多重断言**：状态码、关键字、JSON 字段、响应时间
- **变量提取与关联**：从响应中提取变量，供后续用例使用（如 Token 传递）
- **批量执行**：异步执行 + 实时进度查询
- **测试报告**：HTML 可视化报告（ECharts 图表 + PDF 导出）
- **用户认证**：JWT Token 登录，接口权限保护
- **CI/CD**：GitHub Actions 自动化测试

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | MySQL 8.0 |
| 认证 | JWT (PyJWT) + bcrypt |
| 前端 | HTML + Jinja2 + ECharts |
| CI/CD | GitHub Actions |
| 测试 | pytest + httpx |

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置数据库
修改 `app/database.py` 中的 `DATABASE_URL`，填入你的 MySQL 连接信息。

### 3. 启动服务
```bash
uvicorn app.main:app --reload
```

### 4. 访问
- 管理界面：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目结构

```
test_platform/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI 路由入口
│   ├── models.py         # SQLAlchemy 数据模型
│   ├── schemas.py        # Pydantic 请求/响应模型
│   ├── crud.py           # 数据库操作逻辑
│   ├── database.py       # 数据库连接配置
│   └── auth.py           # JWT 认证模块
├── templates/
│   ├── index.html        # 用例管理前端页面
│   ├── login.html        # 登录/注册页面
│   └── report.html       # 测试报告页面
├── tests/
│   └── test_api.py       # 自动化测试
├── .github/
│   └── workflows/
│       └── ci.yml        # GitHub Actions 配置
├── requirements.txt
├── .gitignore
└── README.md
```

## CI/CD

项目配置了 GitHub Actions，每次推送到 `main` 分支会自动：
1. 启动 MySQL 服务
2. 安装 Python 依赖
3. 运行 pytest 测试
4. 启动服务并验证接口可用性
