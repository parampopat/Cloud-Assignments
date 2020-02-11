"""
Created from the 'BookTrip' Template.
This function is used as a fulfillment code hook for the Restaurant Suggestion
Lex Bot.
For instructions on how to set up and test this bot, as well as additional samples,
visit the Lex Getting Started documentation http://docs.aws.amazon.com/lex/latest/dg/getting-started.html.
"""

import time
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


# --- Helpers that build all of the responses ---


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def confirm_intent(session_attributes, intent_name, slots, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# --- Helper Functions ---


def safe_int(n):
    """
    Safely convert n value to int.
    """
    if n is not None:
        return int(n)
    return n


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


def msg_create(msg):
    return {'contentType': 'PlainText', 'content': msg}


def greet(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'I have finished greeting. Please take note'
        }
    )


def thank(intent_request):
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'I have finished thanking!. Please take note'
        }
    )


def dining_suggest(intent_request):
    """
    Performs dialog management and fulfillment for suggesting a restaruant.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    slots = intent_request['currentIntent']['slots']
    intent_name = intent_request['currentIntent']['name']
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}

    cuisine = slots['cuisine']
    dining_time = slots['dining_time']
    location = slots['location']
    num_people = slots['num_people']
    phone = slots['phone']

    if len(phone) != 10:
        return elicit_slot(
            session_attributes,
            intent_name,
            slots,
            'phone',
            msg_create('Phone number should be 10-digit without dashes/spaces or US . Try again!')
        )

    # Push SNS Notifcation - We are assured that all slots are filled and valid if we reach here
    sqs = boto3.client('sqs')
    sqs.send_message(
        QueueUrl='https://sqs.us-east-1.amazonaws.com/041132386971/restbotsms',
        MessageBody=str(slots)
    )

    # TO DO:
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': 'Great! You should see a text from me in a couple of minutes'
        }
    )


# --- Intents --- Fixed - Change function names later.


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug(
        'dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GreetingIntent':  # Actually does nothing
        return greet(intent_request)
    elif intent_name == 'DiningSuggestionsIntent':
        return dining_suggest(intent_request)
    elif intent_name == 'ThankYouIntent':  # Actually does nothing
        return thank(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


# --- Main handler --- No Change


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
