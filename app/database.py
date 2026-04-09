from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base  # 从 models.py 引入 Base 和模型定义

# 这里把密码改成你自己安装 MySQL 时设置的 root 密码,
# %40 是 URL 编码中 @ 的表示,如果你的密码中有 @ 符号,需要替换成 %40
DATABASE_URL = "mysql+pymysql://root:Root%40123456@127.0.0.1:3306/test_platform"
               # 数据库类型+驱动：//用户名：密码@地址：端口/数据库名
engine = create_engine(
    DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(  #session表示数据库会话，SessionLocal是一个工厂函数，每次调用它都会创建一个新的数据库会话对象
    autocommit=False,
    autoflush=False,
    bind=engine
)

#Base = declarative_base()
# 自动创建所有表
Base.metadata.create_all(bind=engine)

# 生成器函数（用了yield）
def get_db():
    db = SessionLocal()
    try:
        yield db  # 将这个数据库会话对象传递给调用者，调用者可以在需要数据库操作的地方使用它
    finally:
        db.close()