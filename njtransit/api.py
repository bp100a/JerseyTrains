#!/usr/bin/python
"""an object for calling NJTransit's webservice interface"""
import xml.etree.ElementTree as ET
from http import HTTPStatus
from datetime import datetime
import json
import requests
from configuration import config


class NJTransitAPI:
    """a wrapper for calling NJTransit's web services"""
    _username = None
    _apikey = None

    @property
    def username(self) -> str:
        """our username, needed in every request"""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """return username, needed in all requests"""
        self._username = value

    @property
    def apikey(self) -> str:
        """our password, needed in every request"""
        return self._apikey

    @apikey.setter
    def apikey(self, value: str) -> None:
        """set the password, needed in every request"""
        self._apikey = value

    def __init__(self):
        """get our credentials from the configuration package"""
        self.username = config.USERNAME
        self.apikey = config.APIKEY

    @staticmethod
    def parse_station_schedule(root: ET) -> list:
        """parse the XML element tree into a list of train schedules"""
        train_list = []
        for items in root.iter('ITEM'):
            train_id = None
            destination = None
            departure = None
            index = None
            for item in items:
                if item.tag == 'TRAIN_ID':
                    train_id = item.text
                elif item.tag == 'DESTINATION':
                    destination = item.text
                elif item.tag == 'SCHED_DEP_DATE':
                    departure = datetime.strptime(item.text, '%d-%b-%Y %I:%M:%S %p')
                elif item.tag == 'ITEM_INDEX':
                    index = int(item.text)

                # if we got what we came for, exit loop to
                # save some time
                if departure and destination and train_id and index:
                    break

            train_list.append({'tid': train_id,
                               'destination': destination,
                               'departure': departure,
                               'index': index})
        return train_list

    @staticmethod
    def parse_train_schedule(root: ET) -> list:
        """parse the XML element tree into a list of train schedules"""
        train_list = []
        for items in root.iter('ITEM'): #pylint: disable-msg=too-many-nested-blocks
            this_train = {}
            for item in items:
                if item.tag == 'TRAIN_ID':
                    this_train.update({'tid': item.text})
                elif item.tag == 'DESTINATION':
                    this_train.update({'destination': item.text})
                elif item.tag == 'SCHED_DEP_DATE':
                    this_train.update({'departure':
                                           datetime.strptime(item.text, '%d-%b-%Y %I:%M:%S %p')})

                if 'departure' in this_train and \
                    'destination' in this_train and \
                    'tid' in this_train:
                    stop_list = {}
                    for stops in items.iter('STOP'):
                        this_stop = {}
                        station_name = None
                        for stop in stops:
                            if stop.tag == 'NAME':
                                station_name = stop.text
                            elif stop.tag == 'TIME':
                                if stop.text is None:
                                    continue  # skip this!
                                this_stop.update({'time':
                                                      datetime.strptime(stop.text,
                                                                        '%d-%b-%Y %I:%M:%S %p')})
                            elif stop.tag == 'STOP_STATUS':
                                this_stop.update({'status': stop.text})
                            elif stop.tag == 'DEPARTED':
                                this_stop.update({'departed': (stop.text == 'YES')})

                        stop_list.update({station_name: this_stop})

                    this_train.update({'stops': stop_list})
                    train_list.append(this_train)
                    break

        return train_list

    def train_schedule(self, station_abbreviation: str,
                       test_argument: str = None) -> list:
        """returns all the trains departing this station
        this is 'real-time' and shows current status of trains
        to/from this station

        :param station_abbreviation: 2 character abbreviation for station
        :param test_argument: Unit Tests Only! specifies what test data to use
        :return:

        """
        assert self.username and self.apikey
        url = config.HOSTNAME +\
              "/NJTTrainData.asmx/getTrainScheduleXML"
        body = "username={0}&password={1}&station={2}&NJT_Only={3}".\
            format(self.username, self.apikey, station_abbreviation, test_argument)
        try:
            rsp = requests.request(method='POST',
                                   url=url,
                                   headers={'content-type': 'application/x-www-form-urlencoded',
                                            'Accept' : 'application/xml'},
                                   data=body)
            if rsp.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
                response_string = rsp.content.decode('utf-8')
                root = ET.fromstring(response_string)
                return NJTransitAPI.parse_train_schedule(root)

        except requests.RequestException as err:
            print(err.__str__())
        except ET.ParseError as perr:
            print(perr.__str__())

        return []

    def station_schedule(self, station_abbreviation: str) -> list:
        """returns all the trains departing this station for a given day,
        not real-time data, but a list of all trains to/from the specified
        station"""
        assert self.username and self.apikey
        url = config.HOSTNAME +\
              "/NJTTrainData.asmx/getStationScheduleXML"
        body = "username={0}&password={1}&station={2}&NJT_Only=".\
            format(self.username, self.apikey, station_abbreviation)
        try:
            response_string = None
            rsp = requests.request(method='POST',
                                   url=url,
                                   headers={'content-type': 'application/x-www-form-urlencoded',
                                            'Accept' : 'application/xml'},
                                   data=body)
            if rsp.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
                response_string = rsp.content.decode('utf-8')
                root = ET.fromstring(response_string)
                return NJTransitAPI.parse_station_schedule(root)

        except requests.RequestException as err:
            print(err.__str__())
        except ET.ParseError as perr:
            print(perr.__str__())

        return None

    def train_stops(self, train_id: str) -> dict:
        """return all the stops for the train"""
        assert self.username and self.apikey
        url = config.HOSTNAME +\
              "/NJTTrainData.asmx/getTrainStopListJSON"
        body = "username={0}&password={1}&trainID={2}".format(self.username, self.apikey, train_id)
        try:
            rsp = requests.request(method='POST',
                                   url=url,
                                   headers={'content-type': 'application/x-www-form-urlencoded',
                                            'Accept' : 'application/xml'},
                                   data=body)
            if rsp.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
                root = ET.fromstring(rsp.content.decode('utf-8'))
                stop_list = json.loads(s=root.text, encoding='utf-8')['Train']
                train_id = stop_list['Train_ID']
                new_stop_list = []
                for stop in stop_list['STOPS']['STOP']:
                    flat_stop = {stop['NAME']: {'time': stop['TIME'],
                                                'departed': stop['DEPARTED'],
                                                'status': stop['STOP_STATUS']}}
                    new_stop_list.append(flat_stop)

                return {train_id: new_stop_list}
        except requests.RequestException as err:
            print(err.__str__())
        except ET.ParseError as perr:
            print(perr.__str__())

        return {}

    __train_stations = {}  # our private list of train stations

    @property
    def train_stations(self) -> dict:
        """return the list of train stations"""
        if not self.__train_stations:
            self.__train_stations = self.__fetch_train_stations()
        return self.__train_stations

    def __fetch_train_stations(self) -> dict:
        """read the list of train stations. Format of XML is:
        <STATIONS>
            <STATION>
                <STATION_2CHAR>CM</STATION_2CHAR>
                <STATIONNAME>Chatham</STATIONNAME>
            </STATION>
            o
            o
        </STATIONS>

        We return a list of dictionary elements for each station

        Note: Outside of unit tests, this shouldn't be called,
        we should access the station list via the property
        train_stations"""
        assert self.username and self.apikey
        url = config.HOSTNAME +\
              "/NJTTrainData.asmx/getStationListXML"

        body = "username={0}&password={1}".format(self.username, self.apikey)
        try:
            rsp = requests.request(method='POST',
                                   url=url,
                                   headers={'content-type': 'application/x-www-form-urlencoded',
                                            'Accept' : 'application/xml'},
                                   data=body)
            if rsp.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
                root = ET.fromstring(rsp.content.decode('utf-8'))
                station_stops = {}
                for stations in root:
                    abbreviation = None
                    station_name = None
                    for station in stations:
                        if station.tag == 'STATION_2CHAR':
                            abbreviation = station.text
                        elif station.tag == 'STATIONNAME':
                            station_name = station.text
                    if abbreviation and station_name and '\n' not in station_name:
                        station_stops.update({station_name: abbreviation})
                        station_stops.update({abbreviation: station_name})

                return station_stops

        except requests.RequestException as err:
            print(err.__str__())
        except ET.ParseError as perr:
            print(perr.__str__())

        return {}
