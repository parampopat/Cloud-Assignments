import json
import boto3
import base64
from random import sample
from botocore.exceptions import ClientError


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        return False
    return True
    
    
def generate_name(len=7):
    name = ''.join(sample("abcdefghijklmnopqrstuvxyz1234567890", len)) + '.jpg'
    return name
	
    
def lambda_handler(event, context):
    with open("/tmp/image.jpg", "wb") as new_file:
        new_file.write(base64.b64decode(event['body'].split(',')[1]))
    print(upload_file("/tmp/image.jpg", 'ppkbphotos', generate_name()))
    return {
        'statusCode': 200,
        'body': json.dumps('Success')
    }
