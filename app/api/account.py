from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.account import Account, AccountStore
from app.models.user import User
from app.models.storage import Storage
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import json

bp = Blueprint('accounts', __name__)

def get_fernet(passkey: str, salt: bytes):
    """Derive a Fernet key from a passkey and salt"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passkey.encode()))
    return Fernet(key)

@bp.route('', methods=['GET'])
@jwt_required()
def get_accounts():
    """Get all accounts for the current user (only platform and username)"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    if not user.storage_id:
        return jsonify([])
    
    # Get all accounts linked to this user's storage
    account_links = AccountStore.query.filter_by(storage_id=user.storage_id).all()
    accounts = [link.account.to_dict() for link in account_links]
    
    return jsonify(accounts)

@bp.route('', methods=['POST'])
@jwt_required()
def create_account():
    """Create a new account entry encrypted with passkey"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    passkey = data.get('passkey')
    platform = data.get('platform')
    username = data.get('username')
    password = data.get('password')
    
    if not all([passkey, platform, username, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Ensure user has a storage link and a salt (storage_key)
    if not user.storage_key:
        user.storage_key = os.urandom(16)
        db.session.flush()
    
    if not user.storage_id:
        storage = Storage(type='account_manager')
        db.session.add(storage)
        db.session.flush()
        user.storage_id = storage.id
    
    # Encrypt the password and content
    try:
        f = get_fernet(passkey, user.storage_key)
        encrypted_password = f.encrypt(password.encode()).decode()
        
        content = data.get('content', '')
        encrypted_content = f.encrypt(content.encode()).decode() if content else None
    except Exception as e:
        return jsonify({'error': 'Encryption failed'}), 500
    
    new_account = Account(
        platform=platform,
        username=username,
        password=encrypted_password,
        content=encrypted_content,
        noted=data.get('noted', '')
    )
    db.session.add(new_account)
    db.session.flush()
    
    # Link to user's storage
    link = AccountStore(account_id=new_account.id, storage_id=user.storage_id)
    db.session.add(link)
    db.session.commit()
    
    return jsonify(new_account.to_dict()), 201

@bp.route('/<int:account_id>/decrypt', methods=['POST'])
@jwt_required()
def decrypt_account(account_id):
    """Decrypt an account password using the passkey"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    passkey = data.get('passkey')
    if not passkey:
        return jsonify({'error': 'Passkey required'}), 400
    
    # Verify the account belongs to the user
    link = AccountStore.query.filter_by(account_id=account_id, storage_id=user.storage_id).first()
    if not link:
        return jsonify({'error': 'Account not found or access denied'}), 404
    
    account = link.account
    
    try:
        f = get_fernet(passkey, user.storage_key)
        decrypted_password = f.decrypt(account.password.encode()).decode()
        decrypted_content = f.decrypt(account.content.encode()).decode() if account.content else None
        
        return jsonify({
            'password': decrypted_password,
            'content': decrypted_content
        })
    except Exception:
        return jsonify({'error': 'Invalid passkey'}), 401

@bp.route('/<int:account_id>', methods=['DELETE'])
@jwt_required()
def delete_account(account_id):
    """Delete an account entry"""
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)
    
    link = AccountStore.query.filter_by(account_id=account_id, storage_id=user.storage_id).first()
    if not link:
        return jsonify({'error': 'Account not found'}), 404
    
    account = link.account
    db.session.delete(link)
    db.session.delete(account)
    db.session.commit()
    
    return jsonify({'message': 'Account deleted successfully'})
