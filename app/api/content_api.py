import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.content import Document, Spreadsheet
from app.models.whiteboard import Whiteboard
from app.models.task import Task

bp = Blueprint('content', __name__)

# Portfolio Endpoints
@bp.route('/portfolio', methods=['GET'])
@jwt_required()
def get_portfolio():
    user_id = get_jwt_identity()
    tasks = Task.query.filter_by(user_id=user_id, show_in_portfolio=True).all()
    return jsonify([task.to_dict() for task in tasks])

@bp.route('/tasks/<int:task_id>/portfolio', methods=['PUT'])
@jwt_required()
def toggle_portfolio(task_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    task = Task.query.filter_by(id=task_id, user_id=user_id).first_or_404()
    
    task.show_in_portfolio = data.get('show', not task.show_in_portfolio)
    if 'thumbnail' in data:
        task.portfolio_thumbnail = data['thumbnail']
    
    db.session.commit()
    return jsonify(task.to_dict())

# Document Endpoints
@bp.route('/documents', methods=['GET'])
@jwt_required()
def get_documents():
    user_id = get_jwt_identity()
    docs = Document.query.filter_by(user_id=user_id).all()
    return jsonify([doc.to_dict() for doc in docs])

@bp.route('/documents', methods=['POST'])
@jwt_required()
def create_document():
    user_id = get_jwt_identity()
    data = request.get_json()
    doc = Document(
        user_id=user_id,
        title=data.get('title', 'Untitled Document'),
        content=data.get('content', '')
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify(doc.to_dict()), 201

@bp.route('/documents/<int:doc_id>', methods=['PUT'])
@jwt_required()
def update_document(doc_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    doc = Document.query.filter_by(id=doc_id, user_id=user_id).first_or_404()
    
    if 'title' in data:
        doc.title = data['title']
    if 'content' in data:
        doc.content = data['content']
        
    db.session.commit()
    return jsonify(doc.to_dict())

@bp.route('/documents/<int:doc_id>', methods=['DELETE'])
@jwt_required()
def delete_document(doc_id):
    user_id = get_jwt_identity()
    doc = Document.query.filter_by(id=doc_id, user_id=user_id).first_or_404()
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted'})

# Spreadsheet Endpoints
@bp.route('/spreadsheets', methods=['GET'])
@jwt_required()
def get_spreadsheets():
    user_id = get_jwt_identity()
    sheets = Spreadsheet.query.filter_by(user_id=user_id).all()
    return jsonify([sheet.to_dict() for sheet in sheets])

@bp.route('/spreadsheets', methods=['POST'])
@jwt_required()
def create_spreadsheet():
    user_id = get_jwt_identity()
    data = request.get_json()
    sheet = Spreadsheet(
        user_id=user_id,
        title=data.get('title', 'Untitled Spreadsheet'),
        data=data.get('data', [['', '', ''], ['', '', ''], ['', '', '']])
    )
    db.session.add(sheet)
    db.session.commit()
    return jsonify(sheet.to_dict()), 201

@bp.route('/spreadsheets/<int:sheet_id>', methods=['PUT'])
@jwt_required()
def update_spreadsheet(sheet_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    sheet = Spreadsheet.query.filter_by(id=sheet_id, user_id=user_id).first_or_404()
    
    if 'title' in data:
        sheet.title = data['title']
    if 'data' in data:
        sheet.data = data['data']
        
    db.session.commit()
    return jsonify(sheet.to_dict())

@bp.route('/spreadsheets/<int:sheet_id>', methods=['DELETE'])
@jwt_required()
def delete_spreadsheet(sheet_id):
    user_id = get_jwt_identity()
    sheet = Spreadsheet.query.filter_by(id=sheet_id, user_id=user_id).first_or_404()
    db.session.delete(sheet)
    db.session.commit()
    return jsonify({'message': 'Spreadsheet deleted'})

# Config Endpoints
@bp.route('/config/tinymce', methods=['GET'])
@jwt_required()
def get_tinymce_config():
    return jsonify({
        'api_key': os.getenv('TINYMCE_API_KEY', 'no-api-key')
    })

# Whiteboard Endpoints
@bp.route('/whiteboards', methods=['GET'])
@jwt_required()
def get_whiteboards():
    user_id = get_jwt_identity()
    boards = Whiteboard.query.filter_by(user_id=user_id).all()
    return jsonify([board.to_dict() for board in boards])

@bp.route('/whiteboards', methods=['POST'])
@jwt_required()
def create_whiteboard():
    user_id = get_jwt_identity()
    data = request.get_json()
    board = Whiteboard(
        user_id=user_id,
        name=data.get('name', 'Untitled Whiteboard'),
        data=data.get('data', {})
    )
    db.session.add(board)
    db.session.commit()
    return jsonify(board.to_dict()), 201

@bp.route('/whiteboards/<int:board_id>', methods=['PUT'])
@jwt_required()
def update_whiteboard(board_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    
    try:
        board = Whiteboard.query.filter_by(id=board_id, user_id=user_id).first()
        if not board:
            print(f"Whiteboard {board_id} not found for user {user_id}")
            return jsonify({'error': 'Whiteboard not found'}), 404
        
        if 'name' in data:
            board.name = data['name']
        if 'data' in data:
            # data might be a dict or a stringified JSON
            new_data = data['data']
            if isinstance(new_data, str):
                import json
                try:
                    new_data = json.loads(new_data)
                except:
                    pass
            board.data = new_data
            
        db.session.commit()
        return jsonify({
            'message': 'Whiteboard updated successfully',
            'id': board.id,
            'updated_at': board.updated_at.isoformat() if board.updated_at else None
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error updating whiteboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/whiteboards/<int:board_id>', methods=['DELETE'])
@jwt_required()
def delete_whiteboard(board_id):
    user_id = get_jwt_identity()
    board = Whiteboard.query.filter_by(id=board_id, user_id=user_id).first_or_404()
    db.session.delete(board)
    db.session.commit()
    return jsonify({'message': 'Whiteboard deleted'})
