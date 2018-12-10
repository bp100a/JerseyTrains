#!/usr/bin/python
"""orchestration for our train schedules"""
import time
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

    def schedule(self, starting_station: str, ending_station: str, departure_time: time) -> dict:
        """given two stations, find all trains scheduled
        for the specified departure time"""
        assert self.njt
        assert self.validate_station_name(starting_station)
        assert self.validate_station_name(ending_station)

        # lookup schedule with abbreviated name
        starting_station_trains = self.njt.train_schedule(self.njt.train_stations[starting_station])

        # easy stuff first, direct routes where
        # the train goes directly to the ending station
        # ignore trains that are leaving after our proposed
        # departure time
        direct_trains = []
        possible_indirect_trains = []
        for train in starting_station_trains:
            if train['stops'][starting_station]['time'] > departure_time:
                continue
            if ending_station in train['stops']:
                direct_trains.append(train)
            else:
                possible_indirect_trains.append(train)

        # okay we have our direct routes, now we need to
        # look for indirect routes. We created a list
        # of possibles, which will include trains going
        # in the wrong direction!

        # let's get all trains that will be at our
        # ending station, using abbreviated name
        ending_station_trains = self.njt.train_schedule(self.njt.train_stations[ending_station])

        # we are looking for all routes where there's an intersection
        # between the 'possible_indirect_trains' and this list.
        transfer_routes = []
        transfer_threshold = 20 * 60  # wait no more than 20 minutes
        for start_train in possible_indirect_trains:
            for transfer_train in ending_station_trains:
                if starting_station in transfer_train['stops']:
                    continue  # already have this in direct route
                for start_stations in start_train['stops']:
                    if start_stations['time'] < departure_time:
                        continue
                    if start_stations['name'] not in transfer_train['stops']:
                        continue
                    transfer_station = transfer_train['stop'][start_stations['name']]
                    if transfer_station['time'] < start_stations['time']:
                        continue  # no time
                    if transfer_train['stop'][ending_station]['time'] < transfer_station['time']:
                        continue  # wrong direction!
                    wait_time = transfer_station['time'] - start_stations['time']
                    if wait_time > transfer_threshold:
                        continue

                    # It looks like we found a winner!
                    transfer_routes.append({'start': start_train,
                                            'transfer': transfer_train,
                                            'station': transfer_station})

        # transfer_routes can be screwey, we need to filter out the nonsense ones

        return {'direct': direct_trains, 'indirect': transfer_routes}
