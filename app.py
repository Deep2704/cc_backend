import json
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from dotenv import load_dotenv
import boto3
import os
from boto3.dynamodb.conditions import Attr, Key

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
subscription_table = dynamodb.Table('subscriptions')


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    user_name = data.get('user_name')
    password = data.get('password')

    try:
        response = login_table.get_item(Key={'email': email})
    except Exception as e:
        return jsonify({'message': f'Error accessing DB: {str(e)}'}), 500

    if 'Item' in response:
        return jsonify({'message': 'The email already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = {'email': email, 'user_name': user_name, 'password': hashed_password}
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
        token = create_access_token(identity=email)  # ✅ FIXED
        return jsonify({'success': True, 'token': token, 'user': {'email': email, 'user_name': user['user_name']}})
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401


@app.route('/music', methods=['GET'])
def get_music():
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
    title = request.args.get('title')
    artist = request.args.get('artist')
    year = request.args.get('year')
    album = request.args.get('album')

    try:
        if artist and not title and not year and not album:
            response = music_table.query(
                IndexName='ArtistIndex',
                KeyConditionExpression=Key('artist').eq(artist)
            )
        elif year and not title and not artist and not album:
            response = music_table.query(
                IndexName='YearIndex',
                KeyConditionExpression=Key('year').eq(year)
            )
        elif album and not title and not artist and not year:
            response = music_table.query(
                IndexName='AlbumIndex',
                KeyConditionExpression=Key('album').eq(album)
            )
        else:
            filter_expr = None
            allowed_fields = ['title', 'artist', 'year', 'album']
            for field in allowed_fields:
                value = request.args.get(field)
                if value:
                    expr = Attr(field).contains(value)
                    filter_expr = expr if filter_expr is None else filter_expr & expr
            response = music_table.scan(FilterExpression=filter_expr)

        items = response.get('Items', [])
        if not items:
            return jsonify({'message': 'No result is retrieved. Please query again.'}), 404
        return jsonify({'items': items})
    except Exception as e:
        return jsonify({'message': f'Error querying music: {str(e)}'}), 500


@app.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe_album():
    try:
        data = request.get_json()
        email = get_jwt_identity()  # ✅ FIXED
        composite_id = data.get('composite_id')

        if not composite_id:
            return jsonify({'message': 'Album ID is required.'}), 400

        response = subscription_table.get_item(Key={'email': email, 'album_id': composite_id})
        if 'Item' in response:
            subscription_table.delete_item(Key={'email': email, 'album_id': composite_id})
            return jsonify({'subscribed': False, 'message': 'Unsubscribed successfully'})
        else:
            subscription_table.put_item(Item={'email': email, 'album_id': composite_id})
            return jsonify({'subscribed': True, 'message': 'Subscribed successfully'})
    except Exception as e:
        print("🔥 Error in /subscribe:", e)
        return jsonify({'message': f'Error updating subscription: {str(e)}'}), 500


@app.route('/subscriptions', methods=['GET'])
@jwt_required()
def get_subscriptions():
    try:
        email = get_jwt_identity()  # ✅ FIXED

        response = subscription_table.scan(
            FilterExpression=Attr('email').eq(email)
        )
        items = response.get('Items', [])
        album_ids = [item['album_id'] for item in items]

        albums = []
        for aid in album_ids:
            album_resp = music_table.scan(
                FilterExpression=Attr('composite_id').eq(aid)
            )
            if album_resp.get('Items'):
                albums.append(album_resp['Items'][0])

        return jsonify({'albums': albums})
    except Exception as e:
        print("🔥 Error in /subscriptions:", e)
        return jsonify({'message': f'Error retrieving subscriptions: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
