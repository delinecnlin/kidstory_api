import os
from app import create_app, db
from app.models import *

# 创建应用程序实例
app = create_app()

# 在应用程序上下文中关闭数据库连接并删除现有的数据库文件
with app.app_context():
    db.session.remove()
    db.engine.dispose()
    if os.path.exists('instance/app.db'):
        os.remove('instance/app.db')

# 在应用程序上下文中重新创建数据库并初始化
with app.app_context():
    db.create_all()
    print("Database reset and initialized.")
