#!/usr/bin/python
from unittest import TestCase
import os
import pytz
from datetime import datetime
from http import HTTPStatus
from urllib import parse
import responses
from controllers import train_scheduler
from configuration import config


def to_datetime(date_string: str) -> datetime:
    return datetime.strptime(date_string, '%d-%b-%Y %I:%M:%S %p')


def utc_now() -> datetime:
    return pytz.timezone('UTC').localize(datetime.utcnow())


class TestTrainScheduler(TestCase):

    @staticmethod
    def read_data(filename: str) -> bytes:
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
        test_bytes = TestTrainScheduler.read_data('train_stations.xml')
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
        data = TestTrainScheduler.read_data('{0}_train_schedule.xml'.format(station_abbreviation))
        return HTTPStatus.CREATED, {'content-type': 'text/xml'}, data

    @responses.activate
    def test_schedule(self):
        """Since the train scheduler calls the getTrainScheduleXML
        api twice, we use a callback to provide the proper canned
        responses"""
        url = config.HOSTNAME + "/NJTTrainData.asmx/getStationListXML"
        test_bytes = TestTrainScheduler.read_data('train_stations.xml')
        responses.add(responses.POST, url, body=test_bytes, status=HTTPStatus.CREATED)

        url = config.HOSTNAME + "/NJTTrainData.asmx/getTrainScheduleXML"
        responses.add_callback(
            responses.POST, url,
            callback=TestTrainScheduler.request_callback,
            content_type='text/xml',)

        scheduler = train_scheduler.TrainSchedule()
        train_routes = scheduler.schedule(starting_station_abbreviated='CM', ending_station_abbreviated='NY', departure_time=utc_now())

        assert train_routes

    def test_best_schedule_none(self):
        """no routes to test"""
        routes = {}
        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes)
        assert not best_route

    def test_best_schedule_direct_only(self):
        """only a direct route to test"""
        routes = {'direct': [
            {'stops': {
                'Line 1 Station 1': {'time': datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')},
                'Line 1 Station 9': {'time': datetime.strptime('11-Dec-2018 02:00:00 AM', '%d-%b-%Y %I:%M:%S %p')}
                }
            },
            {'stops': {
                'Line 1 Station 1': {'time': datetime.strptime('11-Dec-2018 01:45:00 AM', '%d-%b-%Y %I:%M:%S %p')},
                'Line 1 Station 9': {'time': datetime.strptime('11-Dec-2018 02:00:00 AM', '%d-%b-%Y %I:%M:%S %p')}
                }
            }
            ]
        }

        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes)
        assert best_route['direct'] == routes['direct'][1]

    def test_best_schedule_direct_second_sooner(self):
        """only a direct route to test"""
        routes = {'direct': [
            {'stops': {
                'Line 1 Station 1': {'time': datetime.strptime('11-Dec-2018 01:30:00 AM', '%d-%b-%Y %I:%M:%S %p')},
                'Line 1 Station 9': {'time': datetime.strptime('11-Dec-2018 02:00:00 AM', '%d-%b-%Y %I:%M:%S %p')}
                }
            },
            {'stops': {
                'Line 1 Station 1': {'time': datetime.strptime('11-Dec-2018 01:45:00 AM', '%d-%b-%Y %I:%M:%S %p')},
                'Line 1 Station 9': {'time': datetime.strptime('11-Dec-2018 01:55:00 AM', '%d-%b-%Y %I:%M:%S %p')}
                }
            }
            ]
        }

        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes)
        assert best_route['direct'] == routes['direct'][1]

    def test_best_route_none(self):
        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes={})
        assert not best_route

    def test_best_route_empty(self):
        empty_routes = {'direct': {},
                        'indirect': {}
        }

        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes=empty_routes)
        assert not best_route

    def test_best_schedule_indirect_only(self):
        """only an indirect route to test"""
        routes = {'indirect': [
            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:00:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:25:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:10:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            },

            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 02:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:40:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:50:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:05:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            }
        ],
        }

        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes)
        assert best_route['indirect'] == routes['indirect'][1]

    def test_best_schedule_indirect_simultaneous_arrival(self):
        """only an indirect route to test"""
        routes = {'indirect': [
            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:00:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:25:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:10:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            },

            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 02:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:40:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:50:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:10:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            }
        ],
        }

        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes)
        assert best_route['indirect'] == routes['indirect'][1]

    def test_best_schedule_direct_and_indirect_routes(self):
        """best is the 2nd direct route, arrives same time but leaves later"""
        direct = {'direct': [
            {'stops': {
                'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:30:00 AM')},
                'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 02:00:00 AM')}
                }
            },
            {'stops': {
                'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:45:00 AM')},
                'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 02:00:00 AM')}
                }
            }
            ]
        }

        indirect = {'indirect': [
            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:00:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:25:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:10:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            },

            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 02:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:40:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:50:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:05:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            }
        ],
        }

        routes = {'direct': direct['direct'], 'indirect': indirect['indirect']}

        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes)
        assert best_route['direct'] == routes['direct'][1]

    def test_best_schedule_direct_and_indirect_routes_2(self):
        """2nd indirect route wins"""
        direct = {'direct': [
            {'stops': {
                'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:30:00 AM')},
                'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:10:00 AM')}
                }
            },
            {'stops': {
                'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:45:00 AM')},
                'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 04:00:00 AM')}
                }
            }
            ]
        }

        indirect = {'indirect': [
            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 01:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:00:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:25:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:10:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            },

            {'start':
                {'stops': {
                    'Line 1 Station 1': {'time': to_datetime('11-Dec-2018 02:30:00 AM')},
                    'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:40:00 AM')}
                }
                },
                'transfer':
                    {'stops': {
                        'Line 1 Station 5': {'time': to_datetime('11-Dec-2018 02:50:00 AM')},
                        'Line 1 Station 9': {'time': to_datetime('11-Dec-2018 03:05:00 AM')}
                    }
                    },
                'station': 'Line 1 Station 5'
            }
        ],
        }

        routes = {'direct': direct['direct'], 'indirect': indirect['indirect']}

        best_route = train_scheduler.TrainSchedule.best_route('Line 1 Station 1', 'Line 1 Station 9', routes)
        assert best_route['indirect'] == routes['indirect'][1]
