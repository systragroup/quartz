from quartz.timplot import TimPlot
from quartz.timtest import TimTest
import pandas as pd

def read_excel(path):
    tim = Tim()
    data = pd.read_excel(path, sheet_name=None, index_col=0)

    data['costs'] = pd.read_excel(path, sheet_name='costs', index_col=[0,1])
    data['var'] = pd.read_excel(path, sheet_name='var', index_col=[0, 1])
    data['context'] = pd.read_excel(path, sheet_name='context', index_col=[0, 1])

    def time_frame(df):
        tf = df.T
        tf.index.name = 'year'
        return tf

    data = {k: v if 'ts_' not in k else time_frame(v) for k, v in data.items()}

    for key, value in data.items():
        tim.__setattr__(key, value)

    # easier access to costs 
    for key, value in data['context']['value']['cost'].items():
        tim.__setattr__(key, value)
    for key, value in data['context']['value']['timeline'].items():
        tim.__setattr__(key, value)

    return tim

class Tim(TimPlot, TimTest):
    def __init__(self):
        pass
