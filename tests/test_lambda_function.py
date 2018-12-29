"""testing for the AWS lambda function interface"""
import os
import lambda_function
from tests.setupmocking import TestwithMocking


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
        event_end_session = {"session": {"new": False}, "request" : {"type": "SessionEndRequest"}}
        response = lambda_function.lambda_handler(event=event_end_session, context=None)
        assert response is None
