#!/usr/bin/python3.6


class GtfsObject(object):
    """our base object for all GTFS file reading

    Derived classes will override the following:
    """

    # list of field names for the GTFS object
    _FIELD_NAMES = []