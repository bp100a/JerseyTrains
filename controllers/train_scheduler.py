#!/usr/bin/python
"""orchestration for our train schedules"""
from datetime import datetime, timedelta
from njtransit import api


class TrainSchedule:
    """will produce train schedules"""
    _njt = None  # object for NJTransit API

    @property
    def njt(self):
        """property to hold our NJTransit API object"""
        return self._njt

    def __init__(self):
        self._njt = api.NJTransitAPI()

    def validate_station_name(self, station_name: str) -> bool:
        """make sure the station name is valid"""
        return station_name in self.njt.train_stations

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
            self.njt.train_stations[starting_station_abbreviated], test_argument)

        # easy stuff first, direct routes where
        # the train goes directly to the ending station
        # ignore trains that are leaving after our proposed
        # departure time
        direct_trains = []
        possible_indirect_trains = []
        try:
            for train in starting_station_trains:
                starting_station_name = self.njt.train_stations[starting_station_abbreviated]
                if starting_station_name not in train['stops']:  # weird case to catch
                    continue
                if train['stops'][starting_station_name]\
                ['time'] < departure_time:
                    continue
                if self.njt.train_stations[ending_station_abbreviated] in train['stops']:
                    direct_trains.append(train)
                else:
                    possible_indirect_trains.append(train)
        except KeyError as dict_key_error:
            print(dict_key_error.__str__())

        # okay we have our direct routes, now we need to
        # look for indirect routes. We created a list
        # of possibles, which will include trains going
        # in the wrong direction!

        # let's get all trains that will be at our
        # ending station, using abbreviated name
        ending_station_trains = self.njt.train_schedule(
            self.njt.train_stations[ending_station_abbreviated],
            test_argument)

        # we are looking for all routes where there's an intersection
        # between the 'possible_indirect_trains' and this list.
        transfer_routes = []
        transfer_threshold = timedelta(minutes=35)  # wait no more than 20 minutes
        ending_station = self.njt.train_stations[ending_station_abbreviated]
        for start_train in possible_indirect_trains:
            for transfer_train in ending_station_trains:
                if starting_station_name in transfer_train['stops']:
                    continue  # already have this in direct route

                # we need to find the intersection of the 'start_train'
                # and our tentative 'transfer_train'
                for start_stations in start_train['stops']:

                    # if this is the starting station, skip
                    if start_stations == starting_station_name:
                        continue
                    # ignore trains that have already left
                    if start_train['stops'][start_stations]['time'] < departure_time:
                        continue
                    # if intersection station isn't in transfer train, skip
                    if start_stations not in transfer_train['stops']:
                        continue
                    transfer_station = transfer_train['stops'][start_stations]

                    # to transfer, the transfer has to arrive after the intersection train
                    if transfer_station['time'] < start_train['stops'][start_stations]['time']:
                        continue  # no time

                    # make sure the transfer train is going the correct direction!!
                    if transfer_train['stops'][ending_station]['time'] < transfer_station['time']:
                        continue  # wrong direction!

                    # finally, make sure we have enough time to catch the train
                    wait_time = transfer_station['time'] -\
                                start_train['stops'][start_stations]['time']
                    if wait_time > transfer_threshold:
                        continue

                    # It looks like we found a winner!
                    transfer_routes.append({'start': start_train,
                                            'transfer': transfer_train,
                                            'station': start_stations})

        # transfer_routes can be screwy, we need to filter out the nonsense ones

        return {'direct': direct_trains, 'indirect': transfer_routes}
