#!/usr/bin/python
"""test for NJTransit API"""
from unittest import TestCase
import os
import xml.etree.ElementTree as ET
from http import HTTPStatus
import responses
from njtransit.api import NJTransitAPI
from configuration import config
from requests import RequestException

class TestNJTransitAPI(TestCase):
    """encapsulates our NJTransit API tests"""
    @staticmethod
    def create_tst_object() -> NJTransitAPI:
        """create the NJTransit object with sign-in"""
        njt = NJTransitAPI()
        njt.username = 'bp100a'
        njt.apikey = 'KT9yyHu9VqdW1H'
        return njt

    @staticmethod
    def read_data(filename: str) -> bytes:
        """read our canned XML test data"""
        cwd = os.getcwd().replace('\\', '/')
        root = cwd.split('/tests')[0]
        path = root + '/tests/data/'
        path_n_name = path + filename
        file_pointer = open(path_n_name, mode='rb')
        data = file_pointer.read()
        file_pointer.close()
        return data

    def test_username(self):
        """test that we can set the username"""
        njt = NJTransitAPI()
        assert njt.username

        njt.username = 'abcde'
        assert njt.username == 'abcde'
        assert njt.apikey

    def test_apikey(self):
        """test that we can set the API key/password"""
        njt = NJTransitAPI()
        assert njt.apikey

        njt.apikey = 'xyz'
        assert njt.apikey == 'xyz'
        assert njt.username

    @responses.activate
    def test_train_stations_property(self):
        njt = TestNJTransitAPI.create_tst_object()

        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestNJTransitAPI.read_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        station_list = njt.train_stations
        assert station_list
        assert len(station_list) == 174*2  # each station in by name & by abbreviation

    @responses.activate
    def test_train_stations_property_exception(self):
        njt = TestNJTransitAPI.create_tst_object()

        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = RequestException()
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        try:
            station_list = njt.train_stations
        except RequestException:
            pass

    @responses.activate
    def test_station_list(self):
        njt = TestNJTransitAPI.create_tst_object()

        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestNJTransitAPI.read_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        station_list = njt._NJTransitAPI__fetch_train_stations()
        assert station_list
        assert len(station_list) == 174*2  # each station in by name & by abbreviation

    @responses.activate
    def test_station_list_404(self):
        njt = TestNJTransitAPI.create_tst_object()

        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestNJTransitAPI.read_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.NOT_FOUND)

        station_list = njt._NJTransitAPI__fetch_train_stations()
        assert not station_list

    @responses.activate
    def test_station_list_parse_error(self):
        njt = TestNJTransitAPI.create_tst_object()

        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = b'bogus data to trip up parser'
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        try:
            njt._NJTransitAPI__fetch_train_stations()
            assert False
        except ET.ParseError:
            pass

    @responses.activate
    def test_train_schedule(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        test_bytes = TestNJTransitAPI.read_data('train_schedule.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        train_list = njt.train_schedule(station_abbreviation='CM')
        assert len(train_list) == 19
        for train in train_list:
            assert 'tid' in train
            assert 'departure' in train
            assert 'destination' in train

    @responses.activate
    def test_train_schedule_404(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        test_bytes = TestNJTransitAPI.read_data('train_schedule.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.NOT_FOUND)

        train_list = njt.train_schedule(station_abbreviation='CM')
        assert not train_list

    @staticmethod
    def XXXX_fetch_train_schedule_live():
        njt = TestNJTransitAPI.create_tst_object()
        train_list = njt.train_schedule(station_abbreviation='NY')
        assert not train_list

    @responses.activate
    def test_train_schedule_parse_error(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        test_bytes = b'bogus data to trip up parser'
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        try:
            njt.train_schedule(station_abbreviation='CM')
            assert False
        except ET.ParseError:
            pass

    @responses.activate
    def test_station_schedule(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationScheduleXML"
        test_bytes = TestNJTransitAPI.read_data('station_schedule.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        train_list = njt.station_schedule(station_abbreviation='CM')
        assert len(train_list) == 40
        for train in train_list:
            assert 'tid' in train
            assert 'index' in train
            assert 'departure' in train
            assert 'destination' in train

    @responses.activate
    def test_station_schedule_404(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationScheduleXML"
        test_bytes = TestNJTransitAPI.read_data('station_schedule.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.NOT_FOUND)

        train_list = njt.station_schedule(station_abbreviation='CM')
        assert not train_list

    @responses.activate
    def test_station_schedule_parse_error(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationScheduleXML"
        test_bytes = b'bogus data to trip up parser'
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        try:
            njt.station_schedule(station_abbreviation='CM')
            assert False
        except ET.ParseError:
            pass

    @responses.activate
    def test_station_stops(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainStopListJSON"
        test_bytes = TestNJTransitAPI.read_data('train_stops.json')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        stop_list = njt.train_stops(train_id='6919')  # train_id doesn't matter since pre-canned
        train_id = next(iter(stop_list))
        stops = stop_list[train_id]
        assert len(stops) == 20
        assert 'New York' in stops[0]
        assert 'Chatham' in stops[12]

    @responses.activate
    def test_station_stops_request_exception(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainStopListJSON"
        test_bytes = RequestException()
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        try:
            njt.train_stops(train_id='6919')  # train_id doesn't matter since pre-canned
            assert False
        except RequestException:
            pass

    @responses.activate
    def test_station_stops_404(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainStopListJSON"
        test_bytes = TestNJTransitAPI.read_data('train_stops.json')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.NOT_FOUND)

        stop_list = njt.train_stops(train_id='6919')  # train_id doesn't matter since pre-canned
        assert not stop_list

    @responses.activate
    def test_station_stops_parse_error(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainStopListJSON"
        test_bytes = b'bogus data to trip up parser'
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        try:
            njt.train_stops(train_id='6919')  # train_id doesn't matter since pre-canned
            assert False
        except ET.ParseError:
            pass

    @responses.activate
    def test_station_stops_request_error(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationScheduleXML"
        exception = RequestException()
        responses.add(responses.POST, url, body=exception, status=HTTPStatus.NOT_FOUND)

        try:
            train_list = njt.station_schedule(station_abbreviation='CM')
            assert False
        except RequestException:
            pass

    @responses.activate
    def test_train_schedule_request_error(self):
        njt = TestNJTransitAPI.create_tst_object()

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        exception = RequestException()
        responses.add(responses.POST, url, body=exception, status=HTTPStatus.NOT_FOUND)

        try:
            train_list = njt.train_schedule(station_abbreviation='CM')
            assert False
        except RequestException:
            pass

    @responses.activate
    def test_find_end_to_end(self):

        start_station = 'CM'  # Chatham
        end_station = 'NY'  # NY Penn

        # get the trains for Chatham station from our canned data
        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        test_bytes = TestNJTransitAPI.read_data('train_schedule.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        njt = TestNJTransitAPI.create_tst_object()
        train_list = njt.train_schedule(station_abbreviation=start_station)

        # now we have all trains leaving this station. Look for ones
        # that have our 2nd station as a stop
        prospective_trains = []
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestNJTransitAPI.read_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)
        station_list = njt._NJTransitAPI__fetch_train_stations()
        end_station_name = station_list[end_station]
        assert end_station_name

        # easy stuff first, direct routes
        for train in train_list:
            if end_station_name in train['stops']:
                prospective_trains.append(train)

        assert len(prospective_trains) == 12
