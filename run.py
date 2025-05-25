import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, date
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity, unset_jwt_cookies
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# App Initialization
app = Flask(__name__)
CORS(app)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Logging Setup
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
year_month_dir = os.path.join(logs_dir, date.today().strftime('%Y'), date.today().strftime('%m'))
os.makedirs(year_month_dir, exist_ok=True)
log_file = os.path.join(year_month_dir, f'{date.today()}.log')
log_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    address = db.Column(db.String(255), nullable=True)

class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    token = TokenBlocklist.query.filter_by(jti=jti).first()
    return token is not None

# Routes

@app.route('/', methods=['GET'])
def test():
    logger.info('Test route accessed')
    return jsonify({"status": "success", "message": "Hello, World!"})

# Registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        logger.warning('Username already exists: %s', data['username'])
        return jsonify({"status": "error", "message": "Username already taken"}), 400

    if 'email' in data and User.query.filter_by(email=data['email']).first():
        logger.warning('Email already exists: %s', data['email'])
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    if 'phone' in data and User.query.filter_by(phone=data['phone']).first():
        logger.warning('Phone already exists: %s', data['phone'])
        return jsonify({"status": "error", "message": "Phone number already registered"}), 400

    hashed_password = generate_password_hash(data['password'])

    new_user = User(
        username=data['username'],
        password=hashed_password,
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address')
    )

    db.session.add(new_user)
    db.session.commit()
    logger.info('User registered: %s', data['username'])
    return jsonify({"status": "success", "message": "User registered successfully"}), 201

# Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        logger.error('Invalid login attempt: %s', data['username'])
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    logger.info('User logged in: %s', user.username)
    return jsonify({"status": "success", "access_token": access_token}), 200

# Logout
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    db.session.add(TokenBlocklist(jti=jti, created_at=datetime.utcnow()))
    db.session.commit()
    response = jsonify({"status": "success", "message": "Successfully logged out"})
    unset_jwt_cookies(response)
    logger.info('User logged out with JTI: %s', jti)
    return response

# Get User Details
@app.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found: %d', user_id)
        return jsonify({"status": "error", "message": "User not found"}), 404

    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.name,
        'email': user.email,
        'phone': user.phone,
        'address': user.address
    }
    logger.info('User retrieved: %d', user_id)
    return jsonify({"status": "success", "user": user_data}), 200

# Update User
@app.route('/update/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found: %d', user_id)
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json()
    user.username = data.get('username', user.username)

    if 'password' in data:
        user.password = generate_password_hash(data['password'])

    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    user.phone = data.get('phone', user.phone)
    user.address = data.get('address', user.address)

    db.session.commit()
    logger.info('User updated: %d', user_id)
    return jsonify({"status": "success", "message": "User updated successfully"}), 200

# Delete Entire User
@app.route('/user', methods=['DELETE'])
@jwt_required()
def delete_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found for deletion: %d', user_id)
        return jsonify({"status": "error", "message": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    logger.info('User deleted: %d', user_id)
    return jsonify({"status": "success", "message": "User deleted successfully"}), 200

# Selective Delete Fields
@app.route('/delete/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user_fields(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found for selective delete: %d', user_id)
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json()
    fields_to_delete = data.get('fields', [])
    for field in fields_to_delete:
        if hasattr(user, field):
            setattr(user, field, None)

    db.session.commit()
    logger.info('User fields deleted for: %d', user_id)
    return jsonify({"status": "success", "message": "User information deleted successfully"}), 200

# Protected Route Example
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    logger.info('Protected route accessed')
    return jsonify({"status": "success", "message": "This is a protected route"}), 200

# Main
if __name__ == '__main__':
    app.run(debug=True)

