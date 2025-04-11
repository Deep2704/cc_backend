import json
import boto3
import os

# Setup DynamoDB resource for local usage.
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='dummy',
    aws_access_key_id='dummy',
    aws_secret_access_key='dummy'
)

MUSIC_TABLE = os.getenv('DYNAMODB_MUSIC_TABLE', 'music')
music_table = dynamodb.Table(MUSIC_TABLE)

def load_music_data(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)

    songs = data.get('songs', [])
    count = 0

    for song in songs:
        title = song.get('title')
        album = song.get('album')
        artist = song.get('artist')
        year = song.get('year')

        # Skip invalid entries
        if not title or not album:
            print(f"Skipping incomplete song (missing title/album): {song}")
            continue

        # Make sure artist and year exist for GSI indexing
        if not artist:
            song['artist'] = 'Unknown Artist'
        if not year:
            song['year'] = 'Unknown Year'

        # Optional: Add composite_id to help frontend
        song['composite_id'] = f"{title}|||{album}"

        try:
            music_table.put_item(Item=song)
            count += 1
        except Exception as e:
            print(f"Error inserting {title} - {album}: {e}")

    print(f"✅ Successfully inserted {count} songs.")

if __name__ == '__main__':
    load_music_data('2025a1.json')
