import boto3

dynamodb = boto3.client(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    region_name='dummy',
    aws_access_key_id='dummy',
    aws_secret_access_key='dummy'
)

table_name = 'subscriptions'

try:
    response = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'email',
                'KeyType': 'HASH'  # Partition key
            },
            {
                'AttributeName': 'album_id',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'email',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'album_id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    print("Creating Subscriptions Table...")
    dynamodb.get_waiter('table_exists').wait(TableName=table_name)
    print(f"Table '{table_name}' created successfully!")
except Exception as e:
    print("Error creating subscriptions table:", e)
