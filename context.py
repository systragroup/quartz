import pandas as pd

data = pd.read_excel('data.xlsx', sheet_name=None, index_col=[0, 1])
data = {key: value.reset_index(0, drop=True) for key, value in data.items()}
#data = {key: value.T.interpolate().T for key, value in data.items()}
xdr = data['xdr_per_unit']
consumer_prices = data['consumer_prices']
gdp = data['gdp']

def actualize(country, from_year, to_year, verbose=False, currency=None):
    prices = consumer_prices.loc[country]   
    r = prices[to_year] / prices[from_year]
    if verbose:
        s = "in %s: prices in %i = %.2f * prices in %i" %(country, to_year,r, from_year)
        if currency is not None:
            s+= ' -> 1 %s_%i = %.2f %s_%i' % (currency, from_year, r, currency, to_year)
        print(s)
    return r 

def exchange_rate(from_currency, to_currency, year, verbose=False):
    rates = xdr[year]
    r = rates[from_currency] / rates[to_currency]
    if verbose:
        print("in %i: 1 %s = %.2f %s" %(year, from_currency,r ,  to_currency))
    return r

def localize(from_country, to_country, year, verbose=False):
    ygdp = gdp[year]
    r = ygdp[to_country] / ygdp[from_country]
    if verbose:
        s = "in %i: GNP(%s) / GNP(%s) = %.2f" %(year, to_country, from_country,r)
        s += " -> costs in %s = %.2f * costs in %s" %( to_country,r, from_country)
        print(s)
    return r

def contextualize(
    from_country, 
    from_currency, 
    from_year, 
    to_country=None, 
    to_currency=None, 
    to_year=None,
    to_currency_zone=None,
    verbose=False
):
    if to_currency_zone is None:
        to_currency_zone = to_country

    localization = localize(from_country=from_country, to_country=to_country, year=from_year, verbose=verbose)

    conversion = exchange_rate(from_currency=from_currency, to_currency=to_currency, year=from_year, verbose=verbose)

    actualization = actualize(
        country=to_currency_zone, 
        from_year=from_year, to_year=to_year, verbose=verbose, currency=to_currency)
    product = localization * conversion * actualization
    
    if verbose:    
        s =  '%.2f * %.2f * %.2f = %.2f' % (localization, conversion, actualization, product)
        print(s)
        s = '1 %s_%i in %s -> %.2f %s_%i in %s' % (
            from_currency, from_year, from_country, product,
            to_currency, to_year, to_country
        )
        print(s)
        
    return product

class Contextualizer:
    def __init__(self, year, country, currency):
        self.country = country
        self.year = year
        self.currency = currency
        
    def contextualize_cost(self, data, verbose=False, *args, **kwargs):
        cfactor = contextualize(
            from_country=data['country'],
            from_currency=data['currency'],
            from_year=data['year'], 
            to_country=self.country,
            to_currency=self.currency,
            to_year=self.year,
            to_currency_zone=self.currency_zone,
            verbose=verbose,
            *args, **kwargs
        ) 
        name = str(data.name)
        result = cfactor * data['value']

        if verbose:
            print('%s: %.2f * %.2f =  %.2f' % (name, cfactor,data['value'], result, ))
            print('')
        return result
    
    def contextualize_costs(self, ref_costs, *args, **kwargs):
        costs = ref_costs.copy()
        costs['value'] = ref_costs.apply(self.contextualize_cost, axis=1, *args, **kwargs)
        costs['country'] = self.country
        costs['currency'] = self.currency
        return costs