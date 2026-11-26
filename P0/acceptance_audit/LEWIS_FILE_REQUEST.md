# Pinned files to request

These paths are relative to `Octopus-main/`. The upstream suite on 25 Nov 2026 was 325 passed, 1 skipped, and 23 failed. Every failure is a missing file below. The one skip is `tests/test_capture_contract.py`, which requires torch. No source file was missing.

## Files

1. `empirical/v2v4real/sequence_counts.csv`
   Archived nine-row reference used by `--check` and by `load_scenes`. The regenerated copy in `Negin_validation/P0/v2v4real_all/sequence_counts.csv` matches the published totals, but the tests open this path inside the repository. `test_source_integrity_fails_closed` also expects the 0007 row to begin `0007,221,442,221`.

2. `empirical/v2v4real/packed_outcomes.json`
   Source-verified packed outcomes. `scripts/unpack_verified_v2v4real.py` must expand it to 442 events, and the documented FNV-1a-32 checksum for that sequence is `0e57779e`. The unpacker also reads file 1.

3. `examples/v2v4real_real_seq0007/trace.jsonl`
   The 221-frame, 442-event replay. The six scenario JSON files in that directory are already present and point at this trace. The same path is used by `examples/f0/v2v4real_f0.json`, `examples/energy/v2v4real_0007_energy.json`, `examples/energy/v2v4real_0007_legacy_per_roi.json`, and `examples/coordination/v2v4real_candidate_inventory.json`.

4. `samples/three_vehicle_real_published/cooperscene_published_v2v_v2v2.csv`
   Published CooperScene table read by `scripts/plot_cooperscene_published.py`. The test expects 12 rows, models V2VNet, V2X-ViT, V2VAM, CoBEVT, ERMVP, and CoSDH, and vehicle counts 2 and 3.

5. `samples/three_vehicle_real_published/UPSTREAM_BENCHMARK_PROVENANCE.json`
   Read immediately after file 4. The test expects `source_readme_git_blob_sha` equal to `2de04bda334c5baa2bead8744d90ee0417579e7c`.

## Which of the 23 tests each file blocks

`sequence_counts.csv` is the first missing file for:

- `tests/test_cvc_figure_study.py::test_nine_scene_source_totals_and_matched_rates`
- `tests/test_cvc_figure_study.py::test_source_integrity_fails_closed`
- `tests/test_cvc_figure_study.py::test_bootstrap_is_paired_scene_level_and_repeatable`
- `tests/test_cvc_figure_study.py::test_generate_eight_vector_and_raster_figures_from_clean_inputs`
- `tests/test_v2v4real_public_exploration.py::test_aggregate_source_counts_and_reversal`

`trace.jsonl` is the first missing file for:

- `tests/test_cvc_figure_study.py::test_paired_events_keep_frame_id_and_distinct_roi_answers`
- `tests/test_cvc_figure_study.py::test_frame_level_executor_matches_energy_cost_anchors`
- `tests/test_cvc_figure_study.py::test_energy_assumption_envelopes_do_not_claim_measured_precision`
- `tests/test_cvc_figure_study.py::test_cost_forecasts_are_visibility_dependent_not_executions`
- `tests/test_e1_multiobjective_figures.py::test_bundled_recorded_frame_pairs_are_verified`
- `tests/test_e1_multiobjective_figures.py::test_exact_reweighting_matches_actual_energy_simulator`
- `tests/test_e1_multiobjective_figures.py::test_corrected_frame_level_energy_and_error_endpoints`
- `tests/test_e1_multiobjective_figures.py::test_clean_plot_generation_and_output_counts`
- `tests/test_energy_e0_e1.py::test_energy_replay_v2v4real_full_fusion_source_verified`
- `tests/test_f0_execution_integration.py::test_actual_v2v4real_frame_level_replay_stays_consistent`
- `tests/test_f0_reproducible_study.py::test_actual_v07_local_export_matches_online_f0_per_roi`
- `tests/test_f0_reproducible_study.py::test_synthetic_and_real_study_outputs_have_nonmisleading_provenance`
- `tests/test_f0_reproducible_study.py::test_plots_render_without_placeholder_metadata`
- `tests/test_frame_cache_study.py::test_load_sweep_fixed_outcome_endpoints_and_resource_reconciliation`
- `tests/test_frame_cache_study.py::test_study_cli_writes_traceable_png_and_csv`
- `tests/test_p0_execution_graph.py::test_real_p0_v2v4real_example_end_to_end`

`packed_outcomes.json` is the first missing file for `tests/test_v2v4real_public_exploration.py::test_packed_genuine_source_sequence_and_end_to_end_replay`. That test then reads `sequence_counts.csv`.

The CooperScene CSV is the first missing file for `tests/test_three_vehicle_real_readiness.py::test_published_cooperscene_three_vehicle_numbers_match_pinned_official_table`. That test then reads the provenance JSON.

The figure files under `empirical/v2v4real/figures/` are described in `docs/EMPIRICAL_V2V4REAL_RESULTS.md`. None of these 23 tests opens them.
