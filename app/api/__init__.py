from app.api.auth import bp as auth
from app.api.users import bp as users
from app.api.tasks import bp as tasks
from app.api.workspaces import bp as workspaces
from app.api.income import bp as income
from app.api.ai_integration import bp as ai_integration
from app.api.docs_export import bp as docs_export

__all__ = ['auth', 'users', 'tasks', 'workspaces', 'income', 'ai_integration', 'docs_export']