import os
from flask import Flask
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
    mail.init_app(app)
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "https://*.vercel.app"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    from app.api import auth, users, tasks, workspaces, income, ai_integration, docs_export
    
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(users.bp, url_prefix='/api/users')
    app.register_blueprint(tasks.bp, url_prefix='/api/tasks')
    app.register_blueprint(workspaces.bp, url_prefix='/api/workspaces')
    app.register_blueprint(income.bp, url_prefix='/api/income')
    app.register_blueprint(ai_integration.bp, url_prefix='/api/mcp')
    app.register_blueprint(docs_export.bp, url_prefix='/api/documents')
    
    # Health check
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'version': '1.0.0'}
    
    return app
