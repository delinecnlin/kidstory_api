import os
from app import db
from app.models import *

# 删除现有的数据库文件
if os.path.exists('instance/app.db'):
    os.remove('instance/app.db')

# 重新创建数据库并初始化
db.create_all()
print("Database reset and initialized.")
