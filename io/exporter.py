
styles = {}
for sheet in ['var', 'context', 'costs', 'contextualized_costs', 'scenarios', 'evolution']:
    styles[sheet] = {'color': '#C8D2B2'}
    
for sheet in ['npv', 'synthesis']:
    styles[sheet] = {'color': '#E89194'}
    
for sheet in ['path_sum', 'summaries', 'delta']:
    styles[sheet] = {'color': '#EEC880'}
    
for sheet in ['ts_capex', 'ts_opex','ts_cba', 'ts_costs','ts_evolution', 'ts', 'ts_benefits', 'ts_expenditures', 'ts_cba']:
    styles[sheet] = {'color': '#AACDDA', 'width':5}
    
for sheet in ['xdr_per_unit', 'inflation', 'consumer_price', 'gdp']:
    styles[sheet] = {'color': '#C6A5BE', 'width':5}

styles['test_summaries'] = {'color': '#D0809B', 'width':20}



def save_color_sheet(df, writer, name='Sheet1', color='grey', width=15):
    
    try:
        col_len = len(df.index.levels)
    except AttributeError:
        col_len = 1
    df = df.reset_index()

    df.to_excel(writer, sheet_name=name, index=False)
    # Get the xlsxwriter objects from the dataframe writer object.
    workbook  = writer.book
    worksheet = writer.sheets[name]
    worksheet.set_tab_color(color)

    # Add a header format.
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': color,
        'border': 1})

    
    # Write the column headers with the defined format.
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
    
    for i in range(len(df.columns)):
        worksheet.set_column(i, i, width)
    for i in range(col_len):
        col = df.columns[i]
        worksheet.set_column(i, i, 20)
        for num, value in enumerate(df[col].values):
            try:
                worksheet.write( num+1, i, value, header_format)
            except:
                pass