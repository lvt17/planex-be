from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.product import Product
from app.models.category import Category

products_bp = Blueprint('products', __name__)

@products_bp.route('/api/products', methods=['GET'])
@jwt_required()
def get_products():
    user_id = get_jwt_identity()
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    
    query = Product.query.filter_by(user_id=user_id)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.order_by(Product.name).all()
    return jsonify([p.to_dict() for p in products])

@products_bp.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Tên sản phẩm là bắt buộc'}), 400
    
    if not data.get('price'):
        return jsonify({'error': 'Giá sản phẩm là bắt buộc'}), 400
    
    # Validate category if provided
    if data.get('category_id'):
        category = Category.query.filter_by(id=data['category_id'], user_id=user_id).first()
        if not category:
            return jsonify({'error': 'Danh mục không tồn tại'}), 400
    
    product = Product(
        user_id=user_id,
        category_id=data.get('category_id'),
        name=data['name'],
        price=data['price'],
        stock=data.get('stock', 0),
        image_url=data.get('image_url')
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify(product.to_dict()), 201

@products_bp.route('/api/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    user_id = get_jwt_identity()
    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    
    if not product:
        return jsonify({'error': 'Không tìm thấy sản phẩm'}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        product.name = data['name']
    if 'price' in data:
        product.price = data['price']
    if 'category_id' in data:
        product.category_id = data['category_id']
    if 'stock' in data:
        product.stock = data['stock']
    if 'image_url' in data:
        product.image_url = data['image_url']
    
    db.session.commit()
    
    return jsonify(product.to_dict())

@products_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    user_id = get_jwt_identity()
    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    
    if not product:
        return jsonify({'error': 'Không tìm thấy sản phẩm'}), 404
    
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'message': 'Đã xóa sản phẩm'})
