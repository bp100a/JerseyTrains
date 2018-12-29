# -*- coding: utf-8 -*-
""" Jersey Trains Alexa Skill! Returns the NJTransit train information """
# pylint: disable-msg=R0911, W0401, R1705, W0613
from models import cloudredis, setuplogging


SKILL_NAME = "Jersey Trains"
HELP_MESSAGE = "I can help you find a New Jersey Transit train to your desired destination"
HELP_REPROMPT = "What can I help you with?"
STOP_MESSAGE = "Goodbye!"
FALLBACK_MESSAGE = "The Jersey Trains skill can help you find New Jersey Transit trains " +\
                    " to your desired destination"
FALLBACK_REPROMPT = 'What can I help you with?'
HOME_STATION_SET = 'Your home station has been set to{0}'
CANNOT_SET_HOME = 'Sorry, I cannot set {0} as your home station'
NO_HOME_STATION_SET = 'Sorry, no home station has been set. You can set your home station' + \
                      'by saying ask Jersey Trains to set my home station to a station name'
CURRENT_HOME_STATION = "Your current home station is {0}"
ERROR_NO_STATION = "I'm sorry, you must specify a station"


def lambda_handler(event, context):

    """  App entry point  """
    setuplogging.initialize_logging(mocking=False) # make sure logging is setup
    setuplogging.LOGGING_HANDLER('EVENT{}'.format(event)) # log the event

    if event['session']['new']:
        on_session_started()

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended()

    return None

# --------------- Response handlers -----------------


def on_intent(request, session):
    """ called on receipt of an Intent  """

    intent_name = request['intent']['name']

    # initialize our redis server if needed
    if cloudredis.REDIS_SERVER is None:
        cloudredis.initialize_cloud_redis(injected_server=None)

    # process the intents

    if intent_name == "AMAZON.HelpIntent":
        return get_help_response()
    elif intent_name == "AMAZON.StopIntent":
        return get_stop_response()
    elif intent_name == "AMAZON.CancelIntent":
        return get_stop_response()
    elif intent_name == "AMAZON.FallbackIntent":
        return get_fallback_response()

    return get_help_response()


def get_help_response():
    """ get and return the help string  """

    speech_message = HELP_MESSAGE
    return response(speech_response_prompt(speech_message, speech_message, False))


def get_launch_response():

    """ get and return the help string  """

    return response(speech_response(HELP_MESSAGE, False))


def get_stop_response():

    """ end the session, user wants to quit """

    speech_output = STOP_MESSAGE
    return response(speech_response(speech_output, True))


def get_fallback_response():

    """ end the session, user wants to quit """

    speech_output = FALLBACK_MESSAGE
    return response(speech_response(speech_output, True))


def on_session_started():

    """" called when the session starts  """

    #print("on_session_started")


def on_session_ended():

    """ called on session ends """

    #print("on_session_ended")


def on_launch(request):

    """ called on Launch, we reply with a launch message  """
    return get_launch_response()


# --------------- Speech response handlers -----------------

def speech_response_ssml(output, endsession):

    """  create a simple json response  """

    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': '<speak>' + output + '</speak>'
        },
        'shouldEndSession': endsession
    }


def speech_response(output, endsession):

    """  create a simple json response  """

    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'shouldEndSession': endsession
    }


def speech_response_prompt(output, reprompt_text, endsession):

    """ create a simple json response with a prompt """


    return {

        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },

        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': endsession
    }


def response(speech_message) -> dict:

    """ create a simple json response  """

    return {
        'version': '1.0',
        'response': speech_message
    }
