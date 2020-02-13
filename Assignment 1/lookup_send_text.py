import json
import boto3
from random import randint
from boto3.dynamodb.conditions import Key
from botocore.vendored import requests


def elastic_get_id(req):
    cuisine = req['cuisine']
    es_url = 'https://search-restaurants-eiskklpby24f4jvruokmxlbwba.us-east-1.es.amazonaws.com/restaurants/_search'
    count_query = es_url + '?q=cuisine:' + cuisine

    num_res = requests.get(count_query).json()['hits']['total']['value']
    random_hit = randint(0, num_res)

    query = {
        "from": random_hit,
        "size": 1,
        "query": {
            "multi_match": {
                "query": cuisine,
                "fields": ["cuisine"]
            }
        }
    }

    res = requests.post(es_url, json=query).json()['hits']['hits'][0]['_source']['id']

    return res


def get_restaurant_details(req, rest_id, table):
    response = table.query(
        IndexName='id-index',
        KeyConditionExpression=Key('id').eq(rest_id),
        FilterExpression="cuisine = :thiscus",
        ExpressionAttributeValues={":thiscus": req['cuisine'].lower()}
    )

    response = response['Items'][0]
    details_dict = {
        'name': response['name'],
        'address': ' '.join(eval(response['location'])['display_address']),
        'rating': response['rating']
    }

    sms = """Here is your reccomendation!\n{name}\nAddress: {address}\nRating: {rating}"""

    formatted = sms.format(**details_dict)

    return formatted


def process_request(req, table, sns, sqs, queue_url, receipt_handle):
    # Read Elastic Search for Random Restaurant Id
    restaurant_id = elastic_get_id(req)

    # Find Restaurant DEtails from Dynamo DB
    details = get_restaurant_details(req, restaurant_id, table)

    # Send SMS using SNS
    sns.publish(
        PhoneNumber='+1' + req['phone'],
        Message=details
    )

    # if Success, delete the message!
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


def lambda_handler(event, context):
    # Poll for SQS messages
    sqs = boto3.client('sqs')
    dynamodb = boto3.resource('dynamodb', region_name="us-east-1")
    table = dynamodb.Table('yelp-restaurants')
    sns = boto3.client('sns')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/041132386971/restbotsms'

    messages = sqs.receive_message(
        QueueUrl=queue_url
    )
    messages = messages.get('Messages', None)
    if messages is None:
        return {
            'statusCode': 200,
            'body': json.dumps('Found no Messages')
        }

    for msg in messages:
        receipt_handle = msg['ReceiptHandle']
        process_request(eval(msg['Body']), table, sns, sqs, queue_url, receipt_handle)

    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('I am done processing requests')
    }
