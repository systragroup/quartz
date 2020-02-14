from quartz.timwrap import TimWrap
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from tqdm import tqdm

rainbow_shades = ["#D22328", "#559BB4", "#91A564", "#DC9100", "#8C4B7D", "#A08C69",
                  "#647D6E", "#5A7382", "#64411E", "#A00037", "#643C5A"]

class TimPlot(TimWrap):

    def build_plot_ts(self):

        self.ts['year'] = self.ts.index
        self.ts['discount'] = np.power(
            1 + self.evolution['value']['discount_rate'], self.first_year-self.ts['year'])
        
        self.ts_discounted_cba = self.ts_cba.apply(lambda s: s*self.ts['discount'])
        self.ts_aggregated_discounted_cba = self.ts_discounted_cba.T.groupby(
            level= ['scenario', 'category']).sum().T

        mdf = pd.DataFrame()
 

        for scen in list(self.ts_cba.columns.levels[0]):

            cba = self.ts_cba[scen].apply(lambda s: s*self.ts['discount'])
            benefit_columns = [c for c in cba.columns if 'expenditure' not in c]

            df = pd.DataFrame(
                {
                    'benefits': cba[benefit_columns].T.sum(), 
                    'expenditures':cba['expenditure'].T.sum(),
                    'delta' : cba.T.sum(),
                    'cumsum': cba.T.sum().cumsum()
                }
            )
            df.index = [str(i) for i in df.index]
            
            mdf[scen] = df.stack()
        mdf = mdf.unstack()
        self.ts_plot = mdf
        
    def plot_discounted_benefits(self, unit='', colors=rainbow_shades, filepath=None):

        discounted_sum = self.ts_plot.swaplevel(axis=1)['cumsum']
        if unit == 'M':
            discounted_sum /= 1e6
            
        plt.rcParams['font.size'] = 12
        plot = discounted_sum.plot(figsize=[12, 5], color=rainbow_shades, linewidth=2)
        plot.axhline(0, color='grey', linewidth=1, linestyle='dotted')
        plot.set_title('Beneficios con descuento')
        plot.set_ylabel(unit + self.currency)

        if filepath:
            plot.get_figure().savefig(filepath,bbox_inches='tight')
            
    def plot_cumulated_discounted_benefits(self, unit='', colors=rainbow_shades, filepath=None):

        discounted_sum = self.ts_plot.swaplevel(axis=1)['cumsum']
        if unit == 'M':
            discounted_sum /= 1e6
            
        plt.rcParams['font.size'] = 12
        
        plot = discounted_sum.cumsum().plot(figsize=[12, 5], color=rainbow_shades, linewidth=2)
        plot.axhline(0, color='grey', linewidth=1, linestyle='dotted')
        plot.set_title('Beneficios acumuladas con descuento')
        plot.set_ylabel(unit + self.currency)
        
        if filepath:
            plot.get_figure().savefig(filepath,bbox_inches='tight')

    def plot_discounted_and_cumulative(self, scen, unit='', filepath=None):
        df = self.ts_plot[scen]
        if unit == 'M':
            df /= 1e6
        plot = df[['benefits']].plot(kind='bar', figsize=[12, 5])
        df[['expenditures']].plot(kind='bar', color='red', ax=plot, rot=90)
        df[['cumsum']].plot(rot=90, color='grey',ax=plot)
        plot.set_ylabel(unit + self.currency)
        plot.set_title('Beneficios y gastos con descuento, por año y cumulate')
        if filepath:
            plot.get_figure().savefig(filepath, bbox_inches='tight')
        return plot

    def plot_discounted(self, scen, unit='', filepath=None):
        df = self.ts_plot[scen]
        if unit == 'M':
            df /= 1e6
        plot = df[[ 'benefits']].plot(kind='bar', figsize=[12, 5])
        df[['expenditures']].plot(kind='bar', color='red', ax=plot, rot=90)
        df[['delta']].plot(rot=90, color='black', ax=plot)
        plot.axhline(0, color='grey', linewidth=0.5)
        plot.set_title('Beneficios y gastos con descuento')
        plot.set_ylabel(unit + self.currency)
        if filepath:
            plot.get_figure().savefig(filepath, bbox_inches='tight')
        return plot

    def plot_discounted_category_cumulative(self, scen, unit='', filepath=None, color=rainbow_shades):
        sums = self.ts_aggregated_discounted_cba[scen].drop('expenditure',axis=1)
        sums = sums.sort_values(self.last_year, axis=1, ascending=False)
        if unit == 'M':
            sums /= 1e6
        plot = sums.cumsum().plot(kind='area', figsize=[12, 5], stacked=True, color=color)
        plot.set_title('Beneficios con descuento por categoria (suma acumulativa)')
        plot.set_ylabel(unit + self.currency)
        if filepath:
            plot.get_figure().savefig(filepath, bbox_inches='tight')
        return plot

    def plot_discounted_category_year(self, scen, unit='', filepath=None, color=rainbow_shades):
        sums = self.ts_aggregated_discounted_cba[scen].drop('expenditure',axis=1)
        sums = sums.sort_values(self.last_year, axis=1, ascending=False)
        
        if unit == 'M':
            sums /= 1e6
        plot = sums.plot(kind='bar', figsize=[12, 5], stacked=True, color=color)
        plot.set_title('Beneficios con descuento por categoria (sumados por año)')
        plot.set_ylabel(unit + self.currency)
        if filepath:
            plot.get_figure().savefig(filepath, bbox_inches='tight')
        return plot

    def plot_discounted_category(self, scen, unit='', filepath=None, color=rainbow_shades):
        sums = self.ts_aggregated_discounted_cba[scen].drop('expenditure',axis=1)
        sums = sums.sort_values(self.last_year, axis=1, ascending=False)
        if unit == 'M':
            sums /= 1e6
        plot = sums.plot(kind='line', linewidth=2, figsize=[12, 5], stacked=False, color=color)
        plot.set_title('Beneficios con descuento por categoria')
        plot.set_ylabel(unit + self.currency)
        if filepath:
            plot.get_figure().savefig(filepath, bbox_inches='tight')
        return plot

    def oned_plot_tests(self, tests, kind='line', plot_path=''):
        
        base = self.copy()
        discount_rate = base.evolution['value']['discount_rate']
        x = list(tests.keys())[0]
        x_ref = list(tests.values())[0][0]
        dflist = [pd.DataFrame({key: value, 'join': 'join'}) for key, value in tests.items()]
        merged = pd.DataFrame({'join': ['join']})
        for df in dflist:
            merged = pd.merge(merged, df, on='join')
        all_kwargs = merged.drop('join', axis=1).to_dict(orient='records')

        data = []    
        for kwargs in tqdm(all_kwargs):
            tim = base.copy()
            tim.build(**kwargs)
            tim.synthesis.loc['npv'] = np.round(tim.synthesis.loc['npv'] / 1e6).astype(int)
            s = tim.synthesis.T.reset_index()
            data.append(pd.concat([s, s['irr'].apply(lambda x: pd.Series(kwargs))], axis=1))
        self.all_data.append(data)
            
        df = pd.concat(data).set_index( [x, 'scenario']).drop_duplicates()

        plot = df['irr'].unstack('scenario').plot(figsize=[10, 5], kind=kind, color=rainbow_shades, rot=0)
        plot.set_ylabel('irr')
        plot.axhline(discount_rate*100, color='black',linestyle='dashed',linewidth=1)
        if kind is 'line':
            plot.axvline(x_ref, color='black',linestyle='dashed',linewidth=1)
        plot.set_title('irr vs %s' % x)
        fig = plot.get_figure()
        fig.savefig(plot_path +'irr_vs_%s.png' % x, bbox_inches='tight')
        
        plot = df['npv'].unstack('scenario').plot(figsize=[10, 5], kind=kind, color=rainbow_shades, rot=0)
        plot.axhline(0, color='black',linestyle='dashed',linewidth=1)
        if kind is 'line':
            plot.axvline(x_ref, color='black',linestyle='dashed',linewidth=1)
        plot.set_ylabel('npv')
        plot.set_title('npv vs %s' % x)
        fig = plot.get_figure()
        fig.savefig(plot_path+'npv_vs_%s.png' % x, bbox_inches='tight')