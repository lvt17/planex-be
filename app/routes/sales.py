from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.sale import Sale
from app.models.product import Product
from datetime import datetime, timedelta, timezone
from app.utils.timezone import get_now_vn, timedelta
from sqlalchemy import func

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/api/sales', methods=['POST'])
@jwt_required()
def create_sale():
    """Record a sale - increment product sold quantity"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    if not product_id:
        return jsonify({'error': 'product_id là bắt buộc'}), 400
    
    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({'error': 'Không tìm thấy sản phẩm'}), 404
    
    total_price = float(product.price) * quantity
    
    sale = Sale(
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
        total_price=total_price
    )
    
    db.session.add(sale)
    db.session.commit()
    
    return jsonify({
        'sale': sale.to_dict(),
        'product': product.to_dict()
    }), 201

@sales_bp.route('/api/sales/stats', methods=['GET'])
@jwt_required()
def get_sales_stats():
    """Get sales statistics by period"""
    user_id = get_jwt_identity()
    period = request.args.get('period', 'month')
    
    now = get_now_vn()
    
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'quarter':
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start_date = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == '6months':
        if now.month <= 6:
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now.replace(month=7, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get total sales revenue
    sales_result = db.session.query(
        func.sum(Sale.total_price).label('revenue'),
        func.sum(Sale.quantity).label('quantity'),
        func.count(Sale.id).label('count')
    ).filter(
        Sale.user_id == user_id,
        Sale.sale_date >= start_date
    ).first()
    
    # Get sales breakdown by product
    breakdown = db.session.query(
        Product.name,
        func.sum(Sale.quantity).label('quantity'),
        func.sum(Sale.total_price).label('revenue')
    ).join(Product).filter(
        Sale.user_id == user_id,
        Sale.sale_date >= start_date
    ).group_by(Product.id, Product.name).all()
    
    return jsonify({
        'period': period,
        'start_date': start_date.isoformat(),
        'total_revenue': float(sales_result.revenue or 0),
        'total_quantity': int(sales_result.quantity or 0),
        'total_transactions': int(sales_result.count or 0),
        'breakdown': [
            {
                'product_name': b.name,
                'quantity': int(b.quantity),
                'revenue': float(b.revenue)
            }
            for b in breakdown
        ]
    })

@sales_bp.route('/api/sales/recent', methods=['GET'])
@jwt_required()
def get_recent_sales():
    """Get recent sales"""
    user_id = get_jwt_identity()
    limit = request.args.get('limit', 20, type=int)
    
    sales = Sale.query.filter_by(user_id=user_id).order_by(Sale.sale_date.desc()).limit(limit).all()
    
    return jsonify([s.to_dict() for s in sales])
