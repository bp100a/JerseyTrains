# -*- coding: utf-8 -*-
""" Jersey Trains Alexa Skill! Returns the NJTransit train information """
# pylint: disable-msg=R0911, W0401, R1705, W0613
import re
from datetime import datetime
from models import cloudredis, setuplogging
from controllers import train_scheduler

SKILL_NAME = "Jersey Trains"
HELP_MESSAGE = "I can help you find a New Jersey Transit train to your desired destination"
HELP_REPROMPT = "What can I help you with?"
STOP_MESSAGE = "Goodbye!"
FALLBACK_MESSAGE = "The Jersey Trains skill can help you find New Jersey Transit trains " +\
                    " to your desired destination"
FALLBACK_REPROMPT = 'What can I help you with?'
HOME_STATION_SET = 'Your home station has been set to {0}'
CANNOT_SET_HOME = 'Sorry, I cannot set {0} as your home station'
NO_HOME_STATION_SET = 'Sorry, no home station has been set. You can set your home station' + \
                      'by saying ask Jersey Trains to set my home station to a station name'
CURRENT_HOME_STATION = "Your current home station is {0}"
ERROR_NO_STATION = "I'm sorry, you must specify a station"
DESTINATION_INVALID = "I'm sorry, the destination you specified, {0} is not a recognized station"
DESTINATION_SAME_AS_HOME = "I'm sorry, the destination you specified is the same as your current home station"
NO_TRAINS = "I'm sorry, there are currently no trains running from {0} to {1}"
NOT_IMPLEMENTED = "I'm sorry, this feature has not been implemented"
NEXT_TRAIN_DIRECT = "The next train from {0} to {1} will leave at {2} and arrive at {3}"
NEXT_TRAIN_INDIRECT = NEXT_TRAIN_DIRECT + " with a transfer at {4}"
PROBLEM_WITH_ROUTE = "There was a problem with the routing information, please try later"

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

def set_home_station(request: dict, session: dict) -> dict:
    """set the home station for the user"""
    try:
        station = request['intent']['slots']['station']['value']
        aws_user_id = session['user']['userId']
        success = train_scheduler.ScheduleUser.set_home_station(station=station,
                                                user_id=aws_user_id)
        if success:
            return response(speech_response(HOME_STATION_SET.format(station), True))

        # some problem, tell the user. TBD validate brewery & other things,
        # perhaps ask for clarification
        setuplogging.LOGGING_HANDLER("SetHomeStation, station not found:\"{0}\"".format(station))
        return response(speech_response(CANNOT_SET_HOME.format(station), True))
    except KeyError:
        return response(speech_response(ERROR_NO_STATION, True))


def get_home_station(request: dict, session: dict) -> dict:
    """get the home station for the user"""

    aws_user_id = session['user']['userId']
    station = train_scheduler.ScheduleUser.get_home_station(user_id=aws_user_id)
    if not station:  # didn't find a home
        return response(speech_response(NO_HOME_STATION_SET, True))

    # some problem, tell the user. TBD validate station & other things,
    # perhaps ask for clarification
    return response(speech_response(CURRENT_HOME_STATION.format(station), True))


def next_train_indirect_response(start: str, destination: str, indirect_routes: dict) -> dict:
    """for now, just return the first indirect route"""
    return response(speech_response(NOT_IMPLEMENTED, True))


def format_speech_time(train_time: datetime) -> str:
    """format our time for speech. Note that Windows vs. Linux
    have different formatting for leading zero suppression, so
    easier to skip using strftime and just format it myself"""

    minute_str = ' '
    if train_time.minute < 10:
        if train_time.minute > 0:
            minute_str = ' <say-as interpret-as="spell-out">O</say-as>{0} '.format(train_time.minute)
    else:
        minute_str = ' {0} '.format(train_time.minute)

    if train_time.hour > 12:
        return '{0}'.format(train_time.hour - 12) + minute_str + '<say-as interpret-as="spell-out">PM</say-as>'

    return '{0}'.format(train_time.hour) + minute_str + '<say-as interpret-as="spell-out">AM</say-as>'


def next_train_direct_response(start: str, destination: str, direct_routes: dict) -> dict:
    """for now, just return the first direct route"""
    try:
        start_time = direct_routes[0]['stops'][start]['departure']
        arrival_time = direct_routes[0]['stops'][destination]['departure']

        # for times do AM/PM as '<say-as interpret-as="spell-out">PM</say-as>'
        direct_response = NEXT_TRAIN_DIRECT.format(start, destination,
                                                   format_speech_time(start_time),
                                                   format_speech_time(arrival_time))

        return response(speech_response_ssml(direct_response, True))
    except (KeyError, IndexError):
        return response(speech_response(PROBLEM_WITH_ROUTE, True))


def next_train_response(start_station: str, destination_station: str, train_routes: dict) -> dict:
    """okay, we should have a route (or more), so create our speech response"""
    if train_routes:
        if train_routes.has_key('direct'):
            return next_train_direct_response(start_station, destination_station, train_routes['direct'])

        if train_routes.has_key('indirect'):
            next_train_indirect_response(start_station, destination_station, train_routes['indirect'])

    return response(speech_response(NO_TRAINS.format(start_station, destination_station), True))


def next_train(request: dict, session: dict) -> dict:
    """find the next train leaving the user's home station"""
    aws_user_id = session['user']['userId']
    start_station = train_scheduler.ScheduleUser.get_home_station(user_id=aws_user_id)
    if not start_station: # didn't find a home
        return response(speech_response(NO_HOME_STATION_SET, True))

    # we have a home station, figure out the destination
    destination_station = request['intent']['slots']['station']['value']

    if start_station == destination_station:
        return response(speech_response(DESTINATION_SAME_AS_HOME, True))

    # validate the destination station
    if not train_scheduler.TrainSchedule.validate_station_name(destination_station):
        return response(speech_response(DESTINATION_INVALID.format(destination_station)), True)

    # okay the start & destination are valid, so it's time to do some routing
    current_time = datetime.time
    train_routes = train_scheduler.TrainSchedule().schedule(start_station, destination_station, departure_time=datetime.now())


def on_intent(request, session, fake_redis=None):
    """ called on receipt of an Intent  """

    intent_name = request['intent']['name']

    # initialize our redis server if needed
    if cloudredis.REDIS_SERVER is None:
        cloudredis.initialize_cloud_redis(injected_server=fake_redis)

    # process the intents

    if intent_name == "AMAZON.HelpIntent":
        return get_help_response()
    elif intent_name == "AMAZON.StopIntent":
        return get_stop_response()
    elif intent_name == "AMAZON.CancelIntent":
        return get_stop_response()
    elif intent_name == "AMAZON.FallbackIntent":
        return get_fallback_response()
    elif intent_name == 'GetHomeStation':
        return get_home_station(request, session)
    elif intent_name == 'SetHomeStation':
        return set_home_station(request, session)
    elif intent_name == 'NextTrain':
        return next_train(request, session)

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
