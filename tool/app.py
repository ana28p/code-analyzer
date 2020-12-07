import os
import pathlib as pl
from urllib.parse import quote as urlquote

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from flask import send_file

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
 
Select at least one variable, then click on the type of clustering you want to perform. 
The clustering is based on the selected variables. The computing and rendering of the visualisations might take a few seconds.

"""


@server.route("/download/<path:path>")
def download(path):
    print('download', path)
    # if '/app/app/' in path:
    #     path = path.replace('/app/app/', '')
    return send_file(path, mimetype='text/csv', as_attachment=True)


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
                        html.P("Classification"),
                        html.Hr(),
                        html.Div(id="cluster_result"),
                    ],
                    className="eight columns named-card",
                ),
                html.Div(
                    children=[
                        html.P("Test coverage"),
                        html.Hr(),
                        html.Div(id="test_coverage"),
                    ],
                    className="four columns named-card",
                ),
            ],
            className="twelve columns",
        ),
        html.Hr(),
        html.Div(
            id="data-listed",
            className="twelve columns",
            ),
    ],
    className="container twelve columns",
)


# ======Placeholders and Elements=====
def no_available_data():
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


def get_no_available_data_div_figure():
    return dcc.Graph(figure=no_available_data())


def get_empty_div():
    return html.Div()


def get_pie_charts(low_data, regular_data, high_data):
    labels = ['Covered', 'Uncovered']

    l_values = [low_data['CoveredStatements'].sum(), low_data['TotalStatements'].sum() - low_data['CoveredStatements'].sum()]
    r_values = [regular_data['CoveredStatements'].sum(),
                regular_data['TotalStatements'].sum() - regular_data['CoveredStatements'].sum()]
    h_values = [high_data['CoveredStatements'].sum(), high_data['TotalStatements'].sum() - high_data['CoveredStatements'].sum()]

    fig = make_subplots(rows=3, cols=1, specs=[[{'type': 'domain'}], [{'type': 'domain'}], [{'type': 'domain'}]])
    fig.add_trace(go.Pie(labels=labels, values=l_values, name="Low", marker_colors=["cornflowerblue", "lightskyblue"]),
                  1, 1)
    fig.add_trace(go.Pie(labels=labels, values=r_values, name="Regular", marker_colors=["goldenrod", "wheat"]),
                  2, 1)
    fig.add_trace(go.Pie(labels=labels, values=h_values, name="High", marker_colors=["firebrick", "salmon"]),
                  3, 1)

    # Use `hole` to create a donut-like pie chart
    fig.update_traces(hole=.4, hoverinfo="label+percent+name")

    fig.update_layout(
        showlegend=False,
        annotations=[dict(text='Low', y=0.89, x=0.5, font_size=15, showarrow=False),
                     dict(text='Regular', y=0.5, x=0.5, font_size=15, showarrow=False),
                     dict(text='High', y=0.11, x=0.5, font_size=15, showarrow=False)],
        height=700)

    return fig


def test_coverage_elements(data_coverage):
    total_coverage = data_coverage['CoveredStatements'].sum() / data_coverage['TotalStatements'].sum()

    low = data_coverage[data_coverage['CLevel'] == "low"]
    regular = data_coverage[data_coverage['CLevel'] == "regular"]
    high = data_coverage[data_coverage['CLevel'] == "high"]

    return [
        html.P("Total coverage: " + str(round(total_coverage * 100, 2)) + "%"),
        dcc.Graph(figure=get_pie_charts(low, regular, high)),
    ]


def get_strip_plot(data):
    stripfig = px.strip(
        data_frame=data,
        x='variable',
        y='value',
        category_orders={"CLevel": ["low", "regular", "high"]},
        hover_data=['Method'],
        color='CLevel',
        color_discrete_map={"high": "firebrick", "regular": "goldenrod", "low": "cornflowerblue"},
        facet_col_spacing=0.5,
    )

    stripfig.update_traces(dict(marker_line_width=0.5, marker_line_color="grey"))
    stripfig.update_layout(
        # title_text="",
        height=500,
        # width=900,
        margin=dict(l=0, r=0, t=0, b=0),
        template="plotly_white"
    )
    return stripfig


def get_methods_splitted_bar(dict_splitted):
    colors = ["cornflowerblue", "goldenrod", "firebrick"]

    top_labels = list(dict_splitted.keys())
    x_data = list(dict_splitted.values())
    yd = 0

    fig = go.Figure()

    for i in range(0, len(x_data)):
        fig.add_trace(go.Bar(
            x=[x_data[i]], y=[yd],
            orientation='h',
            marker=dict(
                color=colors[i],
                line=dict(color='white', width=1)
            )
        ))

    fig.update_layout(
        xaxis=dict(
            showgrid=False,
            showline=False,
            showticklabels=False,
            zeroline=False,
            domain=[0.15, 1]
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            showticklabels=False,
            zeroline=False,
        ),
        barmode='stack',
        paper_bgcolor='white',
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=20, b=0),
        height=50,
        showlegend=False,
    )

    annotations = []

    space = 0
    for i in range(len(x_data)):
        annotations.append(dict(xref='x', yref='y',
                                x=space + (x_data[i] / 2), y=yd,
                                text=str(x_data[i]),
                                font=dict(family='Arial', size=14, color='white'),
                                showarrow=False))

        annotations.append(dict(xref='x', yref='paper',
                                x=space + (x_data[i] / 2), y=1.5,
                                text="<i>" + top_labels[i] + "</i>",
                                font=dict(family='Arial', size=14, color='rgb(67, 67, 67)'),
                                showarrow=False))
        space += x_data[i]

    fig.update_layout(annotations=annotations)

    return fig


def cluster_result_elements(melted_data, dict_split):
    total_number_methods = sum(list(dict_split.values()))

    return [
        html.P("Total number of methods: " + str(total_number_methods)),
        dcc.Graph(figure=get_methods_splitted_bar(dict_split), config={'responsive': False, 'staticPlot': True}),
        html.P("Distribution of the scaled variables for each group"),
        dcc.Graph(figure=get_strip_plot(melted_data)),
        # html.P("PCA"),
    ]


def get_tree_map_figure(data):
    data_class = get_tree_map_data(data.copy(), 'Method')
    fig = px.treemap(data_class, path=['Parent_class', 'Class', 'Method'], values='LOC', color='CLevel',
                     # color_discrete_map={'(?)': 'black', "high": "firebrick", "regular": "goldenrod",
                     #                     "low": "cornflowerblue"}
                     color_discrete_map={'(?)': 'black', "high": "salmon", "regular": "wheat",
                                         "low": "lightskyblue"}
                     )
    return fig


def get_uncoverage_percentage(row):
    total, covered = row['TotalStatements'], row['CoveredStatements']
    percentage = 100 * (total - covered) / total
    return round(percentage, 2)


def file_download_link(project_name, result):
    """Create a Plotly Dash 'A' element that downloads a file from the app."""
    filename_path = os.path.join("data", project_name, "result.csv")
    path = os.path.join(APP_PATH, filename_path)
    # print('write the result on disk first. columns: ', result.columns)
    print('write results to ', path)
    result.to_csv(path, sep=';', index=False)
    location = "/download/{}".format(urlquote(filename_path))
    return html.A("Download the result data in CSV format", href=location)


def data_listed_elements(metrics_data, coverage_data, project_name):
    data_combined = pd.merge(metrics_data, coverage_data, on='Method', how='left')

    data_combined['UncoveragePercentage'] = data_combined.apply(lambda row: get_uncoverage_percentage(row), axis=1)

    nr_columns = list(data_combined.columns)
    nr_columns.remove('Method')

    return [
        html.P("Tree map visualisation of the methods and the table with all the data"),
        dcc.Markdown("""The size of the elements in the treemap is based on the methods LOC variable
                     and the color represent their criticality level."""),
        html.Hr(),
        dcc.Graph(figure=get_tree_map_figure(data_combined), config={'scrollZoom': True}, style={'height': '700px'}),
        html.Div(file_download_link(project_name, data_combined)),
        dash_table.DataTable(id="info-table",
                             data=data_combined.to_dict(orient='records'),
                             columns=[{'name': i, 'id': i} for i in data_combined.columns],
                             page_current=0,
                             page_size=20,
                             page_action='custom',

                             filter_action='custom',
                             filter_query='',

                             sort_action='custom',
                             sort_mode='multi',
                             sort_by=[],

                             css=[{
                                 'selector': 'table',
                                 'rule': 'table-layout: fixed'  # note - this does not work with fixed_rows
                             }],
                             style_data={
                                 # 'width': '{}%'.format(100. / len(data_combined.columns)),
                                 'textOverflow': 'hidden'
                             },
                             style_header_conditional=(
                                 [
                                     {'if': {'column_id': 'Method'},
                                      'width': '40%'
                                      },
                                 ] +
                                 [
                                     {
                                         'if': {'column_id': col},
                                         'width': '{}%'.format(60. / len(nr_columns)),
                                     } for col in nr_columns

                                 ]
                             ),
                             style_data_conditional=[
                                 {
                                     'if': {
                                         'filter_query': '{CLevel} = low',
                                     },
                                     'backgroundColor': 'lightskyblue',
                                     'color': 'black'
                                 },
                                 {
                                     'if': {
                                         'filter_query': '{CLevel} = regular',
                                     },
                                     'backgroundColor': 'wheat',
                                     'color': 'black'
                                 },
                                 {
                                     'if': {
                                         'filter_query': '{CLevel} = high',
                                     },
                                     'backgroundColor': 'salmon',
                                     'color': 'black'
                                 },
                             ],

                             style_cell=dict(textAlign='left'),
                             )
    ]


# =====Callbacks=====
@app.callback(
    Output('project-name', 'data'),
    [Input('url', 'pathname')])
def update_project(pathname):
    name = pathname.strip('/')
    return name


@app.callback(
    Output('page-content', 'children'),
    [Input('project-name', 'data')])
def update_layout(project):
    print("try to switch to layout: ", project)
    if project == TAX_COMPARE:
        return myapp_layout
    else:
        return index_page


@app.callback(
    Output('title', 'children'),
    [Input('project-name', 'data')])
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
    Output('metrics-data-store', 'data'),
    [Input('project-name', 'data')])
def update_metrics_data_store(project):
    if project:
        path = os.path.join(APP_PATH, os.path.join("data", project + "/metrics.csv"))
        return pd.read_csv(path, sep=';').to_json()
    else:
        return None


@app.callback(
    Output('coverage-data-store', 'data'),
    [Input('project-name', 'data')])
def update_test_coverage_data_store(project):
    if project:
        path = os.path.join(APP_PATH, os.path.join("data", project + "/test_coverage.csv"))
        return pd.read_csv(path, sep=';').to_json()
    else:
        return None


@app.callback(
    Output('data-metrics', 'options'),
    [Input('metrics-data-store', 'data')])
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

    if (clust_type is not None) and (metrics_ds is not None) and selected_metrics and (len(selected_metrics) > 0):
        df = pd.read_json(metrics_ds)
        classified_data = analysis(df, selected_metrics, clust_type)
        return classified_data.to_json()
    return None


@app.callback(
    Output("test_coverage", "children"),
    [Input("classification-data-store", "data")],
    [
        State("coverage-data-store", "data"),
        State('data-metrics', 'options'),
    ],
)
def update_test_coverage(clustered_ds, coverage_ds, selected_metrics):
    if clustered_ds and coverage_ds:
        df = pd.read_json(clustered_ds)
        test_data = pd.read_json(coverage_ds)
        data_combined = pd.merge(df[['Method', 'CLevel']], test_data, on='Method', how='left')

        return test_coverage_elements(data_combined)
    else:
        return get_no_available_data_div_figure()


@app.callback(
    Output("cluster_result", "children"),
    [Input("classification-data-store", "data")],
    [
        State("data-metrics", "options"),
    ],
)
def update_cluster_result(clustered_ds, data_metrics_options):
    if clustered_ds:
        df = pd.read_json(clustered_ds)
        data_metrics = [d['value'] for d in data_metrics_options]
        scaled_data = scale_data(df, data_metrics)
        melted = pd.melt(scaled_data, id_vars=['Method', 'CLevel'], value_vars=data_metrics)

        low_critical = len(df[df['CLevel'] == "low"])
        regular_critical = len(df[df['CLevel'] == "regular"])
        high_critical = len(df[df['CLevel'] == "high"])
        dict_nr = {'Low': low_critical, 'Regular': regular_critical, 'High': high_critical}

        return cluster_result_elements(melted, dict_nr)
    else:
        return get_no_available_data_div_figure()


@app.callback(
    Output("data-listed", "children"),
    [Input("classification-data-store", "data")],
    [
        State("coverage-data-store", "data"),
        State('project-name', 'data')
    ],
)
def update_data_listed(clustered_ds, coverage_ds, pj_name):
    if clustered_ds:
        df = pd.read_json(clustered_ds)
        coverage_data = pd.read_json(coverage_ds)
        return data_listed_elements(df, coverage_data, pj_name)
    return get_empty_div()


operators = [['ge ', '>='],
             ['le ', '<='],
             ['lt ', '<'],
             ['gt ', '>'],
             ['ne ', '!='],
             ['eq ', '='],
             ['contains '],
             ['datestartswith ']]


def split_filter_part(filter_part):
    for operator_type in operators:
        for operator in operator_type:
            if operator in filter_part:
                name_part, value_part = filter_part.split(operator, 1)
                name = name_part[name_part.find('{') + 1: name_part.rfind('}')]

                value_part = value_part.strip()
                v0 = value_part[0]
                if (v0 == value_part[-1]) and (v0 in ("'", '"', '`')):
                    value = value_part[1: -1].replace('\\' + v0, v0)
                else:
                    try:
                        value = float(value_part)
                    except ValueError:
                        value = value_part

                # word operators need spaces after them in the filter string,
                # but we don't want these later
                return name, operator_type[0].strip(), value

    return [None] * 3


@app.callback(
    Output('info-table', "data"),
    [
        Input('info-table', "page_current"),
        Input('info-table', "page_size"),
        Input('info-table', 'sort_by'),
        Input('info-table', "filter_query")
    ],
    [
        State("classification-data-store", "data"),
        State("coverage-data-store", "data"),
    ])
def update_table(page_current, page_size, sort_by, filter, clustered_ds, coverage_ds):
    filtering_expressions = filter.split(' && ')
    clustered_data = pd.read_json(clustered_ds)
    coverage_data = pd.read_json(coverage_ds)
    dff = pd.merge(clustered_data, coverage_data, on='Method', how='left')
    dff['UncoveragePercentage'] = dff.apply(lambda row: get_uncoverage_percentage(row), axis=1)

    for filter_part in filtering_expressions:
        col_name, operator, filter_value = split_filter_part(filter_part)

        if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
            # these operators match pandas series operator method names
            dff = dff.loc[getattr(dff[col_name], operator)(filter_value)]
        elif operator == 'contains':
            dff = dff.loc[dff[col_name].str.contains(filter_value)]
        elif operator == 'datestartswith':
            # this is a simplification of the front-end filtering logic,
            # only works with complete fields in standard format
            dff = dff.loc[dff[col_name].str.startswith(filter_value)]

    if len(sort_by):
        dff = dff.sort_values(
            [col['column_id'] for col in sort_by],
            ascending=[
                col['direction'] == 'asc'
                for col in sort_by
            ],
            inplace=False
        )

    page = page_current
    size = page_size

    return dff.iloc[page * size: (page + 1) * size].to_dict('records')


if __name__ == "__main__":
    # debug = False if os.environ["DASH_DEBUG_MODE"] == "False" else True
    # app.run_server(host="0.0.0.0", port=8051, debug=debug, dev_tools_hot_reload=False, use_reloader=False)
    app.run_server(
        debug=True, port=8051, dev_tools_hot_reload=False, use_reloader=False
    )
