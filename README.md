# MAE 459 suborbital rocket analysis and CFD package

Mission: 70 kg passenger-equivalent **test payload**, minimum 150 km AMSL.
This is a classroom preliminary ascent design. It is not a human-flight design.

The computed baseline uses two LOX/methane stages and reaches 155 km under
the stated assumptions. The report documents important uncertainties and
unresolved hardware integration. No CFD has been run; analytical distributions
must not be presented as CFD evidence.

## Contents

- `analyze_project.py`: thermochemistry, constant-property nozzle, stage trade,
  and ascent integration.
- `details.py`: contour, cooling, tanks, sensitivities, independent checks, plots.
- `finalize_data.py`: additional checks, feed estimates, STEP fluid surfaces,
  and mission/feed figures.
- `compare_cfd.py`: quantitative comparison of actual Fluent data entered in
  the blank table. It does not solve fluid flow.
- `data/analysis.json`: full-precision calculated values.
- `data/trajectory_*stage.csv`: trajectory histories for all architectures.
- `data/nozzle_stage*_profile.csv`: one-dimensional analytical nozzle profiles.
- `data/cooling_stage*.csv`: correlation-based thermal predictions.
- `data/cfd_results_to_fill.csv`: blank actual-CFD data entry table.
- `geometry/stage*_fluid_surface_mm.step`: 2D axisymmetric fluid faces.
- `figures/`: calculated charts and schematic figures, not CFD contours.
- `report.md`: editable text and equations used for the AIAA report.

## Reproduce calculations

Python 3.12 was used. Install dependencies, then run in order:

```bash
python -m pip install -r requirements.txt
python analyze_project.py
python details.py
python finalize_data.py
```

Gmsh is required only for STEP export in the third script. On Linux, its Python
module may need the system OpenGL libraries supplied with Gmsh. The existing
STEP files can be used without regenerating them. All paths in the scripts are
relative to the script directory. Numerical recalculation may take several minutes.

`analyze_project.py` overwrites the analytical JSON; run all scripts in sequence
to regenerate the complete result. No input file from Fluent is read by those
three scripts. Existing CFD data-entry tables are preserved by finalize_data;
a fresh blank copy is written separately if a table already exists.

## Run Fluent

Use the detailed Appendix B in the report. Important checks:

- STEP geometry coordinates are millimeters; profile CSV coordinates are meters.
- Stage 1 throat radius: 0.08165327 m; stage 2: 0.04055378 m.
- Use 2D **axisymmetric**, not planar, with x axial and y radial.
- Baseline: inviscid, energy on, ideal gas, MW 20.371753 kg/kmol,
  cp 2357.799965 J/(kg K), operating pressure zero.
- Inlet total pressure 1 MPa; total temperature 3327.164842 K.
- Stage 1 ambient 101325 Pa; stage 2 ignition ambient 16799.69543 Pa.
- Run coarse, medium, and fine grids for BOTH nozzles.
- Save actual case/data, mesh, residuals, monitors, six required plots, exit
  reports, and independent momentum/pressure thrust integrals.

After filling all quantities in the CSV from actual CFD reports:

```bash
python compare_cfd.py data/cfd_results_to_fill.csv
```

Blank rows remain pending. The postprocessor calculates comparisons only from
complete rows. Preserve original raw Fluent exports and update the report's
pending CFD section, abstract, and conclusions after review.

## Modeling cautions that affect the result

The 0.45 m body diameter and Mach-dependent drag envelope are assumed.
High-pressure fuel tanks and helium storage imply a long vehicle; final
packaging, structural mass, stability and aerodynamics are unresolved.
The 0.95 thrust factor and stage mass law are assumptions. The thermal model
is a first-order correlation screen with loose gas/coolant coupling, not
conjugate CFD. The report includes perturbations showing that the nominal
5 km altitude margin is not robust to plausible changes.

In code, `dry` is **burnout inert mass**, including 2% trapped propellant.
Physical dry mass subtracts that residual; loaded propellant includes it.
Do not add the residual to both sides of the mass budget.

Author: Jaeyoon Kim. Prepared with AI assistance; review and understand all
assumptions and calculations before submission and the verification exam.

## Rebuild the editable report (optional)

The supplied DOCX is ready to edit in Word. `build_report.py` is also included
for regenerating it from the computed data. Install Pandoc 3.1.11.1 or a
compatible release separately, then run `python build_report.py`. The script
writes the DOCX into an `output` directory beside the package directory and
rewrites `report.md`. The core numerical analysis does not require Pandoc.
Manual changes in Word are not imported back into the generator.
