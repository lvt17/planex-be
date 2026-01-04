import os
from flask import Flask, jsonify
from app.config import config
from app.extensions import db, migrate, jwt, mail, cors


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    # CORS setup - temporarily allow all for debugging
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",  # Allow all origins temporarily
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Admin-Token"],
            "supports_credentials": False,  # Must be False when using "*"
            "expose_headers": ["Content-Type", "Authorization"],
            "max_age": 3600
        }
    })
    
    # Register blueprints
    from app.api import auth, users, tasks, workspaces, income, ai_integration, docs_export, account, content_api, feedback_api, team_api, notification_api, subtask_api, projects, sse, badge_api
    from app.routes.categories import categories_bp
    from app.routes.products import products_bp
    from app.routes.sales import sales_bp
    from app.routes.upload import bp as upload_bp
    
    app.register_blueprint(auth, url_prefix='/api/auth')
    app.register_blueprint(users, url_prefix='/api/users')
    app.register_blueprint(tasks, url_prefix='/api/tasks')
    app.register_blueprint(workspaces, url_prefix='/api/workspaces')
    app.register_blueprint(income, url_prefix='/api/income')
    app.register_blueprint(ai_integration, url_prefix='/api/mcp')
    app.register_blueprint(docs_export, url_prefix='/api/documents')
    app.register_blueprint(account, url_prefix='/api/accounts')
    app.register_blueprint(content_api, url_prefix='/api/content')
    app.register_blueprint(feedback_api.bp, url_prefix='/api/feedback')
    app.register_blueprint(team_api.bp, url_prefix='/api/teams', strict_slashes=False)
    app.register_blueprint(notification_api.bp, url_prefix='/api/notifications')
    app.register_blueprint(subtask_api.bp, url_prefix='/api')
    app.register_blueprint(projects)  # Project API - routes defined in blueprint
    app.register_blueprint(sse, url_prefix='/api')  # SSE endpoint
    app.register_blueprint(badge_api.bp, url_prefix='/api/admin/badges')
    app.register_blueprint(categories_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    
    # Health check
    @app.route('/api/health')
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy", "version": "1.0.0"}), 200
    
    return app
