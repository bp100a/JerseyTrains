#!/usr/bin/python
"""Our train routing algorithm"""
import time


class TrainRouting:
    """Given the information about trains/stops/stations
    this will find the route to take for the specified
    transit points and time"""

    def __init__(self, stations: dict, schedule: dict):
        """

        :param stations: a dictionary of the train stations
        :param schedule: a dictionary of trains at the starting station
        """

    def direct_route(self, start: str, end: str, departure_time: time) -> dict:
        """

        :param start: This is the 2 character station name we are traveling from
        :param end: This the 2 character station name we are traveling to
        :param departure_time: this is (approximately) when we plan to leave
        :return: dict:
            {train_id#1: {'depart':<train leaves>, 'arrival': <train arrives>},
             train_id#2: ...}
        """
