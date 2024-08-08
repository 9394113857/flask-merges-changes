import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, date
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, unset_jwt_cookies
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS

# Configuration settings
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Logger configuration
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

# Get the current year and month
current_year = date.today().strftime('%Y')
current_month = date.today().strftime('%m')

# Create directories for the current year and month
year_month_dir = os.path.join(logs_dir, current_year, current_month)
os.makedirs(year_month_dir, exist_ok=True)

# Define the log file name using today's date
log_file = os.path.join(year_month_dir, f'{date.today()}.log')

# Create a RotatingFileHandler with log file rotation settings
log_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s'))

# Create a logger and set its level to INFO
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add the RotatingFileHandler to the logger
logger.addHandler(log_handler)

# User model with additional fields
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

# Route definitions with CRUD operations

@app.route('/', methods=['GET'])
def test():
    logger.info('Test route accessed')
    return jsonify({"message": "Hello, World!"})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        logger.warning('Registration attempt with existing username: %s', data['username'])
        return jsonify({"message": "Username already taken"}), 400

    # Optional fields checks
    if 'email' in data and User.query.filter_by(email=data['email']).first():
        logger.warning('Registration attempt with existing email: %s', data['email'])
        return jsonify({"message": "Email already registered"}), 400
    if 'phone' in data and User.query.filter_by(phone=data['phone']).first():
        logger.warning('Registration attempt with existing phone: %s', data['phone'])
        return jsonify({"message": "Phone number already registered"}), 400

    new_user = User(
        username=data['username'],
        password=data['password'],
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address')
    )
    db.session.add(new_user)
    db.session.commit()
    logger.info('New user registered: %s', data['username'])
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    if not user:
        logger.error('Invalid login attempt for username: %s', data['username'])
        return jsonify({"message": "Invalid credentials"}), 401
    
    access_token = create_access_token(identity=user.id)
    logger.info('User logged in: %s', data['username'])
    return jsonify(access_token=access_token)

@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    db.session.add(TokenBlocklist(jti=jti, created_at=datetime.utcnow()))
    db.session.commit()
    response = jsonify({"message": "Successfully logged out"})
    unset_jwt_cookies(response)
    logger.info('User logged out with JTI: %s', jti)
    return response

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    logger.info('Accessed protected route')
    return jsonify({"message": "This is a protected route"})

@app.route('/update/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found for update: %d', user_id)
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    user.username = data.get('username', user.username)
    user.password = data.get('password', user.password)
    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    user.phone = data.get('phone', user.phone)
    user.address = data.get('address', user.address)

    db.session.commit()
    logger.info('User updated successfully: %d', user_id)
    return jsonify({"message": "User updated successfully"}), 200

############## Working User deleting route #################
# uncomment this route to delete user 

# @app.route('/user', methods=['DELETE'])
# @jwt_required()
# def delete_user():
#     user_id = get_jwt()['sub']
#     user = User.query.get(user_id)
#     db.session.delete(user)
#     db.session.commit()
#     logger.info('User deleted successfully: %d', user_id)
#     return jsonify({"message": "User deleted successfully"})

############## Working User deleting route #################

# Delete user specific information not sure:-
# @app.route('/delete/<int:user_id>', methods=['DELETE'])
# @jwt_required()
# def delete_user(user_id):
#     user = User.query.get(user_id)
#     if not user:
#         logger.error('User not found for delete: %d', user_id)
#         return jsonify({"message": "User not found"}), 404

#     # Delete specific fields for the user
#     data = request.get_json()
#     fields_to_delete = data.get('fields', [])
#     for field in fields_to_delete:
#         if hasattr(user, field):
#             setattr(user, field, None)  # Set field value to None

#     db.session.commit()
#     logger.info('User information deleted successfully: %d', user_id)
#     return jsonify({"message": "User information deleted successfully"}), 200

@app.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found for get: %d', user_id)
        return jsonify({"message": "User not found"}), 404

    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.name,
        'email': user.email,
        'phone': user.phone,
        'address': user.address
    }
    logger.info('User data retrieved successfully: %d', user_id)
    return jsonify(user_data), 200

if __name__ == '__main__':
    app.run(debug=True)
