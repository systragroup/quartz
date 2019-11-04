import urllib3
urllib3.disable_warnings()

import requests
import pandas as pd
from tqdm import tqdm

from bs4 import BeautifulSoup
import os
import datetime

def currency_table(date):

    r = requests.get('https://www.xe.com/en/currencytables/?from=XDR&date=%s' % str(date), verify=False)
    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table', {'id': 'historicalRateTbl'})
    table_body = table.find('tbody')

    data = []
    rows = table_body.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        data.append([ele for ele in cols if ele]) # Get rid of empty values

    df = pd.DataFrame(data)
    df.columns = ['code', 'name', 'units_per_xdr', 'xdr_per_unit']
    df['date'] = str(date)
    return df

def get_xdr(from_year=2000, to_year=None):
    if to_year is None: 
        to_year = datetime.datetime.now().year
    to_concat = []
    for year in tqdm(range(from_year, to_year+1)):
        to_concat.append(currency_table(str(year) + '-01-01'))
        
    history = pd.concat(to_concat)
    history['year'] = history['date'].apply(lambda d : d.split('-')[0]).astype(int)
    for column in ['units_per_xdr', 'xdr_per_unit']:
        history[column] = history[column].str.replace(',', '.').astype(float) 
        
    xdr = history.set_index(['code','name', 'year'])['xdr_per_unit'].sort_index().unstack()
    return xdr

def get_gdp(leave=False):
    # gdp per capita
    r = requests.get('http://api.worldbank.org/v2/en/indicator/NY.GDP.PCAP.CD?downloadformat=excel')
    open('world_bank_gdp.xls', 'wb').write(r.content)
    df = pd.read_excel('world_bank_gdp.xls', sheet_name='Data', header=3, index_col=[1, 2, 0,   3])
    df.columns = [int(year) for year in df.columns]
    gdp = df.reset_index([1, 3], drop=True)
    if not leave:
        os.remove('world_bank_gdp.xls')
    return gdp

def get_inflation(leave=False):
    # inflation
    r = requests.get('http://api.worldbank.org/v2/en/indicator/FP.CPI.TOTL.ZG?downloadformat=excel')
    open('world_bank_inflation.xls', 'wb').write(r.content)
    df = pd.read_excel('world_bank_inflation.xls', sheet_name='Data', header=3, index_col=[1, 2, 0,   3])
    df.columns = [int(year) for year in df.columns]
    inflation = df.reset_index([1, 3], drop=True)
    
    if not leave:
        os.remove('world_bank_inflation.xls')
    return inflation

def get_consumer_prices(leave=False):
    inflation = get_inflation(leave=leave)
    a = 1 + inflation.T / 100
    consumer_prices = a.cumprod().T#.stack()
    return consumer_prices

def build_database(excelfile):
    
    xdr = get_xdr()
    gdp = get_gdp()
    inflation = get_inflation()
    consumer_prices = get_consumer_prices()

    with pd.ExcelWriter(excelfile) as writer:  
        xdr.swaplevel().to_excel(writer, sheet_name='xdr_per_unit')
        inflation.swaplevel().to_excel(writer, sheet_name='inflation')
        consumer_prices.swaplevel().to_excel(writer, sheet_name='consumer_prices')
        gdp.swaplevel().to_excel(writer, sheet_name='gdp')
        
def update_database():
    folder = os.path.dirname(__file__)
    build_database(folder + r'/data.xlsx')