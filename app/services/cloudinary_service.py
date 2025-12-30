import cloudinary
import cloudinary.uploader
from flask import current_app


def init_cloudinary():
    """Initialize Cloudinary with config"""
    cloudinary.config(
        cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
        api_key=current_app.config['CLOUDINARY_API_KEY'],
        api_secret=current_app.config['CLOUDINARY_API_SECRET']
    )


def upload_image(file, folder='uploads'):
    """
    Upload image to Cloudinary
    
    Args:
        file: File object from request.files
        folder: Folder name in Cloudinary
        
    Returns:
        dict with url and public_id
    """
    init_cloudinary()
    
    result = cloudinary.uploader.upload(
        file,
        folder=f"planex/{folder}",
        resource_type="image",
        allowed_formats=['jpg', 'jpeg', 'png', 'gif', 'webp'],
        transformation=[
            {'width': 1024, 'crop': 'limit'},
            {'quality': 'auto:good'}
        ]
    )
    
    return {
        'url': result['secure_url'],
        'public_id': result['public_id'],
        'width': result.get('width'),
        'height': result.get('height')
    }


def delete_image(public_id):
    """Delete image from Cloudinary"""
    init_cloudinary()
    result = cloudinary.uploader.destroy(public_id)
    return result.get('result') == 'ok'
