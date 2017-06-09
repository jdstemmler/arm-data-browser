import pandas as pd
import sqlite3
import datetime

def cases():

    table = pd.read_csv('https://docs.google.com/spreadsheets/d/' +
                    '1j-yL-SXwPXMxEzhrx7plkggPYJ6WlHD3EM7gVte7Ba8/' +
                    'pub?gid=1851660263&single=true&output=csv',
                    names=['tstamp', 'case_date', 'description', 'category', 'name', 'email'],
                    parse_dates=[0,],
                    header=0)

    table['case_dt'] = table['case_date'].apply(lambda x: datetime.datetime.strptime(x, '%m/%d/%Y'))

    return table

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect('instance/cases.db')
    rv.row_factory = sqlite3.Row
    return rv

def write_rows():
    db = connect_db()
    table = cases()

    query = 'insert into cases (date_submitted, case_date, description, category, name, email) values (?, ?, ?, ?, ?, ?)'

    for row in table.itertuples(name="InterestingCase"):
        for category in row.category.split(', '):
            values = [row.tstamp.strftime('%Y-%m-%d %H:%M:%S'), row.case_dt.strftime('%Y-%m-%d'),
                      row.description, category.lower(), str(row.name).lower(), str(row.email).lower()]
            db.execute(query, values)
            db.commit()

        print("Inserted Row")

if __name__ == "__main__":
    write_rows()
