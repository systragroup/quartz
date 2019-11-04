
import six
import numpy as np
import matplotlib.pyplot as plt

class Current:
    def __init__(self):
        self.s = ''
        
    def replace_seen(self, s):
        if self.s == s:
            to_return = ''
        else :
            to_return = s 
        self.s = s
        return to_return

def render_mpl_table(
    data, 
    col_width=3.0, 
    row_height=0.625, 
    font_size=14,
    header_size=14,
    index_width_ratio=2,
    header_color='#9d1a1e', 
    header_font_color = 'w',
    sub_header_color='#d22328',
    row_colors=['#f1f1f2', 'w'], 
    edge_color='w',
    index_edge_color='#9d1a1e',
    bbox=[0, 0, 1, 1], 
    header_columns=0,
    figsize=None,
    ax=None, 
    dpi=96,
    **kwargs
):
    #c_levels = len(data.columns.names)
    #c_first = data.columns.names[0]
    
    
    i_levels = len(data.index.names)
    i_first = list(data.index.names)[0]

    data = data.reset_index()
    current = Current()
    data[i_first] = data[i_first].apply(lambda s: current.replace_seen(s))

    
    if figsize:
        col_width = figsize[0] / (len(data.T) + (index_width_ratio - 1))
        row_height = figsize[1] / (len(data) +1)
        
    if ax is None:
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = plt.subplots(figsize=size, dpi=dpi)
        ax.axis('off')

    mpl_table = ax.table(
        cellText=data.values, 
        bbox=bbox, 
        colLabels=data.columns, 
        colWidths= [col_width * index_width_ratio ] + [col_width for c in data.columns[1:]],
        **kwargs
    )

    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    for k, cell in  six.iteritems(mpl_table._cells):
        cell.set_edgecolor(index_edge_color)
        if k[0] < 1 or k[1] < header_columns:
            #cell.set_text_props(weight='bold', color=header_font_color)

            cell.set_text_props( color=header_font_color)
            cell.set_fontsize(header_size)
            cell.set_facecolor(header_color)

        elif k[1] < i_levels:
            #cell.set_text_props(weight='bold', color=header_font_color)
            cell.set_text_props( color=header_font_color)
            cell.set_fontsize(header_size)
            cell.set_facecolor(sub_header_color)
        else:
            cell.set_edgecolor(edge_color)
            cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
    return ax