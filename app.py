import json
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from dotenv import load_dotenv
import boto3
import os
from boto3.dynamodb.conditions import Attr

load_dotenv()
app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

# Setup DynamoDB resource and tables
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=os.getenv('DYNAMODB_ENDPOINT'),
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

login_table = dynamodb.Table('login')
music_table = dynamodb.Table('music')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    user_name = data.get('user_name')
    password = data.get('password')

    # Check if email exists
    try:
        response = login_table.get_item(Key={'email': email})
    except Exception as e:
        return jsonify({'message': f'Error accessing DB: {str(e)}'}), 500

    if 'Item' in response:
        return jsonify({'message': 'The email already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = {
        'email': email,
        'user_name': user_name,
        'password': hashed_password
    }
    try:
        login_table.put_item(Item=new_user)
    except Exception as e:
        return jsonify({'message': f'Error saving user: {str(e)}'}), 500

    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    try:
        response = login_table.get_item(Key={'email': email})
    except Exception as e:
        return jsonify({'message': f'Error accessing DB: {str(e)}'}), 500

    user = response.get('Item')
    if user and bcrypt.check_password_hash(user['password'], password):
        token = create_access_token(identity={'email': email})
        return jsonify({'success': True, 'token': token, 'user': {'email': email, 'user_name': user['user_name']}})
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

# New /user endpoint to retrieve current user details.
@app.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    return '', 200

# --- Music Endpoints ---

@app.route('/music', methods=['GET'])
def get_music():
    """
    Retrieve paginated music entries.
    Optional query parameters:
      - limit: number of items per page (default 10)
      - last_evaluated_key: JSON string of the last evaluated key from a previous scan
    """
    try:
        limit = int(request.args.get('limit', 12))
        last_key_str = request.args.get('last_evaluated_key')
        kwargs = {'Limit': limit}
        if last_key_str:
            kwargs['ExclusiveStartKey'] = json.loads(last_key_str)
        response = music_table.scan(**kwargs)
        items = response.get('Items', [])
        last_evaluated_key = response.get('LastEvaluatedKey')
        return jsonify({'items': items, 'lastEvaluatedKey': last_evaluated_key})
    except Exception as e:
        return jsonify({'message': f'Error retrieving music: {str(e)}'}), 500

@app.route('/music/query', methods=['GET'])
def query_music():
    """
    Query the music table by any combination of title, artist, year, and album.
    All provided fields are AND-ed together.
    Example: /music/query?title=American&artist=Tom%20Petty
    """
    filter_expr = None
    allowed_fields = ['title', 'artist', 'year', 'album']
    for field in allowed_fields:
        value = request.args.get(field)
        if value:
            expr = Attr(field).contains(value)
            if filter_expr is None:
                filter_expr = expr
            else:
                filter_expr = filter_expr & expr

    if filter_expr is None:
        return jsonify({'message': 'At least one query parameter must be provided.'}), 400

    try:
        response = music_table.scan(FilterExpression=filter_expr)
        items = response.get('Items', [])
        if not items:
            return jsonify({'message': 'No result is retrieved. Please query again.'}), 404
        return jsonify(items)
    except Exception as e:
        return jsonify({'message': f'Error querying music: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
