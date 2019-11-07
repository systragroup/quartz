from quartz.evolution import Extrapolater
from quartz.context import Contextualizer
from quartz.io.exporter import save_color_sheet, styles
from quartz import context
from copy import deepcopy

import pandas as pd
import numpy as np
from tqdm import tqdm


kg_to_ton = 1 / 1000
m_to_km = 1 / 1000
sec_to_hour = 1 / 3600




class TimWrap(Extrapolater, Contextualizer):
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

    def build_contextualized_costs(self):
        self.contextualized_costs = self.contextualize_costs(self.costs)

    def build_ts_costs(self):
        self.ts_costs = self.extrapolate_costs(self.contextualized_costs)

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

    def build_climate_change(self):

        ts = self.ts
        prop = ts[('proportion_diesel', 'car')]

        for cost in ['carbon', 'fuel']:
            for mode in (self.ts['proportion_diesel'].columns):
                mix = prop * ts[(cost,'diesel')] + (1-prop) * ts[(cost,'gasoline')]
                ts[(cost, mode)] = mix 

        for mode in ts['consumption'].columns:
            if ts[('consumption', mode)].sum() == 0:
                continue
            try:
                ts[('climate_change', mode)] = ts[('consumption', mode)] * ts[
                    ('carbon', mode)] * ts[('carbon', 'carbon_price')] * kg_to_ton
                ts[('fuel', mode)] = ts[('consumption', mode)] * ts[('fuel', mode)]
            except KeyError:
                print('could not compute fuel related externalities for mode: ' + mode)

    def _interpolate_path_sum(self, scenario):
        "for a given cba_scenario, interpolate path_sum data from demand_scenario"
        ref_path_sum = {}
        for year, year_reference in self.ts_scenarios[scenario].dropna(how='all').items():
            ref_path_sum[year] = self.path_sum.unstack('scenario').get(year_reference, np.nan)
        df = pd.DataFrame(ref_path_sum).T
        dense = df.reindex(self.ts.index).interpolate(method='index').fillna(method='bfill').fillna(method='ffill')
        dense.index.name = 'year'
        return dense.unstack()

    def build_ts_delta(self, reference='reference'):
        proto_dict = {scenario: self._interpolate_path_sum(scenario) for scenario in self.ts_scenarios.columns } 
        df = pd.DataFrame(proto_dict)
        df.columns.name = 'scenario'
        
        delta = df.apply(lambda s: s-df[reference])
        segment_sum = delta.unstack('segment').stack('scenario').T.sum()
        segment_sum = segment_sum.unstack('year').reorder_levels(['scenario', 'indicator', 'route_type'])
        ts_delta = segment_sum.sort_index().T
        
        self.ts_delta = ts_delta

    def return_cba_ts(self, scenario, verbose=False):
        
        ts = self.ts
        
        var = self.var['value']
        model_to_year = var[('demand', 'model_to_day')] * var[('demand', 'day_to_year')]
        
        scen_length = self.ts_delta[scenario, 'length'] * model_to_year
        
        # find the costs and externalities that are related to vehicle km
        km_costs = self.costs.loc[self.costs['unit'] == 'km']
        km_cost_categories = list(set(km_costs.reset_index()['category'])) + ['climate_change', 'fuel']
        # km_cost_categories = ['noise', 'local_pollution'] for example
        
        # compute vehicle_km related externalities
        if verbose:
            print('externalities: ' + str(km_cost_categories))

        cba = pd.DataFrame()
        for mode, occupancy_rate in var['occupancy'].items():  
            try:
                delta = scen_length[mode] / occupancy_rate * m_to_km
                ts[('delta_vehicle', mode)] = delta 

                # compute benefit for every externality
                for ext in km_cost_categories:
                    try:
                        cba[(ext, mode)] =  ts[(ext, mode)] * ts[('delta_vehicle', mode)]
                    except KeyError: 
                        if verbose:
                            print('could not compute externality: mode=%s ext=%s' %  (mode, ext))
            except KeyError:
                if verbose:
                    print('could not compute any externality: mode=%s' %  (mode))
                pass

        # reshape
        t = cba.T.sort_index()
        t.index = pd.MultiIndex.from_tuples(t.index)
        cba = t.T
        cba.index.name = 'year'
        cba.columns.names = ['category', 'name']
        
        # time_savings
        scen_time = self.ts_delta[scenario, 'time'].T.sum() * model_to_year
        all_time_savings = scen_time * ts[('value_of_time', 'average')] * sec_to_hour
        cba[('time_savings', 'all')] = all_time_savings
        
        # cut benefits before commissioning_year
        self.ts[('demand', 'bool')] = self.ts_evolution['constant']
        self.ts.loc[:self.commissioning_year-1, [('demand', 'bool')]]= 0
        cba = cba.apply(lambda s: s*self.ts[('demand', 'bool')])
        
        return cba

    def build_ts_benefits(self, *args, **kwargs):
    
        scenarios = list(self.ts_scenarios.columns)[1:]
        all_cba = pd.DataFrame()
        for scen_name in scenarios:
            all_cba[scen_name] = self.return_cba_ts(scen_name, *args, **kwargs).T.stack()

        ts_benefits = all_cba.unstack(['category', 'name'])
        ts_benefits.columns.names = ['scenario', 'category', 'name']
        self.ts_benefits = ts_benefits
        
    def set_scenarios(self):
        # copy interpolated demand scenarios in scenarios sheet
        scenarios = list(self.ts_scenarios.columns)[1:]
        df = pd.DataFrame({'demand_scenario':scenarios}, index=scenarios)
        df.index.name = 'name'
        self.scenarios = df.T

    def build(
        self, 
        capex=1, 
        demand=1, 
        opex=1, 
        commissioning=None, 
        gdp_growth=None, 
        carbon_price=None,
        *args, 
        **kwargs
    ):
        
        # carbon_price
        if carbon_price:   
            self.costs.loc[('carbon', 'carbon_price')] = self.costs.loc[('carbon', carbon_price)]
        
        # commissioning
        if commissioning:
            self.commissioning_year = commissioning
        
        # gdp evolution
        if gdp_growth:
            self.evolution.loc['gdp_per_capita', 'value'] = gdp_growth
            
        self.build_evolution()
        
        # demand
        self.path_sum *= demand
        
        # capex
        self.ts_capex *= capex
        
        # opex
        self.ts_opex *= opex
        
        # include world bank data into GDP history
        past = self.ts_evolution.loc[:self.cost_year].index
        gdp = context.data['gdp'].loc[self.country]
        self.ts_evolution.loc[past, 'gdp_per_capita'] = gdp[past] / gdp[self.cost_year]
        
        self.build_contextualized_costs()
        self.build_ts_costs()
        self.build_time_series()
        self.build_climate_change()
        self.build_ts_delta()
        self.build_ts_benefits(*args, **kwargs)
        self.set_scenarios()
        self.build_expenditures()
        self.build_cba()
        self.build_npv()
        self.build_synthesis()

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



