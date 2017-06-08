import io
import os
import json
from flask import Flask, render_template, request, url_for, redirect, make_response, jsonify, session, g, flash
import requests
import sqlite3
import pandas as pd
from dateutil.parser import parse
import datetime
from collections import OrderedDict
from bs4 import BeautifulSoup

# from secret import SECRET
from plot_types import prefix_to_type, type_to_prefix, prefix_labels

app = Flask(__name__)
app.config.from_object(__name__)

def instance_file(f):
    return os.path.join(app.instance_path, f)

with io.open(instance_file('.recaptcha')) as cred:
    recaptcha = json.load(cred)

with io.open(instance_file('.sheetsu')) as cred:
    sheetsu = json.load(cred)

app.config['SECRET_KEY'] = io.open(instance_file('.flask_secret'), 'rb').read()
app.config.update(dict(
    DATABASE=instance_file('cases.db'),
))

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')

def query_category(category):
    db = get_db()
    query = "select case_date, description from cases where category is ?"
    cur = db.execute(query, [category, ])
    entries = cur.fetchall()
    return sorted(entries, key=lambda x: x['case_date'])

def capitalize(s):
    """Capitalizes the first letter of each word in string 's'"""
    words = s.split(' ')
    return ' '.join(word.capitalize() for word in words)

def list_categories():
    db = get_db()
    cur = db.execute('select distinct category from cases')
    return sorted([capitalize(e['category']) for e in cur.fetchall()])

@app.route('/interesting_cases', methods=['GET', 'POST'])
def interesting_cases():

    categories = list_categories()

    if request.method == "POST":
        category = request.form.get('category')
    else:
        category = categories[0]

    return render_template('list_of_cases.html', category=category, categories=categories, entries=query_category(category.lower()))

@app.route('/', methods=['GET',])
def index():
    default_date = (datetime.datetime.now()-datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    return render_template('index.html', date=default_date)

@app.route('/favicon.ico')
def favicon():
    return redirect(url_for("static", filename="images/favicon.ico"))

@app.route('/apple-touch-icon-precomposed.png')
@app.route('/apple-touch-icon.png')
def apple_touch():
    return redirect(url_for("static", filename="images/apple-touch-icon-precomposed.png"))

@app.route('/_get_figures_page', methods=['POST',])
def _get_figures_page():
    if request.method == 'POST':
        date = request.form.get('date')
        if date is not None:
            return redirect(url_for('figures_page', date=date))
    else:
        return render_template('index.html')

@app.route('/_get_default_prefix')
def _get_default_prefix():
    default_params = {
        'radar': 'boundary-layer-radar',
        'precip': 'precip',
        'wind': 'wind',
        'rose': 'wind-rose',
        'uhsas': 'uhsas',
        'aerosol': 'aerosol-concentration-linear',
        'scattering': '1um-scattering-linear',
        'ccn': 'ccn',
        'cn': 'cn-log',
        'co': 'co-linear',
        'soundings': [],
              }
    return default_params

@app.route('/_set_session_prefix', methods=['POST',])
def _set_session_prefix():

    new_prefix = request.form.get('new_prefix', None)

    if new_prefix is not None:
        plot_type = prefix_to_type[new_prefix]

        current_prefixes = session['prefixes']
        current_prefixes[plot_type] = new_prefix

        session['prefixes'] = current_prefixes

        return jsonify(plot_type=plot_type, new_prefix=new_prefix)

# @app.route('/_list_soundings', methods=['POST',])
def _list_soundings(url):
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

@app.route('/date/<date>', methods=['GET', ])
def figures_page(date):

    if not isinstance(date, datetime.datetime):
        dt = parse(date)
    else:
        dt = date

    global_params = {
        'date': dt,
        'next_day': dt + datetime.timedelta(days=1),
        'prev_day': dt - datetime.timedelta(days=1),
        'date_str': dt.strftime('%Y-%m-%d'),
        'plot_url': 'http://atmos.uw.edu/~jstemm/ena-figures/browser-figures/{}/'.format(dt.strftime('%Y-%m-%d')),
        # 'plot_url': url_for('static', filename='figures/{}/'.format(dt.strftime('%Y-%m-%d')))
    }

    soundings = _list_soundings(global_params['plot_url'])

    if 'prefixes' not in session:
        session['prefixes'] = _get_default_prefix()

    return render_template('new_page_of_figures.html', types=type_to_prefix, labels=prefix_labels, soundings=soundings, **global_params)

@app.route('/bl/<date>')
def redirect_bl(date):
    if 'prefixes' not in session:
        s = _get_default_prefix()
    else:
        s = session['prefixes']
    s['radar'] = 'boundary-layer-radar'
    session['prefixes'] = s

    return redirect(url_for('figures_page', date=date))

@app.route('/full/<date>')
def redirect_full(date):
    if 'prefixes' not in session:
        s = _get_default_prefix()
    else:
        s = session['prefixes']
    s['radar'] = 'full-height-radar'
    session['prefixes'] = s

    return redirect(url_for('figures_page', date=date))


@app.route('/submit_case')
def submit_case():
    return render_template('case_submission.html', site_key=recaptcha['site-key'], d=request.args)


@app.route('/_submit_case', methods=['POST', 'GET'])
def _submit_case():
    form = request.form

    gcaptcha = form.get('g-recaptcha-response', None)
    if gcaptcha is not None:
        gcaptcha_payload = {'secret': recaptcha['secret-key'],
                            'response': gcaptcha}
        captcha_response = requests.post("https://www.google.com/recaptcha/api/siteverify", data=gcaptcha_payload)
        verified = captcha_response.json()['success']
    else:
        verified = False

    if verified:
        categories = form.getlist('category', None)
        other_categories = form.get('other_tags', None)
        case_date = form.get('case_date', None)
        case_description = form.get('case_description', None)
        email = form.get('email', None)
        name = form.get('name', None)

        # s = 'date: {}  categories: {}  description: {}'.format(case_date, categories, case_description)

        if (case_date is None) or (len(case_date) == 0):
            return redirect(url_for('submit_case', date_class='has-error'))

        if (case_description is None) or (len(case_description) == 0):
            return redirect(url_for('submit_case', date=case_date, desc_class='has-error'))

        if (other_categories is not None) and (len(other_categories) > 0):
            categories.extend([s.strip() for s in other_categories.split(', ')])

        payload = {'Timestamp': datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'),
                   'Date': datetime.datetime.strptime(case_date, '%Y-%m-%d').strftime('%m/%d/%Y'),
                   'Description (optional)': case_description,
                   'Category': ', '.join(categories),
                   'Email': email,
                   'Name': name}

        stsu = write_case_to_sheetsu(payload)
        sql = write_case_to_sqlite(case_date, case_description, categories, name, email)

        return sql

    else:
        return "ERROR - It appears that you are a robot"

def write_case_to_sheetsu(payload, headers={"Content-Type": "application/json"}):
    sheetsu_auth = (sheetsu['API_KEY'], sheetsu['API_SECRET'])
    req = requests.post(url=sheetsu['URL'], headers=headers, json=payload, auth=sheetsu_auth)
    if req.status_code == 201:
        return render_template('submit_success.html',
                               date=payload['Date'],
                               categories=payload['Category'].split(', '),
                               description=payload['Description (optional)'],
                               name=payload['Name'], email=payload['Email'])
    else:
        return "ERROR: {}\nStatus Code: {}".format(req.content, req.status_code)

def write_case_to_sqlite(case_date, case_description, categories, name, email):

    db = get_db()
    query = 'insert into cases (date_submitted, case_date, description, category, name, email) values (?, ?, ?, ?, ?, ?)'

    for category in categories:
        values = [datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                  case_date, case_description, category.lower(), str(name).lower(), str(email).lower()]

        db.execute(query, values)
        db.commit()

    flash("Interesting Case was submitted successfully!")

    return render_template('submit_success.html',
                           date=case_date,
                           categories=categories,
                           description=case_description,
                           name=name, email=email)

@app.route('/worldview/<resource>/<date>')
def worldview_image(resource, date):

    #worldview page
    # https://worldview.earthdata.nasa.gov/?
    # p=geographic&
    # l=MODIS_Aqua_CorrectedReflectance_TrueColor,MODIS_Terra_CorrectedReflectance_TrueColor(hidden),
    #   MODIS_Aqua_CorrectedReflectance_Bands721(hidden),MODIS_Terra_CorrectedReflectance_Bands721(hidden),,
    #   Calipso_Orbit_Asc,Coastlines,,,,,,AMSR2_Cloud_Liquid_Water_Day(hidden),AMSR2_Cloud_Liquid_Water_Night(hidden),
    #   AMSR2_Wind_Speed_Day(hidden),AMSR2_Wind_Speed_Night(hidden),&
    # t=2016-08-19

    # static image
    # http://gibs.earthdata.nasa.gov/image-download?
    # TIME=2016300&
    # extent=extent=-79.875,0,0,60.75&
    # epsg=4326&
    # layers=MODIS_Aqua_CorrectedReflectance_TrueColor,Coastlines&
    # opacities=1,1&
    # worldfile=false&
    # format=image/jpeg&
    # width=909&height=691

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
                 'MODIS_Aqua_CorrectedReflectance_Bands721(hidden),MODIS_Terra_CorrectedReflectance_Bands721(hidden),,' \
                 'Calipso_Orbit_Asc,Coastlines,,,,,,AMSR2_Cloud_Liquid_Water_Day(hidden),AMSR2_Cloud_Liquid_Water_Night(hidden),' \
                 'AMSR2_Wind_Speed_Day(hidden),AMSR2_Wind_Speed_Night(hidden),'
        v = '-160.453125,-57.09375,74.390625,78.1875'

        full_url = '{base_url}?p=geographic&l={layers}&t={date}&v={v}'.format(base_url=base_url, layers=layers, date=date, v=v)

        return redirect(full_url)

    else:

        return None

@app.route('/interesting_cases_old')
def cases():
    # table = pd.read_csv('https://docs.google.com/spreadsheets/d/' +
    #                 '1j-yL-SXwPXMxEzhrx7plkggPYJ6WlHD3EM7gVte7Ba8/' +
    #                 'pub?gid=1851660263&single=true&output=csv',
    #                 names=['tstamp', 'case_date', 'description', 'category', 'name', 'email'],
    #                 parse_dates=[0,],
    #                 header=0)

    table = pd.read_csv('interesting_cases.csv',
                        names=['tstamp', 'case_date', 'description', 'category', 'name', 'email'],
                        parse_dates=[0,],
                        header=0)

    table['case_dt'] = table['case_date'].apply(lambda x: datetime.datetime.strptime(x, '%m/%d/%Y'))
    new_table = table.set_index('case_dt')[['description', 'category']].sort_index()

    grouped = new_table.groupby('category')
    sorted_categories = grouped.count().sort_values('description', ascending=False)

    d = OrderedDict()
    for i, j in sorted_categories.iterrows():
        d[i] = grouped.get_group(i).to_dict()

    #d = new_table.groupby('category').apply(lambda x: x.to_dict()).to_dict()

    return render_template('interesting_cases.html', cases=d)

if __name__ == '__main__':
    # app.run(debug=True, port=8080, host='0.0.0.0')
    # app.run(debug=True, port=8080)
    pass
