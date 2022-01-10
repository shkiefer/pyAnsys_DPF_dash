import numpy as np
import plotly.graph_objects as go
import dash
from dash.exceptions import PreventUpdate
from dash import dcc, Output, Input, State, html, dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc
import dash_vtk
from dash_vtk.utils import to_mesh_state

from ansys.dpf import core as dpf
from ansys.dpf.core import examples


APP_ID = 'pyAnsys'
EXAMPLE_MAP = {
    'simple_bar': examples.simple_bar,
    'msup_transient': examples.msup_transient,
    'static': examples.static_rst
    }

def get_grid_with_field(meshed_region, field, grid=None):
    name = '_'.join(field.name.split("_")[:-1])
    location = field.location
    if location == dpf.locations.nodal:
        mesh_location = meshed_region.nodes
    elif location == dpf.locations.elemental:
        mesh_location = meshed_region.elements
    elif location == dpf.locations.elemental_nodal:
        location = dpf.locations.elemental
        mesh_location = meshed_region.elements
        # convert elemental_nodal to elemental
        en_e_op = dpf.operators.averaging.elemental_mean()
        en_e_op.inputs.field.connect(field)
        field = en_e_op.outputs.field()
    else:
        raise ValueError(
            "Only elemental or nodal location are supported for plotting."
        )
    component_count = field.component_count
    if component_count > 1:
        overall_data = np.full((len(mesh_location), component_count), np.nan)
    else:
        overall_data = np.full(len(mesh_location), np.nan)
    ind, mask = mesh_location.map_scoping(field.scoping)
    overall_data[ind] = field.data[mask]
    
    if grid is None:
        grid = meshed_region.grid
    if location == dpf.locations.nodal:
        grid.cell_data['dummy'] = np.zeros(grid.n_cells)
        grid.point_data[name] = overall_data
    elif location == dpf.locations.elemental:
        grid.point_data['dummy'] = np.zeros(grid.n_points)
        grid.cell_data[name] = overall_data
    
    return grid


def make_colorbar(title, rng, bgnd='rgb(51, 76, 102)'):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=[None],
                   y=[None],
                   mode='markers',
                   marker=dict(
                       colorscale='plasma',
                       showscale=True,
                       cmin=rng[0],
                       cmax=rng[1],
                       colorbar=dict(
                           title_text=title, 
                           title_font_color='white', 
                           title_side='top',
                           thicknessmode="pixels", thickness=50,
                           #  lenmode="pixels", len=200,
                           yanchor="middle", y=0.5, ypad=10,
                           xanchor="left", x=0., xpad=10,
                           ticks="outside",
                           tickcolor='white',
                           tickfont={'color':'white'}
                           #  dtick=5
                       )
        ),
            hoverinfo='none'
        )
    )
    fig.update_layout(width=150, margin={'b': 0, 'l': 0, 'r': 0, 't': 0}, autosize=False, plot_bgcolor=bgnd)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H1('PyAnsys DPF in a Dash App', className="mt-3"),
    html.P('This app allows plotting results from built-in examples'),
    dbc.Row([
        dbc.Col([
            dbc.Label('Select Example', html_for="dropdown"),
            dcc.Dropdown(
                id=f'{APP_ID}_example_dropdown',
                options=[
                    {'label': 'simple_bar', 'value': 'simple_bar'},
                    {'label': 'msup_transient', 'value': 'msup_transient'}, 
                    {'label': 'static', 'value': 'static'}, 
                ],
                clearable=False,
            ),
            dbc.Label('Select Time / Frequency', html_for="dropdown"),
            dcc.Dropdown(
                id=f'{APP_ID}_example_tf_dropdown',
                options=[],
                value=None,
                clearable=False
            )
        ]),
        dbc.Col([
            dbc.Label('Select Result', html_for="dropdown"),
            dcc.Dropdown(
                id=f'{APP_ID}_example_result_dropdown',
                options=[],
                value=None,
                clearable=False
            ),
            dbc.Label('Select Component', html_for="dropdown"),
            dcc.Dropdown(
                id=f'{APP_ID}_example_comp_dropdown',
                options=[{'label': 0, 'value': 0}],
                value=0,
                clearable=False,
                disabled=True
            )
        ]),
        dbc.Col(
            dbc.Button(
                'Plot Results',
                id=f'{APP_ID}_plot_button',
                style={'height':'80%', 'width':'80%'},
                class_name='h-50'
            ),
            align="center"
        )
    ]),
    dbc.Row([
        dbc.Col([
            html.Div(
                style={"width": "100%", "height": "60vh"},
                children=[
                    dash_vtk.View(
                        id=f'{APP_ID}_vtk_view',
                        children=dash_vtk.GeometryRepresentation(
                            id=f'{APP_ID}_geom_rep_mesh',
                            children=[],
                            property={"edgeVisibility": True, "opacity": 1, "pointSize": 20, "lineWidth": 2},
                            colorMapPreset="Plasma (matplotlib)",
                        ),
                    ),
                ]
            )
        ],
            width=10
        ),
        dbc.Col([
            dcc.Graph(
                id=f'{APP_ID}_results_colorbar_graph',
                style={"width": "100%", "height": "60vh"},
            ),
 
        ],
            width=2
        )
    ],
    className="g-0"
    ),
    dbc.Card(
        dbc.CardBody(
           dash_table.DataTable(
                id=f'{APP_ID}_results_min_max_dt',
                columns=[
                    {'name': '', 'id': 'index'},
                    {'name': 'Model', 'id': 'model', 'type':'numeric', 'format': Format(precision=2, scheme=Scheme.decimal_or_exponent)},
                 ],
                data=[
                    {'index': 'Max', 'model': None},
                    {'index': 'Min', 'model': None}
                ],
                style_data_conditional=[
                    {
                        'if': {
                            'column_id': 'index',
                        },
                        'fontWeight': 'bold'
                    },
                ],
                style_header={
                    'fontWeight': 'bold'
                },
            )
        ),
        style={"width": "18rem"},
    )
])


@app.callback(
    Output(f'{APP_ID}_example_tf_dropdown', 'options'),
    Output(f'{APP_ID}_example_tf_dropdown', 'value'),
    Output(f'{APP_ID}_example_result_dropdown','options'),
    Output(f'{APP_ID}_example_result_dropdown','value'),
    Input(f'{APP_ID}_example_dropdown', 'value')
)
def dash_vtk_update_result_options(example_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    model = dpf.Model(EXAMPLE_MAP[example_name])
    result_info = model.metadata.result_info
    res_options = [{'label': res.name, 'value': res.name} for res in result_info.available_results]

    tf = model.metadata.time_freq_support.time_frequencies.data
    tf_options = [{'label': tfi, 'value': i} for i, tfi in enumerate(tf)]

    return tf_options, len(tf)-1, res_options, result_info.available_results[0].name


@app.callback(
    Output(f'{APP_ID}_example_comp_dropdown','options'),
    Output(f'{APP_ID}_example_comp_dropdown','value'),
    Output(f'{APP_ID}_example_comp_dropdown','disabled'),
    Input(f'{APP_ID}_example_result_dropdown','value'),
    State(f'{APP_ID}_example_dropdown', 'value')
)
def dash_vtk_update_comp_options(res_name, example_name):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    model = dpf.Model(EXAMPLE_MAP[example_name])
    result_info = model.metadata.result_info
    res = next((r for r in result_info.available_results if r.name == res_name), None)
    if res is not None:
        if res.n_components == 1:
            comp_options = [{'label': 0, 'value': 0}]
            comp_value = 0
            comp_disabled = True
        else:
            comp_options = [{'label': i, 'value': i} for i in range(res.n_components)]
            comp_value = 0
            comp_disabled = False
        return comp_options, comp_value, comp_disabled
    else:
        raise PreventUpdate


@app.callback(
    Output(f'{APP_ID}_geom_rep_mesh', 'children'),
    Output(f'{APP_ID}_geom_rep_mesh', 'colorDataRange'),
    Output(f'{APP_ID}_results_colorbar_graph', 'figure'),
    Output(f'{APP_ID}_results_min_max_dt', 'data'),
    Input(f'{APP_ID}_plot_button', 'n_clicks'),
    State(f'{APP_ID}_example_dropdown', 'value'),
    State(f'{APP_ID}_example_result_dropdown','value'),
    State(f'{APP_ID}_example_comp_dropdown', 'value'),
    State(f'{APP_ID}_example_tf_dropdown', 'value')
) 
def dash_vtk_update_grid(n_clicks, example_name, result_name, comp_idx, tf_idx):

    if any([v is None for v in [example_name, result_name, tf_idx]]):
        raise PreventUpdate

    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trig_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    model = dpf.Model(EXAMPLE_MAP[example_name])
    result_info = model.metadata.result_info
    res = next((r for r in result_info.available_results if r.name == result_name), None)
    mesh = model.metadata.meshed_region
    ugrid = mesh.grid
    
    if res.n_components == 1:
        res_op = dpf.Operator(res.operator_name)
        res_op.inputs.data_sources.connect(model.metadata.data_sources)
        res_op.inputs.time_scoping([tf_idx+1])
        fields = res_op.outputs.fields_container()
        f0 = fields[0]
        name = '_'.join(f0.name.split("_")[:-1])
        ugrid = get_grid_with_field(mesh, f0)
        mesh_state = to_mesh_state(ugrid.copy(), field_to_keep=name)    
    elif res.n_components > 1:
        res_op = dpf.Operator(res.operator_name)
        res_op.inputs.data_sources.connect(model.metadata.data_sources)
        res_op.inputs.time_scoping([tf_idx+1])
        comp_sel = dpf.operators.logic.component_selector_fc()
        comp_sel.inputs.connect(res_op.outputs)
        comp_sel.inputs.component_number.connect(comp_idx)
        fields = comp_sel.outputs.fields_container()
        f0 = fields[0]
        name = '_'.join(f0.name.split("_")[:-1])
        ugrid = get_grid_with_field(mesh, f0)
        mesh_state = to_mesh_state(ugrid.copy(), field_to_keep=name)
    else:
        raise PreventUpdate 
    
    view_max = ugrid[name].max()
    view_min = ugrid[name].min()
    rng = [view_min, view_max]

    name = '_'.join(f0.name.split("_")[:-1])
    fig = make_colorbar(name, rng)

    dt = [{'index':'Max', 'model':view_max}, {'index':'Min', 'model':view_min}] 

    return [dash_vtk.Mesh(state=mesh_state), rng, fig, dt]      



if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Launch PyDPF sample dash server')
    parser.add_argument('--ip', type=str, metavar='',
                        required=False,
                        help='Set the IP address of the server')

    args = parser.parse_args()

    if args.ip:
        app.run_server(debug=True, host=args.ip)
    else:
        app.run_server(debug=True)

