from flask import Flask, render_template, url_for, redirect, request, session, jsonify
import datetime
from dateutil.parser import parse
import requests
import io
import os
from bs4 import BeautifulSoup

from plot_types import type_to_prefix, prefix_info

app = Flask(__name__)
app.config.from_object(__name__)

SUPPORTED_SITES = ('ena', 'asi')


def instance_file(f):
    return os.path.join(app.instance_path, f)

app.config['SECRET_KEY'] = io.open(instance_file('.flask_secret'), 'rb').read()


def list_soundings(url):
    try:
        r = requests.get(url, timeout=2)
        if r.status_code != 200:
            return []

        s = BeautifulSoup(r.content, "html.parser")
        links = s.findAll('a')

        soundings = [a['href'] for a in links if 'sounding' in a['href']]

        return soundings

    except requests.exceptions.Timeout:
        return []


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for("static", filename="images/favicon.ico"))


@app.route('/apple-touch-icon-precomposed.png')
@app.route('/apple-touch-icon.png')
def apple_touch():
    return redirect(url_for("static", filename="images/apple-touch-icon-precomposed.png"))


@app.route('/_get_default_prefix')
def _get_default_prefix():
    default_params = {
        'radar': 'radar-boundary-layer',
        'precip': 'precip',
        'wind': 'wind-timeseries',
        'rose': 'wind-rose',
        'uhsas': 'uhsas-distribution',
        'aerosol': 'uhsas-concentration-linear',
        'scattering': 'scattering-1um-linear',
        'ccn': 'ccn-concentration',
        'cn': 'cn-concentration-log',
        'co': 'co-concentration-linear',
        'soundings': [],
              }
    return default_params


@app.route('/_set_session_prefix', methods=['POST',])
def _set_session_prefix():

    new_prefix = request.form.get('new_prefix', None)

    if new_prefix is not None:
        plot_type = prefix_info[new_prefix]['shortname']

        current_prefixes = session['prefixes']
        current_prefixes[plot_type] = new_prefix

        session['prefixes'] = current_prefixes

        return jsonify(plot_type=plot_type, new_prefix=new_prefix)


@app.route('/', methods=['GET',])
def index():
    return render_template('index.html')


@app.route('/<site_id>', methods=['GET',])
def site(site_id):
    if site_id not in SUPPORTED_SITES:
        return render_template('site_not_found.html')
    else:
        default_date = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        return render_template('site_index.html', site=site_id, date=default_date)


@app.route('/<site_id>/interesting_cases', methods=['GET', ])
def interesting_cases(site_id):
    return site_id


@app.route('/<site_id>/submit_case')
def submit_case(site_id):
    return site_id


@app.route('/<site_id>/<date>')
def figures_page(site_id, date):

    if not isinstance(date, datetime.datetime):
        try:
            dt = parse(date)
        except:
            return render_template('datetime_parse_error.html')
    else:
        dt = date

    plot_url_domain = 'http://atmos.uw.edu/~jstemm/arm-data-browser'
    plot_url = '{domain}/{site_id}/browser-figures/{date}/'.format(domain=plot_url_domain,
                                                                   site_id=site_id,
                                                                   date=dt.strftime('%Y-%m-%d'))

    global_params = {
        'date': dt,
        'next_day': dt + datetime.timedelta(days=1),
        'prev_day': dt - datetime.timedelta(days=1),
        'date_str': dt.strftime('%Y-%m-%d'),
        'plot_url': plot_url,
    }

    soundings = list_soundings(global_params['plot_url'])

    if 'prefixes' not in session:
        session['prefixes'] = _get_default_prefix()

    # session['prefixes'] = _get_default_prefix()

    return render_template('figures_page.html',
                           types=type_to_prefix,
                           labels={k: v['title'] for k,v in prefix_info.items()},
                           soundings=soundings,
                           site_id=site_id,
                           **global_params)


@app.route('/worldview/<resource>/<date>')
def worldview_image(resource, date):
    if resource == 'static':

        params = {'base_url': 'http://gibs.earthdata.nasa.gov/image-download',
                  'TIME': datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%Y%j'),
                  'extent': '-79.875,0,0,60.75',
                  'layers': 'MODIS_Aqua_CorrectedReflectance_TrueColor,Coastlines',
                  'opacities': '1,1',
                  'worldfile': 'false',
                  'format': 'image/jpeg',
                  'epsg': 4326,
                  'width': '909',
                  'height': '691'}

        full_url = '{base_url}?TIME={TIME}&extent={extent}&epsg={epsg}&layers={layers}&opacities={opacities}&' \
                   'worldfile={worldfile}&format={format}&width={width}&height={height}'.format(**params)
        return redirect(full_url)

    elif resource == 'dynamic':

        base_url = 'https://worldview.earthdata.nasa.gov/'

        layers = 'MODIS_Aqua_CorrectedReflectance_TrueColor,MODIS_Terra_CorrectedReflectance_TrueColor(hidden),' \
                 'MODIS_Aqua_CorrectedReflectance_Bands721(hidden),MODIS_Terra_CorrectedReflectance_Bands721(hidden),,'\
                 'Calipso_Orbit_Asc,Coastlines,,,,,,AMSR2_Cloud_Liquid_Water_Day(hidden),'\
                 'AMSR2_Cloud_Liquid_Water_Night(hidden),' \
                 'AMSR2_Wind_Speed_Day(hidden),AMSR2_Wind_Speed_Night(hidden),'
        v = '-160.453125,-57.09375,74.390625,78.1875'

        full_url = '{base_url}?p=geographic&l={layers}&t={date}&v={v}'.format(base_url=base_url,
                                                                              layers=layers, date=date, v=v)

        return redirect(full_url)

    else:

        return None

if __name__ == "__main__":
    app.run(debug=True, port=8080)
