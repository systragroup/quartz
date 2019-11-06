from quartz.evolution import Extrapolater
from quartz.context import Contextualizer
from quartz.io.exporter import save_color_sheet, styles
from copy import deepcopy

import pandas as pd
import numpy as np
from tqdm import tqdm


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


class Tim(Extrapolater, Contextualizer):
    def __init__(self):
        self.ts_costs = None
        self.var = None
        self.opex = None
        self.capex = None

    def copy(self):
        return deepcopy(self)
    
    def build_time_series(self):

        def var_series(v):
            # change ts_cost.index for a range based on context
            return pd.Series(index=self.ts_costs.index, data=v)

        ts_var = self.var['value'].apply(var_series).T
        columns = [c for c in ts_var.columns if c not in self.ts_costs.columns]
        ts_var = ts_var[columns]

        self.ts = pd.concat([self.ts_costs, ts_var ], axis=1)

    def build_expenditures(self):

        evaluation_period = range(self.first_year, self.last_year+1)

        capex = self.ts_capex.copy()
        opex = self.ts_opex.copy()
        capex['category'] = 'expenditure'
        capex['name'] = 'capex'
        opex['name'] = 'opex'
        expenditures = pd.concat([capex, opex], sort=False)
        expenditures['category'] = 'expenditure'
        expenditures.set_index(['category', 'name'], append=True, inplace=True)
        expenditures = expenditures.reorder_levels(['category', 'name', 'year'])
        expenditures = expenditures.unstack(['category', 'name']).fillna(0)
        expenditures.columns.names = ['scenario', 'category', 'name']
        self.ts_expenditures = expenditures.loc[evaluation_period]

    def build_benefits(self):
        ts_benefits = self.ts_benefits
        assert tuple(ts_benefits.columns.names) == ('scenario', 'category', 'name')
        assert ts_benefits.index.name == 'year'

    def build_cba(self):
        ts_benefits = self.ts_benefits
        ts_expenditures = self.ts_expenditures
        match = self.scenarios.loc['demand_scenario']

        # match cba scens with demand scens
        levels = ['category', 'name']
        selected = ts_benefits.stack(levels)[list(match)]
        selected.columns = match.index
        benefits = selected.unstack(levels)

        ts_cba = -1 * pd.concat([ts_expenditures, benefits ], axis=1)
        ts_cba.sort_index(axis=1, inplace=True)
        ts_cba.sort_index(axis=1, inplace=True)
        self.ts_cba = ts_cba.fillna(0)

    def build_npv(self):

        rate = self.evolution['value']['discount_rate']
        evaluation_period = range(self.first_year, self.last_year+1)

        evaluated = self.ts_cba.loc[evaluation_period]
        discounted = evaluated.apply(lambda c: np.npv(rate, c))
        self.npv = discounted.unstack('scenario')

    def build_synthesis(self):

        rate = self.evolution['value']['discount_rate']
        evaluation_period = range(self.first_year, self.last_year+1)

        ts_sum = self.ts_cba.loc[evaluation_period].groupby(level=['scenario'], axis=1).sum()
        data = {}
        data['irr'] = ts_sum.apply(np.irr) * 100
        data['npv'] = ts_sum.apply(lambda s: np.npv(rate, s))
        self.synthesis = pd.DataFrame(data).T
        self.synthesis.index.name = 'indicator'

    def readable_npv(self, aggregate=False):
        npv = self.npv.groupby(level=0).sum() if aggregate else self.npv

        t = npv.T
        t['total']= npv.sum()
        npv = t.T 
        main = np.round(npv / 1e6).astype(int)
        main =  main.loc[np.abs(main.T.sum()) > 0] 

        
        a = main.loc[[c for c in main.index if 'expenditure' not in c and 'total' not in c]]
        b = main.loc[['expenditure']]
        c = main.loc[['total']]

        main = pd.concat([a,b, c])

        return main

    def to_excel(self, filepath ,styles=styles):
        to_excel_dict = {}
        for name, df in self.__dict__.items():
            if isinstance(df, pd.DataFrame) or isinstance(df, pd.Series):
                if 'ts' in name[:2]:
                    to_excel_dict[name] = df.T
                else:
                    to_excel_dict[name] = df   

            
        with pd.ExcelWriter(filepath, engine='xlsxwriter') as writer:
            for sheet, style in tqdm(styles.items()):
                try:
                    save_color_sheet(to_excel_dict[sheet], writer, name=sheet, **style)
                except KeyError: 
                    pass



