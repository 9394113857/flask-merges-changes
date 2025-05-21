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

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Logging
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
    return jsonify({"message": "Hello, World!"})

@app.route('/register', methods=['POST'])
def register():
    # Here is where Flask receives the JSON from Angular/Postman.
    # Data is now a Python dictionary.
    data = request.get_json() # <- Click here and press F9 to set a breakpoint
    if User.query.filter_by(username=data['username']).first(): # 🔍 This line checks: Does a user with this username already exist?
        logger.warning('Username already exists: %s', data['username'])
        return jsonify({"message": "Username already taken"}), 400

    if 'email' in data and User.query.filter_by(email=data['email']).first(): # Checks if email is present and already used.
        logger.warning('Email already exists: %s', data['email'])
        return jsonify({"message": "Email already registered"}), 400
    if 'phone' in data and User.query.filter_by(phone=data['phone']).first(): # Checks if phone number is already used.
        logger.warning('Phone already exists: %s', data['phone'])
        return jsonify({"message": "Phone number already registered"}), 400

    hashed_password = generate_password_hash(data['password']) # 🛡️ Converts password like 'secret' → hashed string.
    # ✔️ Hover over hashed_password to view the hash.

    
    new_user = User(  # 📌 Breakpoint here shows values inside new_user (use __dict__ to inspect all fields in Debug pane).
        username=data['username'],
        password=hashed_password,
        name=data.get('name'),
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address')
    )

    # 🏗️ Creates a new user object.


    db.session.add(new_user)
    db.session.commit()
    # 🏗️ Adds the new user to the database session and commits it.
    # 💾 Adds the new user to the database and saves the record.

    logger.info('User registered: %s', data['username'])    
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        logger.error('Invalid login attempt: %s', data['username'])
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    logger.info('User logged in: %s', user.username)
    return jsonify(access_token=access_token)

@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    db.session.add(TokenBlocklist(jti=jti, created_at=datetime.utcnow()))
    db.session.commit() # Store the JTI in the blocklist
    # This will prevent the token from being used again
    response = jsonify({"message": "Successfully logged out"})
    unset_jwt_cookies(response)
    logger.info('User logged out with JTI: %s', jti)
    return response

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    logger.info('Protected route accessed')
    return jsonify({"message": "This is a protected route"})

@app.route('/update/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found: %d', user_id)
        return jsonify({"message": "User not found"}), 404

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
    return jsonify({"message": "User updated successfully"}), 200

@app.route('/user', methods=['DELETE'])
@jwt_required()
def delete_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found for deletion: %d', user_id)
        return jsonify({"message": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    logger.info('User deleted: %d', user_id)
    return jsonify({"message": "User deleted successfully"})

@app.route('/delete/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user_fields(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found for selective delete: %d', user_id)
        return jsonify({"message": "User not found"}), 404

    data = request.get_json()
    fields_to_delete = data.get('fields', [])
    for field in fields_to_delete:
        if hasattr(user, field):
            setattr(user, field, None)
    db.session.commit()
    logger.info('User fields deleted for: %d', user_id)
    return jsonify({"message": "User information deleted successfully"}), 200

@app.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user = User.query.get(user_id)
    if not user:
        logger.error('User not found: %d', user_id)
        return jsonify({"message": "User not found"}), 404

    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.name,
        'email': user.email,
        'phone': user.phone,
        'address': user.address
    }
    logger.info('User retrieved: %d', user_id)
    return jsonify(user_data), 200

if __name__ == '__main__':
    app.run(debug=True)
        
# The following commands are for initializing and migrating your database using Flask-Migrate:
# flask db init           # Initializes a new migration repository (run once per project)
# flask db migrate -m "Initial migration"   # Generates a new migration script (run after model changes)
# flask db upgrade        # Applies the migration to the database (updates the schema)

# To run the Flask application, use:
# python run.py           # Starts the Flask development server

