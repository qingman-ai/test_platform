# 接口自动化测试平台

一套基于 FastAPI 的 B/S 架构接口自动化测试平台，覆盖用例管理、接口执行、定时调度、测试报告、用例导入导出等完整测试流程。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | MySQL |
| 用户认证 | JWT (PyJWT) + bcrypt |
| 定时调度 | APScheduler |
| 前端 | Jinja2 模板 + 原生 JS |
| 图表 | ECharts |
| 测试 | pytest |
| CI/CD | GitHub Actions |

## 功能特性

### 用例管理
- 用例增删改查，支持按模块、优先级、标签多维筛选
- 支持 GET / POST / PUT / DELETE 等请求方法
- 支持请求头、查询参数、请求体、多组参数化配置

### 接口执行
- 单条执行：即时发送请求并返回断言结果
- 批量执行：后台异步执行 + 实时进度轮询
- 多重断言：状态码、关键字、JSON 字段、响应时间
- 变量提取：从响应中提取变量，实现跨用例关联（接口链路测试）

### 定时任务调度
- 基于 APScheduler 实现 cron 表达式定时执行
- 支持按模块筛选执行范围
- 任务启用/禁用切换、手动立即触发
- 服务启动时自动加载已有任务

### 用例导入导出
- 支持 Excel (.xlsx) 和 YAML (.yaml) 两种格式
- 导出支持按模块筛选，Excel 含格式化表头和自动列宽
- 导入自动校验必填字段，跳过无效数据并返回错误详情

### 测试报告
- ECharts 可视化图表（通过率饼图、模块分布统计）
- 支持 PDF 导出
- 失败用例详情展示

### 用户认证
- JWT Token 认证，支持注册/登录/退出
- bcrypt 密码加密存储
- 写操作接口权限保护

### CI/CD
- GitHub Actions 自动化流水线
- 代码推送自动触发 pytest 测试（9 个测试用例）
- 测试通过后自动标记构建状态

## 项目结构

```
test_platform/
├── app/
│   ├── __init__.py
│   ├── main.py              # 路由入口（用例/认证/定时任务/导入导出）
│   ├── models.py            # 数据模型（TestCase/TestResult/BatchRun/User/ScheduleJob）
│   ├── schemas.py           # Pydantic 请求/响应模型
│   ├── crud.py              # 业务逻辑（用例CRUD、执行、批量执行、变量提取）
│   ├── database.py          # 数据库连接配置
│   ├── auth.py              # JWT 认证模块
│   ├── scheduler.py         # APScheduler 定时调度模块
│   └── export_import.py     # 用例导入导出模块（Excel/YAML）
├── templates/
│   ├── index.html           # 用例管理 + 定时任务前端页面（深色主题）
│   ├── login.html           # 登录/注册页面
│   └── report.html          # 测试报告页面（ECharts 图表 + PDF 导出）
├── tests/
│   ├── __init__.py
│   └── test_api.py          # pytest 单元测试
├── .github/workflows/
│   └── ci.yml               # GitHub Actions CI 配置
├── requirements.txt
├── README.md
└── .gitignore
```

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 5.7+

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/qingman-ai/test_platform.git
cd test_platform
```

2. **创建虚拟环境**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置数据库**

在 MySQL 中创建数据库：

```sql
CREATE DATABASE test_platform DEFAULT CHARACTER SET utf8mb4;
```

修改 `app/database.py` 中的数据库连接信息：

```python
DATABASE_URL = "mysql+pymysql://用户名:密码@127.0.0.1:3306/test_platform"
```

5. **启动服务**

```bash
uvicorn app.main:app --reload
```

访问 http://localhost:8000 即可使用，首次使用需先注册账号。

### 运行测试

```bash
pytest tests/ -v
```

## API 接口一览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/cases/` | 查询用例列表（支持筛选） | - |
| POST | `/cases/` | 创建用例 | 需要 |
| PUT | `/cases/{id}` | 编辑用例 | 需要 |
| DELETE | `/cases/{id}` | 删除用例 | 需要 |
| POST | `/run/{id}` | 执行单条用例 | 需要 |
| POST | `/run/` | 批量执行用例 | 需要 |
| GET | `/run/status/{batch_id}` | 查询批量执行进度 | - |
| GET | `/run/report/html/{batch_id}` | 查看 HTML 测试报告 | - |
| POST | `/api/register` | 用户注册 | - |
| POST | `/api/login` | 用户登录 | - |
| GET | `/api/jobs` | 查询定时任务列表 | - |
| POST | `/api/jobs` | 创建定时任务 | 需要 |
| PUT | `/api/jobs/{id}` | 编辑定时任务 | 需要 |
| DELETE | `/api/jobs/{id}` | 删除定时任务 | 需要 |
| POST | `/api/jobs/{id}/toggle` | 启用/禁用定时任务 | 需要 |
| POST | `/api/jobs/{id}/run` | 手动触发定时任务 | 需要 |
| GET | `/api/export/excel` | 导出用例为 Excel | - |
| GET | `/api/export/yaml` | 导出用例为 YAML | - |
| POST | `/api/import/excel` | 从 Excel 导入用例 | 需要 |
| POST | `/api/import/yaml` | 从 YAML 导入用例 | 需要 |

## 许可证

MIT License
