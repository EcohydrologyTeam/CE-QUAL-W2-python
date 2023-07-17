"""
CE-QUAL-W2 Module

Author: Todd E. Steissberg, PhD, PE
Organization: Ecohydrology Team, Water Quality and Contaminant Modeling Branch,
    Environmental Laboratory, Engineer Research and Development Center (ERDC),
    U.S. Army Corps of Engineers
Version: 1.0
Date: June 10, 2023

The CE-QUAL-W2 module is a numerical modeling framework developed by the Ecohydrology Team at ERDC. CE-QUAL-W2 is
designed for simulating water quality and hydrodynamics in natural and engineered water systems. CE-QUAL-W2 is a
two-dimensional, vertically-averaged, hydrodynamic and water quality model. It simulates water movement, temperature,
and concentrations of various chemical constituents in lakes, reservoirs, estuaries, and rivers. The model takes into
account physical processes such as advection, dispersion, diffusion, settling, and resuspension, as well as chemical
reactions and biological processes.

The CE-QUAL-W2 model is widely used by researchers, engineers, and environmental scientists for studying and managing
water resources. It has been applied to various water bodies worldwide to assess water quality, evaluate the impacts
of pollution sources, develop water management strategies, and support decision-making related to water resources.

This module provides a comprehensive set of functions and classes to set up and run CE-QUAL-W2 simulations, define the
system geometry, specify boundary conditions, initialize the model, read and write CE-QUAL-W2 input and output files,
and visualize and analyze the simulation results. It offers flexibility in configuring the model parameters and allows
for customization to suit specific modeling needs.

Usage:
    import cequalw2

    # Create a CE-QUAL-W2 model instance
    model = cequalw2.CEQualW2Model()

    # Set up the model configuration
    model.set_geometry(...)
    model.set_boundary_conditions(...)
    model.set_initial_conditions(...)
    model.set_model_parameters(...)

    # Run the simulation
    model.run_simulation(...)

    # Analyze the simulation results
    model.plot_results(...)
    model.export_results(...)

Please refer to the CE-QUAL-W2 model documentation and publications for detailed information on model theory,
input data requirements, and model applications.
"""

from .w2_datetime import *
from .w2_io import *
from .w2_reports import *
from .w2_visualization import *