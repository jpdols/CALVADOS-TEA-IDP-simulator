# ELP Studio: local design → simulation → analysis

The default `app.py` is a simplified, three-stage Streamlit app. The
previous advanced motif editor is preserved as `legacy_app.py`.

## Start

From the cloned repository and activated Conda environment:

```bat
git pull origin main
python -m pytest -q
python -m streamlit run app.py
```

Create a repeated-motif ELP, paste a custom one-letter sequence, or generate
a composition-matched two-motif library. In **Design**, select a unique
experiment name and prepare. In **Simulate**, select that experiment and click
**Run queued simulations**. The app runs one queue item at a time, updating
the progress area every five seconds. It does not delete older experiments.

## Diagnose an old or new prepared run

Example, using a path relative to the repository:

```bat
python -m calvados_library_builder.preflight "runs\test1\test_sequence"
```

The preflight prints the exact generated `run.py` invocation, platform,
step count and missing inputs. The child wrapper executes the generated script
as:

```text
python ABSOLUTE_RUN_DIR/run.py --path ABSOLUTE_RUN_DIR --config config.yaml --components components.yaml
```

If a run stays at 0 frames, inspect these files inside its run directory:

- `run.log`: CALVADOS's stdout and exact launch command.
- `run_error.log`: errors and Python tracebacks.
- `runner_exit_code.txt`: subprocess exit code if a subprocess finished.
- `runner_state.json`: saved PID, times, detected frames and state.
- `config.yaml` and `components.yaml`: requested CALVADOS settings.

A quiet Streamlit terminal does **not** prove the simulation is idle: the
simulation runs in a child process whose output is redirected to those logs.
OpenMM's detected backends, not a guessed GPU, determine which platforms the
new UI offers.

If you want to test without Streamlit, run the command printed by preflight
*only when the existing worker is not running*. Never launch a second copy
in the same run folder while the first one is active.

## Rg analysis

In **Analyze**, select a run with its PDB and DCD and click
**Analyze selected trajectory**. Results are saved to
`runs/<experiment>/<sequence>/analysis/`:

- `all_rg_values.csv` with per-frame Rg, time and collapsed state
- `summary.csv` with Rg, theta, collapsed population and two-state kinetics
- `rg_time.png` and `rg_distribution.png`
- `methods.json` recording definitions and assumptions

Standalone command:

```bat
python -m calvados_library_builder.analysis "runs\first_test\test_vpgvg" --stride 1
```

Scientific definitions match the selected thesis convention:

- Mass-weighted Rg, coordinates Å → nm.
- Default `Rg_theta(N) = sqrt(2 * 0.40 nm * 0.38 nm * (N - 1) / 6)`.\n  Thus `Rg_theta(420) = 4.608 nm` (419 backbone bonds).
  This is the thesis's 420-residue calibration, **not** a universal polymer
  ideal-chain value. The reference threshold is editable in Analyze.
- Collapsed when `Rg < Rg_theta` (no hysteresis).
- `k_collapse = N(expanded→collapsed) / total expanded time` (/ns).
- `k_escape = N(collapsed→expanded) / total collapsed time` (/ns).
- Mean dwell times exclude the first and last trajectory segments because
  they are censored.
- The 0.01 ps integration timestep comes from the pinned CALVADOS version;
  frame spacing is `wfreq * 0.01 ps * analysis_stride`.
- The current Rg analyzer supports only one chain per run and requires a
  contiguous coordinate representation. Periodic wrapping of a chain can bias
  Rg. Check the PDB/DCD before interpreting results.

A 50-frame / 50,000-step run is a **pipeline smoke test**, not a converged
sample from which to infer equilibrium or reliable rate constants. For
publication-grade comparisons, use independently seeded replicates,
equilibration removal, uncertainty estimates and sufficient transitions.

## Existing power-user interface

```bat
python -m streamlit run legacy_app.py
```

The legacy app remains available but is not the recommended starting point.
