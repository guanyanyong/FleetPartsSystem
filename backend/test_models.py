import asyncio
from app.db.session import engine
from app.db.base import Base
from app.models import *  # noqa

async def main():
    async with engine.begin() as conn:
        # 只检查模型定义，不建表
        print("已注册表：", list(Base.metadata.tables.keys()))

asyncio.run(main())