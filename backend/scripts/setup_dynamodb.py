"""
DynamoDB Setup Script for Nativity.ai Production
Creates the NativityProduction table with proper schema

Usage: python scripts/setup_dynamodb.py

Schema:
    - Partition Key: PK (String) → USER#<user_id>
    - Sort Key: SK (String) → VIDEO#<timestamp>
"""

import boto3
from botocore.exceptions import ClientError
import sys
import os

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings


TABLE_NAME = "NativityProduction"


def create_table(dynamodb_client):
    """
    Create the NativityProduction table with:
    - PK: Partition Key (String) - USER#<user_id>
    - SK: Sort Key (String) - VIDEO#<timestamp>
    """
    try:
        response = dynamodb_client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'  # String
                }
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand capacity
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'Nativity.ai'
                },
                {
                    'Key': 'Environment',
                    'Value': 'Production'
                }
            ]
        )
        
        print(f"✅ Table '{TABLE_NAME}' creation initiated!")
        print(f"   Status: {response['TableDescription']['TableStatus']}")
        print(f"   ARN: {response['TableDescription']['TableArn']}")
        
        # Wait for table to be active
        print("\n⏳ Waiting for table to become ACTIVE...")
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=TABLE_NAME)
        print(f"✅ Table '{TABLE_NAME}' is now ACTIVE and ready to use!")
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"ℹ️  Table '{TABLE_NAME}' already exists.")
            return True
        else:
            print(f"❌ Error creating table: {e}")
            return False


def describe_table(dynamodb_client):
    """Show table details"""
    try:
        response = dynamodb_client.describe_table(TableName=TABLE_NAME)
        table = response['Table']
        
        print(f"\n📊 Table Details: {TABLE_NAME}")
        print(f"   Status: {table['TableStatus']}")
        print(f"   Item Count: {table.get('ItemCount', 'N/A')}")
        print(f"   Size: {table.get('TableSizeBytes', 0) / 1024:.2f} KB")
        print(f"   ARN: {table['TableArn']}")
        
        print("\n🔑 Key Schema:")
        for key in table['KeySchema']:
            print(f"   {key['AttributeName']} ({key['KeyType']})")
            
    except ClientError as e:
        print(f"❌ Error describing table: {e}")


def main():
    print("=" * 60)
    print("🚀 NATIVITY.AI DYNAMODB SETUP")
    print("=" * 60)
    
    # Check AWS configuration
    if not settings.AWS_ACCESS_KEY_ID:
        print("❌ AWS_ACCESS_KEY_ID not configured!")
        print("   Please set AWS credentials in .env file")
        sys.exit(1)
    
    print(f"\n📍 Region: {settings.AWS_REGION}")
    print(f"📦 Table: {TABLE_NAME}")
    
    # Create DynamoDB client
    dynamodb = boto3.client(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )
    
    print("\n" + "-" * 40)
    
    # Create table
    if create_table(dynamodb):
        describe_table(dynamodb)
        
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
