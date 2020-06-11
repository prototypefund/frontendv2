'''
utility functions for the frontend
'''

from math import isnan

def trend2color(trendvalue):
    '''
    return a color code for a given trend value
    '''
    if isnan(trendvalue):
        return "#999999"
    elif trendvalue > 200:
        # red
        return "#cc0000"
    elif trendvalue < 20:
        # green
        return "#00cc22"
    else:
        # yellow
        return "#ccaa00"
        
def tooltiptext(df):
    '''
    generate texts list for map hoverinfo
    '''
    cols = sorted(df.columns)
    def make_string(df):
        s = ""
        for col in cols:
            s += "{}: {}<br>".format(str(col).capitalize(),str(df[col]))
        return s

    return list(df.apply(lambda x: make_string(x),axis=1))