from collections import defaultdict

prefix_info = {

    'scattering-10um-linear':       {'shortname': 'scattering', 'title': '10um Linear'},
    'scattering-10um-log':          {'shortname': 'scattering', 'title': '10um Log'},
    'scattering-1um-linear':        {'shortname': 'scattering', 'title': '1um Linear'},
    'scattering-1um-log':           {'shortname': 'scattering', 'title': '1um Log'},

    'uhsas-concentration-linear':   {'shortname': 'aerosol', 'title': 'Linear'},
    'uhsas-concentration-log':      {'shortname': 'aerosol', 'title': 'Log'},

    'radar-boundary-layer':         {'shortname': 'radar', 'title': 'Boundary Layer'},
    'radar-full-height':            {'shortname': 'radar', 'title': 'Full Height'},

    'ccn-concentration':            {'shortname': 'ccn', 'title': 'CCN'},

    'cn-concentration-linear':      {'shortname': 'cn', 'title': 'Linear'},
    'cn-concentration-log':         {'shortname': 'cn', 'title': 'Log'},

    'co-concentration-linear':      {'shortname': 'co', 'title': 'Linear'},
    'co-concentration-log':         {'shortname': 'co', 'title': 'Log'},

    'precip':                       {'shortname': 'precip', 'title': 'Precipitation'},
    'wind-timeseries':              {'shortname': 'wind', 'title': 'Wind'},
    'wind-rose':                    {'shortname': 'rose', 'title': 'Wind Rose'},

    'uhsas-distribution':           {'shortname': 'uhsas', 'title': 'UHSAS'},

}

type_to_prefix = defaultdict(list)

for k, v in prefix_info.items():
    type_to_prefix[v['shortname']].append(k)
