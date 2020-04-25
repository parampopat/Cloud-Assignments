"""
This is called search_photo on AWS... Ignore the naming convention
"""

import json
import time
import os
import logging
import spacy

# import en_core_web_sm

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


def extract_objects(
        text,
        stop_nouns=['photo', 'pic', 'picture', 'image', 'gallery'],
        verbose=False, start=""
):
    nlp = spacy.load('/opt/en_core_web_sm/')
    nlp.add_pipe(nlp.create_pipe('merge_noun_chunks'))

    doc = nlp(start + text)
    items = []
    for token in doc:
        if verbose:
            print(token.text, token.lemma_, token.pos_)

        if token.pos_ in ['NOUN', 'PROPN'] and not any([s in token.text for s in stop_nouns]):
            items.append(token.lemma_)

    return items


def search_photo(intent_request):
    """
    Performs dialog management and fulfillment for suggesting a restaruant.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of sessionAttributes to pass information that can be used to guide conversation
    """
    session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    text = intent_request['inputTranscript']

    things = extract_objects(text)

    # TO DO:
    return close(
        session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': json.dumps(things)
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
    if intent_name == 'SearchPic':  # Actually does nothing
        return search_photo(intent_request)
    else:
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
