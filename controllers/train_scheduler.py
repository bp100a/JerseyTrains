#!/usr/bin/python
"""orchestration for our train schedules"""
from datetime import datetime, timedelta
from njtransit import api
from models import cloudredis


class TrainSchedule:
    """will produce train schedules"""
    _njt = None  # object for NJTransit API

    def train_stations(self, value: str) -> str:
        """dereference our NJTransit property"""
        return self.njt.train_stations[value]

    @property
    def njt(self):
        """property to hold our NJTransit API object"""
        return self._njt

    def __init__(self):
        self._njt = api.NJTransitAPI()

    def validate_station_name(self, station_name: str) -> bool:
        """make sure the station name is valid"""
        return station_name in self.njt.train_stations

    @staticmethod
    def optimize_indirect_routes(indirect_routes: list, destination: str) -> list:
        """
        From our list of indirect routes, remove any that are
        redundant, that is starting with same train but arriving
        later at the destination after a transfer.
        :param indirect_routes: list of current indirect train routes
        :param destination - our destination station
        :return: optimized list of indirect routes
        """
        # we need to determine if we should add this route to the list, or
        # add it and remove an existing route that isn't as good

        # 1. Add route if...
        #     a) No existing route with same start
        # 2. Don't add route if...
        #     a) existing route with same start
        #               - and -
        #     b) this route arrives at the terminus after
        #        the route already in the list
        #
        # 3. Remove route and add this one if...
        #     a) existing route with same start
        #              - and -
        #     b) this route arrives at the terminus
        #        before existing route
        #
        optimized = []
        for current in indirect_routes:
            best = current
            for same_start in indirect_routes:
                if current == same_start:
                    continue
                if current['start']['tid'] == same_start['start']['tid']:
                    if current['transfer']['stops'][destination]['time'] > \
                            same_start['transfer']['stops'][destination]['time']:
                        best = same_start
            if best not in optimized:
                optimized.append(best)

        return optimized

    def schedule_indirect_routes(self, possible_indirect_trains: list,
                                 starting_station: str,
                                 ending_station: str,
                                 departure_time: datetime,
                                 test_argument: str) -> list:
        """inspect the trains that originate from starting station but don't
        terminate at the ending station to see if there's a transfer
        to another line that will get us to the destination
        :param possible_indirect_trains - list of trains that start but don't end
        :param starting_station - full name of station we are leaving from
        :param ending_station - full name of station we wish to travel to
        :param departure_time - when we can get to start station
        :param test_argument - name of our test data for mocking input
        :return list of indirect train routes
        """
        # let's get all trains that will be at our
        # ending station, using abbreviated name
        ending_station_trains = self.njt.train_schedule(ending_station,
                                                        test_argument)

        # we are looking for all routes where there's an intersection
        # between the 'possible_indirect_trains' and this list.
        transfer_routes = []
        transfer_threshold = timedelta(minutes=5)  # allow at least 5 minutes to transfer
        for start_train in possible_indirect_trains:
            for transfer_train in ending_station_trains:
                if starting_station in transfer_train['stops']:
                    continue  # already have this in direct route
                arrival_time = transfer_train['stops'][ending_station]['time']
                if arrival_time <= departure_time:
                    continue

                # we need to find the intersection of the 'start_train'
                # and our tentative 'transfer_train'
                for start_stations in start_train['stops']:

                    # if this is the starting station, skip
                    if start_stations == starting_station:
                        continue

                    # ignore trains that have already left or going in wrong direction
                    start_time = start_train['stops'][start_stations]['time']
                    if start_time < departure_time or start_time >= arrival_time:
                        continue
                    # if intersection station isn't in transfer train, skip
                    if start_stations not in transfer_train['stops']:
                        continue
                    transfer_station = transfer_train['stops'][start_stations]
                    # to transfer, the transfer has to arrive after the intersection train
                    if transfer_station['time'] <= start_time:
                        continue  # no time

                    # make sure the transfer train is going the correct direction!!
                    if transfer_train['stops'][ending_station]['time'] < transfer_station['time']:
                        continue  # wrong direction!

                    # finally, make sure we have enough time to catch the train
                    wait_time = transfer_station['time'] - \
                        start_train['stops'][start_stations]['time']
                    if wait_time < transfer_threshold:
                        continue

                    # It looks like we found a winner!
                    transfer_routes.append({'start': start_train,
                                            'transfer': transfer_train,
                                            'station': start_stations})
                    break

        # remove any redundant routes from the list
        return TrainSchedule.optimize_indirect_routes(transfer_routes, ending_station)

    @staticmethod
    def best_route(starting_station_name: str, ending_station_name: str, routes: dict) -> dict:
        """
        Given a set of direct & indirect routes, find the *best* route:

            find the *best* direct train. Best means
            it arrives at the destination the earliest.
            if more than one arrives at the destination at
            the same time, take the one that leaves the
            start station the latest

        :param self:
        :param starting_station_name: starting station (not abbreviation)
        :param ending_station_name: destination station (not abbreviation)
        :param routes: dictionary of {'direct':[], 'indirect':[]}, can be empty
        :return: dictionary, either {'direct':[]} or {'indirect':[]}
        """

        # simple case of empty schedule
        if 'direct' not in routes and 'indirect' not in routes:
            return {}

        best_direct_train = {}
        if 'direct' in routes:
            leaves = None
            arrives = None
            for train in routes['direct']:
                if leaves is None:
                    leaves = train['stops'][starting_station_name]['time']
                if arrives is None:
                    arrives = train['stops'][ending_station_name]['time']
                    best_direct_train = train
                if best_direct_train != train:
                    if arrives == train['stops'][ending_station_name]['time']:
                        if leaves < train['stops'][starting_station_name]['time']:
                            best_direct_train = train
                            leaves = train['stops'][ending_station_name]['time']

                    if arrives > train['stops'][ending_station_name]['time']:
                        best_direct_train = train
                        arrives = train['stops'][ending_station_name]['time']

        # now find the best indirect, same criteria as the best direct
        best_indirect_train = {}
        if 'indirect' in routes:
            leaves = None
            arrives = None
            for train in routes['indirect']:
                if leaves is None:
                    leaves = train['start']['stops'][starting_station_name]['time']
                if arrives is None:
                    arrives = train['transfer']['stops'][ending_station_name]['time']
                    best_indirect_train = train
                if best_indirect_train != train:
                    if arrives == train['transfer']['stops'][ending_station_name]['time']:
                        if leaves < train['start']['stops'][starting_station_name]['time']:
                            best_indirect_train = train
                            leaves = train['transfer']['stops'][ending_station_name]['time']

                    if arrives > train['transfer']['stops'][ending_station_name]['time']:
                        best_indirect_train = train
                        arrives = train['transfer']['stops'][ending_station_name]['time']

        if best_direct_train and not best_indirect_train:
            return {'direct': best_direct_train}
        if best_indirect_train and not best_direct_train:
            return {'indirect': best_indirect_train}

        # this would be very strange indeed
        if not best_direct_train and not best_direct_train:
            return {}

        # TBD: should we worry about 'ties' at the destination and look for latest
        # leaving starting station?
        if best_indirect_train['transfer']['stops'][ending_station_name]['time'] < \
                best_direct_train['stops'][ending_station_name]['time']:
            return {'indirect': best_indirect_train}

        return {'direct': best_direct_train}

    def schedule(self, starting_station_abbreviated: str,
                 ending_station_abbreviated:
                 str, departure_time: datetime,
                 test_argument: str = None) -> dict:
        """given two stations, find all trains scheduled
        for the specified departure time"""
        assert self.njt
        assert self.validate_station_name(starting_station_abbreviated)
        assert self.validate_station_name(ending_station_abbreviated)

        # lookup schedule with abbreviated name
        starting_station_trains = self.njt.train_schedule(
            starting_station_abbreviated,
            test_argument)

        # easy stuff first, direct routes where
        # the train goes directly to the ending station
        # ignore trains that are leaving after our proposed
        # departure time
        direct_trains = []
        possible_indirect_trains = []
        starting_station_name = self.train_stations(starting_station_abbreviated)
        ending_station_name = self.train_stations(ending_station_abbreviated)
        try:
            for train in starting_station_trains:
                if starting_station_name not in train['stops']:  # weird case to catch
                    continue
                start_time = train['stops'][starting_station_name]['time']
                if start_time < departure_time:
                    continue
                if ending_station_name in train['stops']:
                    arrival_time = train['stops'][ending_station_name]['time']
                    if arrival_time > departure_time and \
                            arrival_time > start_time:
                        direct_trains.append(train)
                else:
                    possible_indirect_trains.append(train)
        except (KeyError, TypeError) as e:
            raise

        # okay we have our direct routes, now we need to
        # look for indirect routes. We created a list
        # of possibles, which will undoubtedly include
        # trains going in the wrong direction!

        transfer_routes = self.schedule_indirect_routes(possible_indirect_trains,
                                                        starting_station_name,
                                                        ending_station_name,
                                                        departure_time,
                                                        test_argument)

        return {'direct': direct_trains, 'indirect': transfer_routes}


class ScheduleUser:
    """Perform user-specific actions """
    @staticmethod
    def get_home_station(user_id: str) -> str:
        """get the home station, if set"""
        home_key = cloudredis.home_key(user_id)
        if not cloudredis.REDIS_SERVER.exists(home_key):
            return ''

        return cloudredis.REDIS_SERVER.get(home_key).decode('utf-8')

    @staticmethod
    def set_home_station(station: str, user_id: str) -> bool:
        """set a home station. Make sure it's a valid station"""
        ts = TrainSchedule()
        if not ts.validate_station_name(station):
            return False

        cloudredis.REDIS_SERVER.set(cloudredis.home_key(user_id), station)
        return True

