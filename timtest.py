from quartz.timwrap import TimWrap
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

rainbow_shades = ["#D22328", "#559BB4", "#91A564", "#DC9100", "#8C4B7D", "#A08C69",
                  "#647D6E", "#5A7382", "#64411E", "#A00037", "#643C5A"]

class TimTest(TimWrap):
    def __init__(self):
        pass

    def build_tests(self):
        flat = []
        for d in self.all_data:
            flat = flat + d

        df = pd.concat(flat, sort=False)
        try:
            df['commissioning'] = df['commissioning'].fillna(self.commissioning_year)
            df['commissioning'] = df['commissioning'].astype(int)
        except:
            pass
        df = df.fillna(1)
        df = df.drop_duplicates()
        order = [c for c in df.columns if c not in ['npv', 'irr']] + ['npv', 'irr']
        df = df[order].sort_values(by=order)
        indicator_tests = df.set_index(order).reset_index(['npv', 'irr'])
        self.test_summaries = indicator_tests
    