import json
import boto3

def lambda_handler(event, context):
    items = call_lex(event['message'])
    items = json.loads(items)
    resp = {
        'statusCode': 200,
        'body': items
    }

    return resp


def call_lex(message):
    """
    """
    lex = boto3.client('lex-runtime')
    response = lex.post_text(
        botName='SearchPhotos',
        botAlias='prod',
        userId='kb3127',
        sessionAttributes={}, requestAttributes={},
        inputText=message
    )

    return response['message']
