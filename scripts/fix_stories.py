import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import db, app
from app.models import Story

app = create_app()
app.app_context().push()

def fix_stories():
    # 获取前4个故事
    stories = Story.query.limit(4).all()
    for story in stories:
        # 将故事分配给其他用户并设置为开放状态
        story.user_id = 2  # 假设用户ID 2是其他用户
        story.is_open = True
    db.session.commit()
    print("Stories updated successfully")

if __name__ == "__main__":
    fix_stories()
