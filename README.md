# Planex Backend

API backend cho ứng dụng Planex - Quản lý công việc thông minh.

## Tech Stack
- Python Flask
- PostgreSQL + Supabase
- JWT Authentication
- Cloudinary (Image storage)
- Resend (Email)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env

# Edit .env with your credentials
nano .env

# Run migrations
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Run development server
python run.py
```

## API Endpoints

### Auth
- `POST /api/auth/register` - Đăng ký
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/forgot-password` - Quên mật khẩu
- `POST /api/auth/reset-password` - Đặt lại mật khẩu

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/:id` - Get task
- `PUT /api/tasks/:id` - Update task
- `DELETE /api/tasks/:id` - Delete task

### AI Integration (MCP)
- `GET /api/mcp/tasks` - AI query tasks
- `GET /api/mcp/tasks/:id` - AI get task detail
- `PUT /api/mcp/tasks/:id/progress` - AI update progress
- `GET /api/mcp/context` - AI get current context

### Documents & Whiteboard
- `GET /api/documents/task/:id/export/word` - Export task to Word document
- `POST /api/documents/task/:id/export/gg-docs` - Export task to Google Docs
- `POST /api/documents/task/:id/export/gg-forms` - Create Google Form for task
- `POST /api/documents/whiteboard/create` - Create whiteboard session
- `GET /api/documents/whiteboard/:id` - Get whiteboard
- `POST /api/documents/whiteboard/:id/export` - Export whiteboard
- `GET /api/documents/whiteboard/:id/elements` - Get whiteboard elements
- `POST /api/documents/whiteboard/:id/elements` - Add element to whiteboard
- `PUT /api/documents/whiteboard/:id/elements/:element_id` - Update whiteboard element
- `DELETE /api/documents/whiteboard/:id/elements/:element_id` - Remove element from whiteboard
- `GET /api/documents/whiteboard/user` - Get all user whiteboards

## Environment Variables

See `.env.example` for required configuration.

## License
MIT
