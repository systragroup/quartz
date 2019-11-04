import pandas as pd
import numpy as np

class Extrapolater:
    
    def __init__(self, evolution):
        self.evolution = evolution

    def build_evolution(self):


        a = min(
            self.context['value']['timeline'].min(), 
            self.costs['year'].min()
        )
        b = self.context['value']['timeline'].max()
        period = range(a, b+1)
        df= pd.DataFrame(pd.Series(1, index=period))
        df['year'] = df.index
        for name, value in self.context['value']['timeline'].items():
            df[name] = df['year'] - value

        ts_evolution = self.evolution.apply(
            lambda rate: np.power(1+rate['value'], df[rate['year']]), axis=1).T

        ts_evolution['constant'] = 1
        self.ts_evolution = ts_evolution


        for name, series in self.ts_forecast.items():
            year_name = self.evolution['year'][name]
            year = self.context['value'][('timeline', year_name)]
            s = series / series[year]
            s = s.loc[self.cost_year:]
            self.ts_evolution.loc[s.index, name] = s
        
    def extrapolate_cost(self, cost):
        ts = self.ts_evolution[cost['evolution']]
        delta = ts / ts[cost['year']] - 1 
        evolution_factor = 1 + delta * cost['elasticity']
        return evolution_factor * cost['value']
    
    def extrapolate_costs(self, costs):
        return costs.apply(self.extrapolate_cost, axis=1).T