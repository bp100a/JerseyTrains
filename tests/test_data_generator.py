#!/usr/bin/python
"""Test Data generator. The easiest way to test
this infernal problem is to generate specific test
data to cover all conditions"""
from unittest import TestCase
from datetime import datetime, timedelta
import os
from datetime import datetime
from http import HTTPStatus
from urllib import parse
import responses
from controllers import train_scheduler
from configuration import config


class TrainScheduleData:

    # define our stations
    station_names = {  # Stations for line #1
                     'Line 1 Station 1': '11',
                     'Line 1 Station 2': '12',
                     'Line 1 Station 3': '13',
                     'Line 1 Station 4': '14',
                     'Line 1 Station 5': '15',
                     'Line 1 Station 6': '16',
                     'Line 1 Station 7': '17',
                     'Line 1 Station 8': '18',
                     'Line 1 Station 9': '19',

                     # Stations for Line #2
                     'Line 2 Station A': '2A',
                     'Line 2 Station B': '2B',
                     'Line 2 Station C': '2C',
                     'Line 2 Station D': '2D'
                    }

    _train_stops = {}

    # structure is {'train_id', {'depart': <time>, 'stops': [list of stations]}
    # we use this to synthesize station and train schedules
    default_train = {'01': {'depart': '11-Dec-2018 01:00:00 AM',
                            'stops': ['11', '12', '13', '14', '15', '16', '17', '18', '19']},  # all stops
                     '02': {'depart': '11-Dec-2018 02:00:00 AM',
                            'stops': ['11', '12', '13', '14', '16', '17', '19']},  # no stop at intersection
                     '03': {'depart': '11-Dec-2018 01:30:00 AM',
                            'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '18', '19']},  # all stops
                     '04': {'depart': '11-Dec-2018 02:30:00 AM',
                            'stops': ['2A', '2B', '2C', '2D', '16', '17', '18', '19']},  # all stops at intersection
                     '05': {'depart': '11-Dec-2018 03:30:00 AM',
                            'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '18']},  # no stop at terminus
                     '06': {'depart': '11-Dec-2018 04:00:00 AM',
                            'stops': ['11', '12', '13', '14', '15', '16', '17', '18']},  # no stop at terminus
                     '07': {'depart': '11-Dec-2018 02:30:00 AM',
                            'stops': ['11', '12', '13', '14', '15', '16']},  # connection for '03'
                     '08': {'depart': '11-Dec-2018 04:30:00 AM',
                            'stops': ['11', '12', '13', '19']}  # express train
                    }

    @property
    def train_stops(self) -> dict:
        return self._train_stops

    def __init__(self, train_stops: dict = None):
        """pass in the train stop dictionary so we
        can easily change scenarios"""
        if train_stops is None:
            self._train_stops = self.default_train
        else:
            self._train_stops = train_stops

    def station_abbreviation_to_name(self, abbreviation: str) -> str:
        """reverse lookup of abbreviation -> name"""
        for name in self.station_names:
            if self.station_names[name] == abbreviation:
                return name
        return None

    def generate_station_xml(self) -> str:
        """Generate a test pattern for stations:

        <?xml version="1.0" encoding="utf-8"?>
        <STATIONS>
          <STATION>
            <STATION_2CHAR>AB</STATION_2CHAR>
            <STATIONNAME>Absecon</STATIONNAME>
          </STATION>
        """

        station_list = '<?xml version="1.0" encoding="utf-8"?>' + '\n'
        station_list += '<STATIONS>\n'

        for station in self.station_names:
            station_list += '  <STATION>'
            station_list += '    <STATION_2CHAR>{0}</STATION_2CHAR>\n'.format(self.station_names[station])
            station_list += '    <STATIONNAME>{0}</STATIONNAME>\n'.format(station)
            station_list += '  </STATION>\n'

        station_list += '</STATIONS>'
        return station_list

    train_schedules = []   # where we'll keep our train schedules

    def generate_train_schedule(self, station_name: str, current_time: datetime) -> str:
        """Generate the train schedule
        pass in the station name and the current time so we can
        compute the relevant schedule """
        schedules = {}
        station_abbreviation = station_name
        try:
            station_abbreviation = self.station_names[station_name]
        except KeyError:
            #  this is really the abbreviation
            station_name = next(key for key, value in self.station_names.items() if value == station_abbreviation)

        schedule = '<?xml version="1.0" encoding="utf-8"?>\n'
        schedule += '<STATION>\n'
        schedule += ' '*2 + '<STATION_2CHAR>{0}</STATION_2CHAR>\n'.format(station_abbreviation)
        schedule += ' '*2 + '<STATIONNAME>{0}</STATIONNAME>\n'.format(station_name)
        schedule += ' '*2 + '<ITEMS>\n'

        item_index = 0
        for train_id in self.train_stops:
            if station_abbreviation not in self.train_stops[train_id]['stops']:
                continue

            # This train goes to this station, so include in our list of trains
            item = ''
            item += ' '*4 + '<ITEM>\n'
            item += ' '*4 + '<ITEM_INDEX>{0}</ITEM_INDEX>\n'.format(item_index)
            item_index += 1
            item += ' '*6 + '<TRAIN_ID>{0}</TRAIN_ID>\n'.format(train_id)
            item += ' '*6 + '<DESTINATION>{0}</DESTINATION>\n'.\
                format(self.station_abbreviation_to_name(self.train_stops[train_id]['stops'][-1]))

            departure = datetime.strptime(self.train_stops[train_id]['depart'], '%d-%b-%Y %I:%M:%S %p')
            departure += timedelta(minutes=30 * self.train_stops[train_id]['stops'].index(station_abbreviation))
            item += ' '*6 + '<SCHED_DEP_DATE>{0}</SCHED_DEP_DATE>\n'.format(departure.strftime('%d-%b-%Y %I:%M:%S %p'))

            item += ' '*6 + '<STOPS>\n'
            on_time = False
            ignore_schedule = False
            departure = datetime.strptime(self.train_stops[train_id]['depart'], '%d-%b-%Y %I:%M:%S %p')
            for stop in self.train_stops[train_id]['stops']:
                item += ' '*8 + '<STOP>\n'
                item += ' '*8 + '<NAME>{0}</NAME>\n'.format(self.station_abbreviation_to_name(stop))
                item += ' '*8 + '<TIME>{0}</TIME>\n'.format(departure.strftime('%d-%b-%Y %I:%M:%S %p'))
                if departure <= current_time:
                    item += ' '*10 + '<DEPARTED>YES</DEPARTED>\n'
                    # if train has already departed this station, ignore
                    if station_abbreviation == stop:
                        ignore_schedule = True
                        break
                else:
                    item += ' '*10 + '<DEPARTED>NO</DEPARTED>\n'

                if departure > current_time and not on_time:
                    item += ' '*10 + '<STOP_STATUS>OnTime</STOP_STATUS>\n'
                    on_time = True
                else:
                    item += ' '*10 + '<STOP_STATUS>\n' + ' '*10 + '</STOP_STATUS>\n'

                item += ' '*8 + '</STOP>\n'
                departure += timedelta(minutes=30)

            if not ignore_schedule:  # train departed station being queried
                schedule += item + ' '*6 + '</STOPS>\n' + ' '*4 + '</ITEM>\n'

        schedule += ' '*2 +'</ITEMS>\n</STATION>\n'

        return schedule

    def generate_station_schedule(self, station_name: str) -> dict:
        """
        Return the XML for a Station's schedule

        <?xml version="1.0" encoding="utf-8"?>
        <STATION>
          <STATION_2CHAR>CM</STATION_2CHAR>
          <STATIONNAME>Chatham</STATIONNAME>
          <ITEMS>
            <ITEM>
              <ITEM_INDEX>0</ITEM_INDEX>
              <SCHED_DEP_DATE>08-Dec-2018 12:59:30 AM</SCHED_DEP_DATE>
              <DESTINATION>Dover</DESTINATION>
              <SCHED_TRACK>1</SCHED_TRACK>
              <TRAIN_ID>6683</TRAIN_ID>
              <LINE>Morris &amp; Essex Line</LINE>
              <STATION_POSITION>1</STATION_POSITION>
              <DIRECTION>Westbound</DIRECTION>
              <DWELL_TIME>60</DWELL_TIME>
              <PERM_CONNECTING_TRAIN_ID>
              </PERM_CONNECTING_TRAIN_ID>
              <PERM_PICKUP>
              </PERM_PICKUP>
              <PERM_DROPOFF>
              </PERM_DROPOFF>
              <STOP_CODE>S</STOP_CODE>
            </ITEM>

        :return:
        """
        schedules = {}
        station_abbreviation = self.station_names[station_name]
        schedule = '<?xml version="1.0" encoding="utf-8"?>\n'
        schedule += '<STATION>\n'
        schedule += ' '*2 + '<STATION_2CHAR>{0}</STATION_2CHAR>\n'.format(station_abbreviation)
        schedule += ' '*2 + '<STATIONNAME>{0}</STATIONNAME>\n'.format(station_name)
        schedule += ' '*2 + '<ITEMS>\n'

        item_index = 0
        for train_id in self.train_stops:
            if station_abbreviation in self.train_stops[train_id]['stops']:
                departure = datetime.strptime(self.train_stops[train_id]['depart'], '%d-%b-%Y %I:%M:%S %p')

                # This train goes to this station, so include in our list of trains
                schedule += ' '*4 + '<ITEM>\n'
                schedule += ' '*6 + '<ITEM_INDEX>{0}</ITEM_INDEX>\n'.format(item_index)
                item_index += 1
                schedule += ' '*6 + '<TRAIN_ID>{0}</TRAIN_ID>\n'.format(train_id)

                # determine departure time from this station
                departure += timedelta(minutes=30*self.train_stops[train_id]['stops'].index(station_abbreviation))
                schedule += ' '*6 + '<SCHED_DEP_DATE>{0}</SCHED_DEP_DATE>\n'.format(departure.strftime('%d-%b-%Y %I:%M:%S %p'))
                schedule += ' '*6 + '<DESTINATION>{0}</DESTINATION>\n'.format(self.station_abbreviation_to_name(self.train_stops[train_id]['stops'][-1]))
                schedule += ' '*6 + '<STOP_CODE>S</STOP_CODE>\n'
                schedule += ' '*4 + '</ITEM>\n'

        schedule += ' '*2 + '</ITEMS>\n</STATION>\n'

        return {station_abbreviation: schedule}


class TestDataGenerator(TestCase):
    """Test our data generating functions"""

    def test_generate_train_schedule_all(self):
        """test our schedule data generator, get all trains"""
        tsd = TrainScheduleData()
        current_time = datetime.strptime('11-Dec-2018 12:30:00 AM', '%d-%b-%Y %I:%M:%S %p')

        schedule = tsd.generate_train_schedule('Line 1 Station 1', current_time)
        assert '<TRAIN_ID>01</TRAIN_ID>' in schedule
        assert '<TRAIN_ID>02</TRAIN_ID>' in schedule
        assert '<TRAIN_ID>06</TRAIN_ID>' in schedule

    def test_generate_train_schedule_miss_first(self):
        """test our schedule data generator, missed first train"""
        tsd = TrainScheduleData()
        current_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')

        schedule = tsd.generate_train_schedule('Line 1 Station 1', current_time)
        assert '<TRAIN_ID>01</TRAIN_ID>' not in schedule
        assert '<TRAIN_ID>02</TRAIN_ID>' in schedule
        assert '<TRAIN_ID>06</TRAIN_ID>' in schedule
        assert '<TRAIN_ID>07</TRAIN_ID>' in schedule
        assert '<TRAIN_ID>08</TRAIN_ID>' in schedule

    def test_generate_station_schedule_01(self):
        tsd = TrainScheduleData()
        station_schedule = tsd.generate_station_schedule('Line 1 Station 1')
        assert station_schedule
        assert '11' in station_schedule
        assert '<TRAIN_ID>01</TRAIN_ID>' in station_schedule['11']
        assert '<TRAIN_ID>02</TRAIN_ID>' in station_schedule['11']
        assert '<TRAIN_ID>06</TRAIN_ID>' in station_schedule['11']

    def test_generate_station_schedule_15(self):
        tsd = TrainScheduleData()
        station_schedule = tsd.generate_station_schedule('Line 1 Station 5')
        assert station_schedule
        assert '15' in station_schedule
        assert '<TRAIN_ID>01</TRAIN_ID>' in station_schedule['15']
        assert '<TRAIN_ID>03</TRAIN_ID>' in station_schedule['15']
        assert '<TRAIN_ID>05</TRAIN_ID>' in station_schedule['15']
        assert '<TRAIN_ID>06</TRAIN_ID>' in station_schedule['15']


# for travel between '11' -> '19':
#   direct routes: #01, #02, #06
#   indirect routes: #05:04
test_data = {'test_schedule_1':
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
                  },
             'test_schedule_2':
                  {'01': {'depart': '11-Dec-2018 01:00:00 AM',
                          'stops': ['11', '12', '13', '14', '15', '16', '17', '18', '19']},  # all stops
                   '02': {'depart': '11-Dec-2018 02:00:00 AM',
                          'stops': ['11', '12', '13', '14', '16', '17', '19']},  # no stop at intersection
                   '03': {'depart': '11-Dec-2018 12:00:00 AM',
                          'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '18']},  # no stop at terminus
                   '04': {'depart': '11-Dec-2018 03:00:00 AM',
                          'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '19']},  # good transfer
                   '06': {'depart': '11-Dec-2018 04:30:00 AM',
                          'stops': ['11', '12', '13', '19']}  # express train
                   },
             'test_schedule_3':
                 {'01': {'depart': '11-Dec-2018 01:00:00 AM',
                         'stops': ['11', '12', '13', '14', '15', '16', '17', '18', '19']},  # all stops
                  '02': {'depart': '11-Dec-2018 02:00:00 AM',
                         'stops': ['11', '12', '13', '14', '16', '17', '19']},  # no stop at intersection
                  '03': {'depart': '11-Dec-2018 12:00:00 AM',
                         'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '18']},  # no stop at terminus
                  '04': {'depart': '11-Dec-2018 03:00:00 AM',
                         'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '19']},  # @15 5:00am, 6:30am
                  '05': {'depart': '11-Dec-2018 02:30:00 AM',
                         'stops': ['11', '12', '13', '14', '15', '18']},  # connection for '04' @15 4:30am
                  '06': {'depart': '11-Dec-2018 04:30:00 AM',
                         'stops': ['11', '12', '13', '19']}, # express train
                  '07': {'depart': '11-Dec-2018 02:55:00 AM',
                         'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '19']},  # @15 4:55am, 6:25am arrival
                  },

             'test_schedule_4':
                 {'01': {'depart': '11-Dec-2018 01:00:00 AM',
                         'stops': ['11', '12', '13', '14', '15', '16', '17', '18', '19']},  # all stops
                  '02': {'depart': '11-Dec-2018 02:00:00 AM',
                         'stops': ['11', '12', '13', '14', '16', '17', '19']},  # no stop at intersection
                  '03': {'depart': '11-Dec-2018 12:00:00 AM',
                         'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '18']},  # no stop at terminus
                  '04': {'depart': '11-Dec-2018 03:00:00 AM',
                         'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '19']},  # @15 5:00am, 6:30am
                  '05': {'depart': '11-Dec-2018 02:30:00 AM',
                         'stops': ['11', '12', '13', '14', '15', '18']},  # connection for '04' @15 4:30am
                  '06': {'depart': '11-Dec-2018 04:30:00 AM',
                         'stops': ['11', '12', '13', '19']}, # express train
                  '07': {'depart': '11-Dec-2018 02:33:00 AM',
                         'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '19']},  # @15 4:33am (not enough time to xfer)
                  '08': {'depart': '11-Dec-2018 02:25:00 AM',
                         'stops': ['2A', '2B', '2C', '2D', '15', '16', '17', '19']},  # @15 4:25am
                  }

             }


class TestSchedulerGeneratedData(TestCase):

    @staticmethod
    def request_callback_station_list(request):
        arguments = dict(parse.parse_qsl(request.body))
        tsd = TrainScheduleData()
        data = tsd.generate_station_xml()
        return HTTPStatus.CREATED, {'content-type': 'text/xml'}, data

    @staticmethod
    def request_callback_train_schedule(request):
        arguments = dict(parse.parse_qsl(request.body))
        tsd = TrainScheduleData(train_stops=test_data[arguments['NJT_Only']])
        current_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        schedule = tsd.generate_train_schedule(station_name=arguments['station'], current_time=current_time)
        return HTTPStatus.CREATED, {'content-type': 'text/xml'}, schedule

    @responses.activate
    def test_schedule_1(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_train_schedule,
            content_type='text/xml',)

        test_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='11',
                                          ending_station_abbreviated='19',
                                          departure_time=test_time,
                                          test_argument='test_schedule_1')
        assert train_routes
        assert train_routes['direct']
        assert train_routes['indirect']
        assert len(train_routes['indirect']) == 1
        assert train_routes['indirect'][0]['station'] == 'Line 1 Station 5'
        assert train_routes['direct'][0]['tid'] == '02' and train_routes['direct'][1]['tid'] == '06'

    @responses.activate
    def test_schedule_2(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_train_schedule,
            content_type='text/xml',)

        test_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='11',
                                          ending_station_abbreviated='19',
                                          departure_time=test_time,
                                          test_argument='test_schedule_2')
        assert train_routes
        assert train_routes['direct']
        assert not train_routes['indirect']
        assert train_routes['direct'][0]['tid'] == '02' and train_routes['direct'][1]['tid'] == '06'

    @responses.activate
    def test_schedule_1a(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_train_schedule,
            content_type='text/xml',)

        test_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='11',
                                          ending_station_abbreviated='18',
                                          departure_time=test_time,
                                          test_argument='test_schedule_1')
        assert not train_routes['indirect']
        assert train_routes['direct'][0]['tid'] == '05'

    @responses.activate
    def test_schedule_3_no_trains(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_train_schedule,
            content_type='text/xml',)

        test_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='11',
                                          ending_station_abbreviated='2A',
                                          departure_time=test_time,
                                          test_argument='test_schedule_3')
        assert not train_routes['direct']
        assert not train_routes['indirect']

    @responses.activate
    def test_schedule_3(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_train_schedule,
            content_type='text/xml',)

        test_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='11',
                                          ending_station_abbreviated='19',
                                          departure_time=test_time,
                                          test_argument='test_schedule_3')
        assert train_routes['indirect']
        assert train_routes['direct'][0]['tid'] == '02' and train_routes['direct'][1]['tid'] == '06'
        assert len(train_routes['indirect']) == 1
        # route 05 -> 04 arrives at 5am whereas 05 -> 07 arrives at 4:55am, so only one route is optimal
        assert train_routes['indirect'][0]['start']['tid'] == '05' and train_routes['indirect'][0]['transfer']['tid'] == '07'

    @responses.activate
    def test_schedule_4(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_station_list,
            content_type='text/xml',)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestSchedulerGeneratedData.request_callback_train_schedule,
            content_type='text/xml',)

        test_time = datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')
        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='11',
                                          ending_station_abbreviated='19',
                                          departure_time=test_time,
                                          test_argument='test_schedule_4')
        assert train_routes['indirect']
        assert train_routes['direct'][0]['tid'] == '02' and train_routes['direct'][1]['tid'] == '06'
        assert len(train_routes['indirect']) == 1
        # route 05 -> 04 arrives at 5am whereas 05 -> 07 only allows 3 minutes to transfer, so discarded
        assert train_routes['indirect'][0]['start']['tid'] == '05' and train_routes['indirect'][0]['transfer']['tid'] == '04'
