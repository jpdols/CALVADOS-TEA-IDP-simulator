# Temperature-dependent residue parameters

This folder contains the 11 user-supplied `residues_gamma_6p0_<temperature>K_argdefault_minus.csv` parameter tables for 300, 310, 320, 330, 340, 350, 360, 370, 380, 390 and 400 K.

Each file has 20 amino acid entries and columns `one,three,MW,lambdas,sigmas,q,bondlength`. Numeric values are preserved as supplied; source Windows CRLF line endings were normalized to LF on upload.

`calvados_library_builder.config.SimulationConfig.resolve_residue_file()` uses the correct filename for each supported temperature. An unsupported temperature needs an explicitly provided custom file. These tables are custom research inputs; check their scientific provenance and licensing before wider redistribution.
