# %% [markdown]
'''
# PyDPF Example
In this 'VS Code 'Python Code file' a built-in example is selected, its model description is printed and results are selected and plotted.  
Selection is done by assigning variables
'''

# %% [markdown]
'''
Print model description, note available results and timesteps  
'''

# %%
import numpy as np
from ansys.dpf import post
from ansys.dpf import core as dpf
from ansys.dpf.core import examples

rst = examples.simple_bar
tf_idx = 0
dof_idx = 2

model = dpf.Model(rst)
tfs = model.metadata.time_freq_support.time_frequencies
mesh = model.metadata.meshed_region
ugrid = mesh.grid
print(model)


# %%
# 1st result in results set
res_idx = 0
# last available 'time' index
tf_idx = len(tfs) - 1
# first component (if more than 1)
comp_idx = 0

mesh = model.metadata.meshed_region
result_info = model.metadata.result_info
res = result_info.available_results[res_idx]
if res.n_components == 1:
    res_op = dpf.Operator(res.operator_name)
    res_op.inputs.data_sources.connect(model.metadata.data_sources)
    res_op.inputs.time_scoping([tf_idx + 1])
    fields = res_op.outputs.fields_container()
    f0 = fields[0] 
elif res.n_components > 1:
    res_op = dpf.Operator(res.operator_name)
    res_op.inputs.data_sources.connect(model.metadata.data_sources)
    res_op.inputs.time_scoping([tf_idx + 1])
    comp_sel = dpf.operators.logic.component_selector_fc()
    comp_sel.inputs.connect(res_op.outputs)
    comp_sel.inputs.component_number.connect(comp_idx)
    fields = comp_sel.outputs.fields_container()
    f0 = fields[0]
mesh.plot(f0)

# %%
def get_grid_with_field(meshed_region, field):
    name = '_'.join(field.name.split("_")[:-1])
    location = field.location
    if location == dpf.locations.nodal:
        mesh_location = meshed_region.nodes
    elif location == dpf.locations.elemental:
        mesh_location = meshed_region.elements
    else:
        raise ValueError(
            "Only elemental or nodal location are supported for plotting."
        )
    overall_data = np.full(len(mesh_location), np.nan)
    ind, mask = mesh_location.map_scoping(field.scoping)
    overall_data[ind] = field.data[mask]

    grid = meshed_region.grid
    if location == dpf.locations.nodal:
        grid.point_data[name] = overall_data
    elif location == dpf.locations.elemental:
        grid.cell_data[name] = overall_data
    return grid


grid = get_grid_with_field(mesh, f0)
name = '_'.join(f0.name.split("_")[:-1])
grid.plot(scalars=name)


# %%
