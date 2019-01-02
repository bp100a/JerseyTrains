"""testing for the AWS lambda function interface"""
import os
from datetime import datetime
import responses
from http import HTTPStatus
import lambda_function
import fakeredis
import responses
from urllib import parse
from tests.setupmocking import TestwithMocking
from models import cloudredis
from configuration import config
from tests.njtransit.test_NJTransitAPI import TestNJTransitAPI
from tests.test_data_generator import TrainScheduleData, TestSchedulerGeneratedData


class TestAWSlambda(TestwithMocking):

    @staticmethod
    def data_dir() -> str:
        # return the test data directory from the current root
        cwd = os.getcwd().replace('\\', '/')
        root = cwd.split('/tests')[0]
        path = root + '/tests/data/'
        return path

    def test_session_state(self):

        # create our launch request
        launch_event = {"request" : {"type": "LaunchRequest"}, "session" : {"new": True} }
        response = lambda_function.lambda_handler(event=launch_event, context=None)
        assert not response['response']['shouldEndSession']

    def test_fallback_response(self):
        get_fallback = {"request" : {"type": "IntentRequest", "intent": {"name": "AMAZON.FallbackIntent", "mocked": True}}, "session" : {"new": False} }
        response = lambda_function.lambda_handler(event=get_fallback, context=None)
        assert response['response']['shouldEndSession']
        assert response['response']['outputSpeech']['text'] == lambda_function.FALLBACK_MESSAGE

    def test_cancel_response(self):
        get_cancel = {"request" : {"type": "IntentRequest", "intent": {"name": "AMAZON.CancelIntent", "mocked": True}}, "session" : {"new": False} }
        response = lambda_function.lambda_handler(event=get_cancel, context=None)
        assert response['response']['shouldEndSession']
        assert response['response']['outputSpeech']['text'] == lambda_function.STOP_MESSAGE

    def test_stop_response(self):
        get_stop = {"request" : {"type": "IntentRequest", "intent": {"name": "AMAZON.StopIntent", "mocked": True}}, "session" : {"new": False} }
        response = lambda_function.lambda_handler(event=get_stop, context=None)
        assert response['response']['shouldEndSession']
        assert response['response']['outputSpeech']['text'] == lambda_function.STOP_MESSAGE

    def test_help_response(self):
        get_help = {"request" : {"type": "IntentRequest",\
                                 "intent": {"name": "AMAZON.HelpIntent", "mocked": True}}, "session" : {"new": False}}
        response = lambda_function.lambda_handler(event=get_help, context=None)
        assert not response['response']['shouldEndSession']
        assert response['response']['outputSpeech']['text'] == lambda_function.HELP_MESSAGE

    def test_unknown_intent_response(self):
        get_unknown = {"request" : {"type": "IntentRequest", "intent":\
                                    {"name": "JerseyTrains.UNKNOWN_INTENT", "mocked": True}},\
                       "session": {"new": False}}
        response = lambda_function.lambda_handler(event=get_unknown, context=None)
        assert not response['response']['shouldEndSession']
        assert response['response']['outputSpeech']['text'] == lambda_function.HELP_MESSAGE

    def test_new_session(self):
        event_new_session = {"session": {"new": False}, "request" : {"type" : "Bogus"} }
        response = lambda_function.lambda_handler(event=event_new_session, context=None)
        assert response is None

    def test_end_session(self):
        event_end_session = {"session": {"new": False}, "request" : {"type": "SessionEndedRequest"}}
        response = lambda_function.lambda_handler(event=event_end_session, context=None)
        assert response is None

    def test_unknown_intent_no_redis(self):
        get_unknown = {"request" : {"type": "IntentRequest", "intent":\
                                    {"name": "JerseyTrains.UNKNOWN_INTENT", "mocked": True}},\
                       "session": {"new": False}}
        cloudredis.REDIS_SERVER = None
        response = lambda_function.on_intent(request=get_unknown['request'],
                                             session=get_unknown['session'],
                                             fake_redis=fakeredis.FakeStrictRedis())
        assert not response['response']['shouldEndSession']
        assert response['response']['outputSpeech']['text'] == lambda_function.HELP_MESSAGE
        assert cloudredis.REDIS_SERVER

    @responses.activate
    def test_set_home_station_bogus(self):
        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestNJTransitAPI.read_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        set_home_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "SetHome", "mocked": True,\
                                                            "slots": {"station": {"value": "bogus"}}}},\
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=set_home_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.CANNOT_SET_HOME.format('bogus')

    @responses.activate
    def test_set_home_station(self):
        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestNJTransitAPI.read_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        set_home_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "SetHome", "mocked": True,\
                                                            "slots": {"station": {"value": "Chatham"}}}},\
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=set_home_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.HOME_STATION_SET.format('Chatham')

    def test_get_home_station_not_set(self):
        get_home_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "GetHome", "mocked": True}},\
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=get_home_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.NO_HOME_STATION_SET

    def test_get_home_station_set(self):

        self.test_set_home_station()

        get_home_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "GetHome", "mocked": True}}, \
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=get_home_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.CURRENT_HOME_STATION.format('Chatham')

    def test_format_speech_time_1am(self):

        test_time = datetime.strptime('11-Dec-2018 01:00:00 AM', '%d-%b-%Y %I:%M:%S %p')
        speech_time = lambda_function.format_speech_time(test_time)
        assert speech_time == '1 <say-as interpret-as="spell-out">AM</say-as>'

        test_time = datetime.strptime('11-Dec-2018 03:05:00 PM', '%d-%b-%Y %I:%M:%S %p')
        speech_time = lambda_function.format_speech_time(test_time)
        assert speech_time == '3 <say-as interpret-as="spell-out">O</say-as>5 <say-as interpret-as="spell-out">PM</say-as>'

        test_time = datetime.strptime('11-Dec-2018 12:10:00 PM', '%d-%b-%Y %I:%M:%S %p')
        speech_time = lambda_function.format_speech_time(test_time)
        assert speech_time == '12 10 <say-as interpret-as="spell-out">AM</say-as>'

    @staticmethod
    def request_callback_station_list(request):
        arguments = dict(parse.parse_qsl(request.body))
        tsd = TrainScheduleData()
        data = tsd.generate_station_xml()
        return HTTPStatus.CREATED, {'content-type': 'text/xml'}, data

    test_data = {'test_schedule':
                     {'01': {'depart': '11-Dec-2018 01:00:00 AM',
                             'stops': ['11', '12', '13', '14', '15', '16', '17', '18', '19']},  # all stops
                      '02': {'depart': '11-Dec-2018 02:00:00 AM',
                             'stops': ['11', '12', '13', '14', '16', '17', '19']},  # no stop at intersection
                      '03': {'depart': '11-Dec-2018 12:00:00 AM',
                             'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '18']},  # no stop at terminus
                      '04': {'depart': '11-Dec-2018 03:00:00 AM',
                             'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '19']},  # good transfer
                      '05': {'depart': '11-Dec-2018 02:30:00 AM',
                             'stops': ['11', '12', '13', '14', '15', '18']},  # connection for '04'
                      '06': {'depart': '11-Dec-2018 04:30:00 AM',
                             'stops': ['11', '12', '13', '19']}  # express train
                      }}

    @staticmethod
    def request_callback_train_schedule(request):
        arguments = dict(parse.parse_qsl(request.body))
        tsd = TrainScheduleData(train_stops=TestAWSlambda.test_data['test_schedule'])
        current_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        schedule = tsd.generate_train_schedule(station_name=arguments['station'], current_time=current_time)
        return HTTPStatus.CREATED, {'content-type': 'text/xml'}, schedule

    @responses.activate
    def test_lambda_schedule_no_home(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestAWSlambda.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestAWSlambda.request_callback_train_schedule,
            content_type='text/xml',)

        # now send intent with station routing
        next_station_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "NextTrain", "mocked": True,\
                                                            "slots": {"station": {"value": "Line 1 Station 1"}}}},\
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=next_station_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.NO_HOME_STATION_SET

    @responses.activate
    def test_lambda_schedule_start_destination_same(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestAWSlambda.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestAWSlambda.request_callback_train_schedule,
            content_type='text/xml',)

        # set the home station
        home_station = 'Line 1 Station 1'
        set_home_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "SetHome", "mocked": True,\
                                                            "slots": {"station": {"value": home_station}}}},\
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=set_home_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.HOME_STATION_SET.format(home_station)

        # now send intent with station routing
        next_station_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "NextTrain", "mocked": True,\
                                                            "slots": {"station": {"value": home_station}}}},\
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=next_station_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.DESTINATION_SAME_AS_HOME

    @responses.activate
    def test_lambda_next_train(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestAWSlambda.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestAWSlambda.request_callback_train_schedule,
            content_type='text/xml',)

        # set the home station
        home_station = 'Line 1 Station 1'
        destination_station = 'Line 1 Station 9'
        set_home_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "SetHome",
                                                            "slots": {"station": {"value": home_station}}}},
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=set_home_event, context=None)
        assert response['response']['outputSpeech']['text'] == lambda_function.HOME_STATION_SET.format(home_station)

        # now send intent with station routing
        test_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        next_station_event = {
            "request": {"type": "IntentRequest", "intent": {"name": "NextTrain", "time": test_time,
                                                            "slots": {"station": {"value": destination_station}}}},
            "session": {"new": False, "user": {"userId": "bogus_user_id"}}}

        response = lambda_function.lambda_handler(event=next_station_event, context=None)
        expected_response = '<speak>The next train from Line 1 Station 1 to Line 1 Station '\
                            '9 will leave at 2 <say-as interpret-as="spell-out">AM</say-as> and'\
                            ' arrive at 5 <say-as interpret-as="spell-out">AM</say-as></speak>'
        assert response['response']['outputSpeech']['ssml'] == expected_response

    # @staticmethod
    # def test_live_lambda_next_train():
    #     """Since the train scheduler calls the getTrainScheduleXML
    #     api twice, we use a callback to provide the proper canned
    #     responses"""
    #     # set the home station
    #     home_station = 'Chatham'
    #     destination_station = 'New York'
    #     set_home_event = {
    #         "request": {"type": "IntentRequest", "intent": {"name": "SetHome",
    #                                                         "slots": {"station": {"value": home_station}}}},
    #         "session": {"new": False, "user": {"userId": "bogus_user_id"}}}
    #
    #     fake_redis = fakeredis.FakeStrictRedis()
    #     response = lambda_function.on_intent(request=set_home_event['request'],
    #                                          session=set_home_event['session'],
    #                                          fake_redis=fake_redis)
    #     assert response['response']['outputSpeech']['text'] == lambda_function.HOME_STATION_SET.format(home_station)
    #
    #     # now send intent with station routing
    #     next_station_event = {
    #         "request": {"type": "IntentRequest", "intent": {"name": "NextTrain",
    #                                                         "slots": {"station": {"value": destination_station}}}},
    #         "session": {"new": False, "user": {"userId": "bogus_user_id"}}}
    #
    #     response = lambda_function.on_intent(request=next_station_event['request'],
    #                                          session=next_station_event['session'],
    #                                          fake_redis=fake_redis)
    #     assert response