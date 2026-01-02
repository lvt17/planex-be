import os
from app import create_app
from app.extensions import db

app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    if os.getenv('FLASK_ENV') == 'testing':
        with app.app_context():
            db.create_all()
    app.run(host='0.0.0.0', port=5001)
