import boto3
import json
import os

def get_labels(bucket, file, num_labels=12):
    client = boto3.client('rekognition')
    response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':file}},MaxLabels=num_labels)
    labels = []
    for label in response['Labels']:
        labels.append(label['Name'].lower())
    return labels
    

def generateIndexRecord(bucket, file, time, labels):
    file_name = "/tmp/dummy_data.json"

    # Generate Record
    record = { "objectKey": file, "bucket" : bucket, "createdTimestamp" : time,  "labels" : labels}
    print('Written to JSON: ', record)
    
    # Index Record
    es_url = 'https://vpc-photo-index-6gtjhllhc3y47utn5shxhmfhu4.us-east-1.es.amazonaws.com/photos/_doc/'
    cmd = 'curl -XPOST %s -d \'%s\' -H "Content-Type: application/json"' % (es_url, json.dumps(record))
    
    resp = os.system(cmd)
    print("Done uploading to Elastic Search Index with res: ", resp)
    return record


def lambda_handler(event, context):
    bucket=event['Records'][0]['s3']['bucket']['name']
    file=event['Records'][0]['s3']['object']['key']
    labels = get_labels(bucket, file)
    record = generateIndexRecord(bucket, file, event['Records'][0]['eventTime'], labels)
    
    
    return {
        'statusCode': 200,
        'body': json.dumps(record)
    }
