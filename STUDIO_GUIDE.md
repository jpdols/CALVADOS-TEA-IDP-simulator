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
python -u -m calvados_library_builder.calvados_entrypoint ABSOLUTE_RUN_DIR/run.py --path ABSOLUTE_RUN_DIR --config config.yaml --components components.yaml
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

## Windows: checkpoint error WinError 5/183

The original OpenMM 8.4 checkpoint saver renames a temporary file over an
existing `restart.chk`. Some Windows drives reject this replacement. This
does not imply an MD integration failure. The new entrypoint applies a
**Windows-only** compatibility fix *inside the simulation child process*:
it calls OpenMM's supported `saveCheckpoint(file_object)` API instead of
`saveCheckpoint(filename)`, bypassing rename operations. Before overwriting
an existing checkpoint it saves a full copy to `restart.chk.previous`.

The previous checkpoint is preserved for recovery, but file-object writing
is not atomic; do not interrupt the process during checkpoint writes.
No packages need reinstalling, and the CALVADOS simulation equations and
integrator are untouched. The helper does nothing on Linux.

**Do not restart a failed folder blindly.** Existing trajectories and
checkpoints may represent different integration steps. Leave older folders
alone and use a new experiment name for the next short smoke test.

## Bracketed mono-motif editor and autosaved motifs

The Design page always displays a draggable row of colored motif balls.
**Consecutive identical motifs appear inside one bracket with a ×N label.**
Adjacent identical runs merge automatically; changing order can therefore
merge two blocks without changing the underlying sequence. Drag a block
between others or drop it on the left/right half of another block.

Hover a block (or focus it using the keyboard) to reveal a floating toolbar:

- **+1** adds one copy of that motif.
- **−1** removes one copy; it removes the block at 1.
- **Split** divides a run into two separately draggable parts.
- **×** deletes the entire motif run.
- The count field edits any run's repeat count directly.

A split creates an *explicit temporary boundary* between two adjacent
identical motif runs so one part can be dragged away. After reordering,
adjacent identical runs merge again. All actions update the exact sequence
used for FASTA export and CALVADOS preparation.

### Standard palette

| Motif | Full amino-acid sequence | Color |
| --- | --- | --- |
| VPGVG | VPGVG | `#4C78A8` |
| IPAVG | IPAVG | `#F2CF5B` |
| VPGIG | VPGIG | `#54A24B` |
| VPGKG | VPGKG | `#C13CFF` |
| VPGEG | VPGEG | `#F28E2B` |
| VPAVG | VPAVG | `#FF66B3` |
| RGD block | AVTGRGDSPASS | `#7944AC` |

The RGD purple is matched to the user-supplied color reference.
The existing six colors remain unchanged.

### Persistence between app sessions

New motifs (name, sequence, HEX color) are saved to
`runs/_custom_motifs.json`; they are automatically loaded on app restart.
Built-in motif entries cannot be replaced by custom motifs. The **current
sequence name, ordered blocks, counts and explicit splits** are also saved,
to `runs/_current_elp_draft.json`. The last valid draft is restored
automatically after the application restarts.

Both files live under the user's existing `runs` folder. Keep them in
backups if custom motifs and the last draft should be preserved.

Pasting a FASTA still detects known motifs and creates grey fragments for
unmatched amino acids. The optional two-motif library generator is unchanged.

The editor uses Streamlit bidirectional custom components, without adding
npm, Node.js or Python runtime dependencies. GitHub CI uses Node.js only
to syntax-check the embedded JavaScript. The actual hover/drag experience
must be verified in a browser.

## Bulk-import libraries, simulation help and PDF comparison

The Design tab keeps the one-ball-per-block editor for single ELPs. To
prepare an existing library without building it manually, use **Import a
sequence library**. Upload a multi-record FASTA file, or a CSV with columns
`name,sequence`. Pasting multi-FASTA is also supported. The old experimental
two-motif composition generator has been removed from the main app. The
importer validates amino-acid codes and duplicate names, then queues one
single-chain simulation per imported sequence under the selected experiment.

Example multi-FASTA:

```fasta
>ELP_01
VPGVGVPGVGVPGVG
>ELP_02
VPGVGAVTGRGDSPASSVPGVG
```

Each simulation parameter now has a hover-help icon explaining its unit,
purpose and impact: temperature, compute backend, saved frames, steps per
frame, box size, pH, ionic strength and initial random seed.

### Typeface

The Streamlit app and the motif canvas request **Suisse Intl / Suisse** as
their preferred system font. Due to licensing, **no font files are
distributed**. If neither font is installed on your laptop, the UI falls
back to Helvetica Neue or Arial. For consistent visuals on another computer,
install Suisse using your own valid font licence.

### Analysis PDF

After analyzing at least one trajectory, open **Analyze → Compare analyzed
sequences → Generate comparison PDF**. The downloadable landscape report has
one colored ball (with `×N` repeat count) per contiguous motif run, a table
of results next to each sequence, and comparative vector charts for:

- fraction collapsed;
- mean Rg (nm);
- mean compact Rg (nm);
- collapse rate (ns⁻¹);
- escape rate (ns⁻¹).

Figures use the saved sequence and thesis motif colors. Existing
`analysis/summary.csv` files are the source of numerical values; not-yet-
analyzed sequences cannot be included. Rates based on short, non-equilibrated
runs should not be treated as reliable equilibrium properties.

Credits: **Created by Joep Dols · Nikolina Šoštarić Lab · TU Delft**.


## Triplicate simulations

Under **Design → Prepare simulations**, enable **Run in triplicate**.
For each sequence the app prepares three independently seeded runs:

```text
runs/
  experiment_name/
    batch_state.json
    ELP_A/
      ELP_A__rep01/
        config.yaml
        components.yaml
        run.py
        replicate_info.json
        input/
      ELP_A__rep02/
        ...
      ELP_A__rep03/
        ...
```

The sequence itself is unchanged across replicates. Each run has a separate
random seed (starting seed + 0, +1, +2), generated system, trajectory,
checkpoint, logs and analysis directory. All three are queued sequentially
by the existing batch runner. Preflight rejects existing run folders, so
nothing is overwritten. If the selected library contains ten sequences,
triplicate preparation queues 30 independent simulations.

The previous single-replicate folder layout remains unchanged. Each
replicate stores its original sequence name, replicate number and seed in
`replicate_info.json`, allowing the Analyze tab to group statistics by
sequence even though every simulation has a unique run name.

## Excluding equilibration frames

In **Analyze**, optionally enable **Discard first 10% of trajectory frames**.
For a 1,000-frame DCD, this excludes the first 100 original frames.
The number removed is `floor(0.10 * original_DCD_frame_count)`. This is
applied **before** analysis stride, Rg statistics, collapsed fractions,
transition counts, dwell times and kinetics. The saved time trace retains
absolute frame numbers and original simulation times; a shorter selected
trajectory is not relabeled as starting at zero.

The choice is recorded in `analysis/summary.csv` as `discard_fraction`,
`discarded_frames` and `total_trajectory_frames`, and in
`analysis/methods.json`. When repeating an analysis, the same output files
are regenerated with the newly selected discard setting. The source DCD is
never modified.

The Analyze comparison now includes an additional per-sequence table with
**mean and between-replicate standard deviation** for the five central
metrics whenever more than one independently analyzed replicate exists.
It does not concatenate frames or pool transition counts. For meaningful
comparisons, apply the same equilibration policy and adequate trajectory
duration to all replicates.
