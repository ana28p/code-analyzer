import io
import base64

import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objs as go
import pandas as pd

# df = pd.read_excel(
#     "C:/Users/aprodea/Documents/salesfunnel.xlsx"
# )
# mgr_options = df["Manager"].unique()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.H2("Sales Funnel Report"),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Div(id='table'),
    html.Div(id='output-data-upload'),
    dcc.Graph(id='funnel-graph'),
])


def parse_contents(contents, filename):
    if contents is not None:
        content_type, content_string = contents.split(',')

        decoded = base64.b64decode(content_string)

        try:
            if 'csv' in filename:
                # Assume that the user uploaded a CSV file
                df = pd.read_csv(
                    io.StringIO(decoded.decode('utf-8')))
            elif 'xlsx' in filename:
                # Assume that the user uploaded an excel file
                df = pd.read_excel(io.BytesIO(decoded))
        except Exception as e:
            print(e)
            return html.Div([
                'There was an error processing this file.'
            ])

        return df
    else:
        return [{}]


# @app.callback(Output('table', 'data'),
@app.callback(Output('output-data-upload', 'children'),
              [Input('upload-data', 'contents'),
              Input('upload-data', 'filename')])
def update_output(contents, filename):
    if contents is not None:
        df = parse_contents(contents, filename)
        if df is not None:
            return df
        else:
            return [{}]
    else:
        return [{}]


@app.callback(
    Output('funnel-graph', 'figure'),
    [Input('upload-data', 'contents'),
     Input('upload-data', 'filename')])
def plot_graph(contents, filename):
    df = parse_contents(contents, filename)
    if not df:
        df_plot = df.copy()
        pv = pd.pivot_table(
            df_plot,
            index=['Name'],
            columns=["Status"],
            values=['Quantity'],
            aggfunc=sum,
            fill_value=0)

        trace1 = go.Bar(x=pv.index, y=pv[('Quantity', 'declined')], name='Declined')
        trace2 = go.Bar(x=pv.index, y=pv[('Quantity', 'pending')], name='Pending')
        trace3 = go.Bar(x=pv.index, y=pv[('Quantity', 'presented')], name='Presented')
        trace4 = go.Bar(x=pv.index, y=pv[('Quantity', 'won')], name='Won')

        layout = go.Layout(
            title='funnel-graph'
        )
        fig = go.Figure(data=[trace1, trace2, trace3, trace4], layout=layout)
        return fig
    else:
        return {
            "layout": {
                "xaxis": {
                    "visible": False
                },
                "yaxis": {
                    "visible": False
                },
                "annotations": [
                    {
                        "text": "No available data",
                        "xref": "paper",
                        "yref": "paper",
                        "showarrow": False,
                        "font": {
                            "size": 28
                        }
                    }
                ]
            }
        }

    # return {
    #     'data': [trace1, trace2, trace3, trace4],
    #     'layout':
    #         go.Layout(
    #             title='Customer Order Status for {}'.format("All Managers"),
    #             barmode='stack')
    # }


if __name__ == '__main__':
    app.run_server(debug=True)