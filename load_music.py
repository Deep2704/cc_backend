import json
import boto3
import os
# from dotenv import load_dotenv

# load_dotenv()

# Setup DynamoDB resource for local usage.
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',  # Local DynamoDB endpoint
    region_name='dummy',
    aws_access_key_id='dummy',
    aws_secret_access_key='dummy'
)

MUSIC_TABLE = os.getenv('DYNAMODB_MUSIC_TABLE', 'music')  # Default to 'music' if not set
music_table = dynamodb.Table(MUSIC_TABLE)

def load_music_data(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    songs = data.get('songs', [])
    count = 0
    for song in songs:
        # Assuming the table uses a composite key: 'title' (partition key) and 'album' (sort key)
        try:
            music_table.put_item(Item=song)
            count += 1
        except Exception as e:
            # Using .get() for keys to avoid KeyError if missing
            title = song.get('title', 'Unknown Title')
            album = song.get('album', 'Unknown Album')
            print(f"Error inserting {title} from {album}: {e}")
    print(f"Successfully inserted {count} songs.")

if __name__ == '__main__':
    # Ensure your JSON file path is correct.
    load_music_data('2025a1.json')
