#!/usr/bin/python
from unittest import TestCase
import os
from http import HTTPStatus
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

    @responses.activate
    def test_validate_station_name(self):

        # mock the request
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestTrainScheduler.read_test_data('train_stations.raw')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        scheduler = train_scheduler.TrainSchedule()
        assert scheduler.validate_station_name('Chatham')

    def test_initialization(self):
        """make sure NJT api object is initialized"""
        scheduler = train_scheduler.TrainSchedule()
        assert scheduler.njt

