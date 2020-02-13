"""
__author__ = "Param Popat"
__version__ = "1.0"
__git__ = "https://github.com/parampopat/"
"""
import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def lambda_handler(event, context):
    # TODO implement
    update = call_lex(event['message'])
    return {
        'statusCode': 200,
        'body': json.dumps(update)
    }


def call_lex(message):
    """
    """
    lex = boto3.client('lex-runtime')
    response = lex.post_text(botName='RestaurantSuggestBot', botAlias='restbot', userId='procmon_kb3127',
                             sessionAttributes={}, requestAttributes={}, inputText=message)
    return response['message']
