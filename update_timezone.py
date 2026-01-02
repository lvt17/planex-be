import os
import re

def update_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    
    # Add import if missing and datetime.utcnow is found
    if 'datetime.utcnow' in content and 'from app.utils.timezone import get_now_vn' not in content:
        # Try to find where to insert the import
        if 'from datetime import datetime' in content:
            new_content = content.replace('from datetime import datetime', 'from datetime import datetime, timedelta, timezone\nfrom app.utils.timezone import get_now_vn')
        elif 'import datetime' in content:
            new_content = content.replace('import datetime', 'import datetime\nfrom app.utils.timezone import get_now_vn')
        else:
            # Insert at the top
            new_content = 'from app.utils.timezone import get_now_vn\n' + content

    # Replace datetime.utcnow() with get_now_vn()
    new_content = new_content.replace('datetime.utcnow()', 'get_now_vn()')
    # Replace datetime.utcnow with get_now_vn (for SQLAlchemy defaults)
    new_content = new_content.replace('default=datetime.utcnow', 'default=get_now_vn')
    new_content = new_content.replace('onupdate=datetime.utcnow', 'onupdate=get_now_vn')

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

files_to_update = [
    'app/models/project.py',
    'app/models/team.py',
    'app/models/notification.py',
    'app/models/member_rating.py',
    'app/models/income.py',
    'app/models/user.py',
    'app/models/content.py',
    'app/models/whiteboard.py',
    'app/models/product.py',
    'app/models/account.py',
    'app/models/user_feedback.py',
    'app/models/image.py',
    'app/models/category.py',
    'app/models/sale.py',
    'app/models/storage.py',
    'app/api/team_api.py',
    'app/api/notification_api.py',
    'app/api/income.py',
    'app/api/tasks.py',
    'app/api/auth.py',
    'app/api/ai_integration.py',
    'app/api/docs_export.py',
    'app/routes/sales.py'
]

for file_path in files_to_update:
    if os.path.exists(file_path):
        updated = update_file(file_path)
        if updated:
            print(f"Updated {file_path}")
        else:
            print(f"No changes in {file_path}")
    else:
        print(f"File not found: {file_path}")
