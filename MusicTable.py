import boto3

dynamodb = boto3.client(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='dummy',
    aws_access_key_id='dummy',
    aws_secret_access_key='dummy'
)

table_name = 'music'

try:
    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'title', 'KeyType': 'HASH'},
            {'AttributeName': 'album', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'title', 'AttributeType': 'S'},
            {'AttributeName': 'album', 'AttributeType': 'S'},
            {'AttributeName': 'artist', 'AttributeType': 'S'},
            {'AttributeName': 'year', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'ArtistIndex',
                'KeySchema': [{'AttributeName': 'artist', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            },
            {
                'IndexName': 'YearIndex',
                'KeySchema': [{'AttributeName': 'year', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            },
            {
                'IndexName': 'AlbumIndex',
                'KeySchema': [{'AttributeName': 'album', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    print("Creating Music Table with GSIs...")
    dynamodb.get_waiter('table_exists').wait(TableName=table_name)
    print(f"Table '{table_name}' created successfully!")
except Exception as e:
    print("Error creating music table:", e)
