#!/usr/bin/python
from unittest import TestCase
import os
from datetime import datetime
from http import HTTPStatus
from urllib import parse
import responses
from controllers import train_scheduler
from configuration import config


class TestTrainScheduler(TestCase):

    @staticmethod
    def read_test_data(filename: str) -> bytes:
        cwd = os.getcwd().replace('\\', '/')
        root = cwd.split('/tests')[0]
        path = root + '/tests/data/'
        path_n_name = path + filename
        file_pointer = open(path_n_name, mode='rb')
        data = file_pointer.read()
        file_pointer.close()
        return data

    def test_validate_station_name(self):
        """verify we can find station name in the name list"""
        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestTrainScheduler.read_test_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        scheduler = train_scheduler.TrainSchedule()
        assert scheduler.validate_station_name('Chatham')

    def test_initialization(self):
        """make sure NJT api object is initialized"""
        scheduler = train_scheduler.TrainSchedule()
        assert scheduler.njt

    @staticmethod
    def request_callback(request):
        arguments = dict(parse.parse_qsl(request.body))
        mapping = {'Chatham': 'CM', 'New York': 'NY', 'CM': 'CM', 'NY': 'NY'}
        station_abbreviation = mapping[arguments['station']]
        data = TestTrainScheduler.read_test_data('{0}_train_schedule.xml'.format(station_abbreviation))
        return HTTPStatus.CREATED, {'content-type': 'text/xml'}, data

    @responses.activate
    def test_schedule(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestTrainScheduler.read_test_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestTrainScheduler.request_callback,
            content_type='text/xml',)

        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='CM', ending_station_abbreviated='NY', departure_time=datetime.now())

        assert train_routes

