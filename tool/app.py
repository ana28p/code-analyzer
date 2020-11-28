import os
import pathlib as pl

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px

import flask

import numpy as np
import pandas as pd

from clustering import ClusteringType, analysis
from helpers import scale_data, get_tree_map_data

APP_PATH = str(pl.Path(__file__).parent.resolve())

app = dash.Dash(__name__)
server = app.server
app.config.suppress_callback_exceptions = True

# Projects:
TAX_COMPARE = 'tax-compare'

intro_text = """
**About this app**

This apps groups the method metrics in 3 groups of criticality: high, regular and low. 
There three ways to do it:
- threshold-based by summing the metrics and split de groups in >90% as high, 70-90% as regular, and <70% as low
- K-means clustering algorithm groups the method in 3 clusters; the classification in the 3 levels of criticality
 is based on total mean value of the values from a cluster
- Expectation-Maximisation (EM) clustering algorithm groups the method in 3 clusters; the classification in the 3 levels
 of criticality is based on total mean value of the values from a cluster

"""


# Dash App Layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=True),
    dcc.Store(id='project-name'),
    html.Div(id='page-content')
])

index_page = html.Div([
    html.H4("Wrong path"),
    html.Hr(),
    html.P("Available projects to visualise:"),
    dcc.Link('TAX-Compare', href='/tax-compare'),
])

myapp_layout = html.Div(
    children=[
        dcc.Store(id="metrics-data-store"),
        dcc.Store(id="coverage-data-store"),
        dcc.Store(id="classification-data-store"),
        html.Div(id="title"),
        html.Hr(),
        html.Div(id="intro-text", children=dcc.Markdown(intro_text)),
        html.Hr(),
        html.P("Variables Options"),
        dcc.Checklist(
            id="data-metrics",
            options=[],
            # value=dashboard_pj.metrics_List,
            labelStyle={'display': 'inline-block', 'margin': '5px'}
        ),
        html.Div(
            children=[
                html.Div(
                    html.Button(
                        "Run threshold clustering",
                        id="btn-clust-th",
                        title="Click to run threshold clustering",
                        n_clicks=0,
                        n_clicks_timestamp=0,
                    ),
                    className="btn-outer",
                ),
                html.Div(
                    html.Button(
                        "Run k-means clustering",
                        id="btn-clust-km",
                        title="Click to run k-means clustering",
                        n_clicks=0,
                        n_clicks_timestamp=0,
                    ),
                    className="btn-outer",
                ),
                html.Div(
                    html.Button(
                        "Run EM clustering",
                        id="btn-clust-em",
                        title="Click to run EM clustering",
                        n_clicks=0,
                        n_clicks_timestamp=0,
                    ),
                    className="btn-outer",
                ),
            ],
            style={'display': 'inline-flex', 'width': '100%'}
        ),
        html.Hr(),
        html.Div(
            children=[
                html.Div(
                    children=[
                        html.P("Test coverage"),
                        html.Hr(),
                        html.P("Pie charts"),
                        html.Hr(),
                        html.P("Table"),
                        html.Hr(),
                    ],
                    className="seven columns named-card",
                ),
                html.Div(
                    children=[
                        html.P("Classification"),
                        html.Hr(),
                        html.P("Total"),
                        html.Hr(),
                        html.P("Graph"),
                        html.Hr(),
                        html.P("PCA"),
                        html.Hr(),
                    ],
                    className="five columns named-card",
                ),
            ],
            className="twelve columns",
        ),
        html.Hr(),
        html.P("Tree map"),
        dcc.Graph(id="data-tree-map", config={'scrollZoom': True}),
    ],
    className="container twelve columns",
)


# =====Callbacks=====
@app.callback(
    dash.dependencies.Output('project-name', 'data'),
    [dash.dependencies.Input('url', 'pathname')])
def update_project(pathname):
    name = pathname.strip('/')
    return name


@app.callback(
    dash.dependencies.Output('page-content', 'children'),
    [dash.dependencies.Input('project-name', 'data')])
def update_layout(project):
    print("try to switch to layout: ", project)
    if project == TAX_COMPARE:
        return myapp_layout
    else:
        return index_page


@app.callback(
    dash.dependencies.Output('title', 'children'),
    [dash.dependencies.Input('project-name', 'data')])
def update_header(project):
    info = ''
    if project:
        info += ' for project ' + project
    return html.Div(
        [
            html.H4("Criticality Clustering" + info),
        ],
        className="header__title",
    )


@app.callback(
    dash.dependencies.Output('metrics-data-store', 'data'),
    [dash.dependencies.Input('project-name', 'data')])
def update_metrics_data_store(project):
    if project:
        path = os.path.join(APP_PATH, os.path.join("data", project + "/metrics.csv"))
        return pd.read_csv(path, sep=';').to_json()
    else:
        return None


@app.callback(
    dash.dependencies.Output('coverage-data-store', 'data'),
    [dash.dependencies.Input('project-name', 'data')])
def update_test_coverage_data_store(project):
    if project:
        path = os.path.join(APP_PATH, os.path.join("data", project + "/test_coverage.csv"))
        return pd.read_csv(path, sep=';').to_json()
    else:
        return None


@app.callback(
    dash.dependencies.Output('data-metrics', 'options'),
    [dash.dependencies.Input('metrics-data-store', 'data')])
def update_metrics_options_dict(metrics_ds):
    metrics_list = []
    if metrics_ds is not None:
        df = pd.read_json(metrics_ds)
        metrics_list = list(df.select_dtypes(include=[np.number]).columns.values)
        # metrics_list = ['LOC', 'CC', 'NP', 'NV', 'NEST', 'Ca', 'Ce', 'NChg', 'NCall']
    metrics_map = []
    for metric in metrics_list:
        metrics_map.append({"label": metric, "value": metric})
    return metrics_map


@app.callback(
    Output("classification-data-store", "data"),
    [Input("btn-clust-th", "n_clicks_timestamp"),
     Input("btn-clust-km", "n_clicks_timestamp"),
     Input("btn-clust-em", "n_clicks_timestamp")],
    [
        State("metrics-data-store", "data"),
        State("data-metrics", "value"),
    ],
)
def update_clustered_ds(btn_th, btn_km, btn_em, metrics_ds, selected_metrics):
    clust_type = None
    if int(btn_th) > int(btn_km) and int(btn_th) > int(btn_em):
        clust_type = ClusteringType.THRESHOLD
    elif int(btn_km) > int(btn_th) and int(btn_km) > int(btn_em):
        clust_type = ClusteringType.K_MEANS
    elif int(btn_em) > int(btn_th) and int(btn_em) > int(btn_km):
        clust_type = ClusteringType.EM

    if (clust_type is not None) and (metrics_ds is not None) and (len(selected_metrics) > 0):
        df = pd.read_json(metrics_ds)
        classified_data = analysis(df, selected_metrics, clust_type)
        return classified_data.to_json()
    return None


@app.callback(
    Output("data-tree-map", "figure"),
    [Input("classification-data-store", "data")],
    [
        State("metrics-data-store", "data"),
        State("data-metrics", "value"),
    ],
)
def update_tree_map(clustered_ds, metrics_ds, selected_metrics):
    if clustered_ds:
        df = pd.read_json(clustered_ds)
        data_class = get_tree_map_data(df, 'Method')
        config = dict({'scrollZoom': True})
        fig = px.treemap(data_class, path=['Parent_class', 'Class', 'Method'], values='LOC', color='CLevel',
                         color_discrete_map={'(?)': 'black', 'low': 'blue', 'regular': 'yellow', 'high': 'red'})
        return fig
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


if __name__ == "__main__":
    app.run_server(
        debug=True, port=8051, dev_tools_hot_reload=False, use_reloader=False
    )
