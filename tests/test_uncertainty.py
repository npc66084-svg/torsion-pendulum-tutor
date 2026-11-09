"""不确定度、标定、回归和出图的核心单元测试；不启动界面、不调用模型。"""
import math

import numpy as np
import pytest

import charts
import experiment
import stages
import torsion
import uncertainty


def test_u_a_and_u_b():
    values = [7.690, 7.700, 7.695]
    assert uncertainty.u_a(values) == pytest.approx(np.std(values, ddof=1) / math.sqrt(3))
    assert uncertainty.u_b(0.001) == pytest.approx(0.001 / math.sqrt(3))
    assert uncertainty.combine(3.0, 4.0) == pytest.approx(5.0)
    assert uncertainty.u_a([7.695]) == 0.0
    assert uncertainty.u_b(None) == 0.0


def test_readings_summary_matches_manual():
    summary = uncertainty.readings_summary([7.690, 7.700, 7.695], 0.001, "总时间")
    assert summary["count"] == 3
    assert summary["mean"] == pytest.approx(7.695)
    assert summary["u"] == pytest.approx(
        math.hypot(uncertainty.u_a([7.690, 7.700, 7.695]), uncertainty.u_b(0.001)))


def test_times_summary_scales_by_n():
    summary = uncertainty.times_summary([7.690, 7.700], 10, 0.001)
    assert summary["period"] == pytest.approx(0.7695)
    assert summary["period_u"] == pytest.approx(summary["total_u"] / 10)


def test_calibration_recovers_true_constants():
    params = experiment.virtual_param()
    empty = torsion.measure_period("carrier", 10, 0)["summary"]["total_time_s"]
    loaded = torsion.measure_period("carrier_cylinder", 10, 0)["summary"]["total_time_s"]
    result = uncertainty.calibration(params, [empty], [loaded], 10)
    assert result["K"]["value"] == pytest.approx(torsion.K_TRUE, rel=5e-3)
    assert result["I0"]["value"] == pytest.approx(torsion.CARRIER_I, rel=5e-3)
    assert result["i1"]["value"] == pytest.approx(7.75e-4, rel=5e-3)


def test_inertia_from_period_round_trip():
    result = uncertainty.inertia_from_period(0.032, 0.0, 1.2, 0.0)
    assert result["value"] == pytest.approx(0.032 * 1.2 ** 2 / (4 * math.pi ** 2))


def test_regression_exact_line():
    xs = [0.0025, 0.01, 0.0225, 0.04, 0.0625]
    ys = [2 * x + 1 for x in xs]
    fit = uncertainty.regression(xs, ys)
    assert fit["slope"] == pytest.approx(2.0)
    assert fit["intercept"] == pytest.approx(1.0)
    assert fit["r2"] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        uncertainty.regression([1.0, 2.0], [1.0, 2.0])


def test_percent_error_and_format_result():
    error = uncertainty.percent_error(1.1, 0.1, 1.0, 0.05)
    assert error["value"] == pytest.approx(0.1)
    text, _ = uncertainty.format_result(0.7695, 0.0007, "s")
    assert text == "0.7695 ± 0.0007 s"


def test_stage_calibration_estimate_uses_groups():
    state = experiment.blank_state()
    experiment.set_mode(state, "virtual")
    params = experiment.active_param(state, "virtual")
    for _ in range(3):
        empty = torsion.measure_period("carrier", 10, 0)["summary"]["total_time_s"]
        loaded = torsion.measure_period("carrier_cylinder", 10, 0)["summary"]["total_time_s"]
        stages.add_calibration_group(state, "virtual", 10, str(empty), str(loaded))
    estimate = stages.calibration_estimate(state, "virtual", params)
    assert estimate["groups"] == 3
    assert estimate["K"]["value"] == pytest.approx(torsion.K_TRUE, rel=5e-3)


def test_group_tables_show_period_and_param_version():
    state = experiment.blank_state()
    experiment.set_mode(state, "virtual")
    empty = torsion.measure_period("carrier", 10, 0)["summary"]["total_time_s"]
    loaded = torsion.measure_period("carrier_cylinder", 10, 0)["summary"]["total_time_s"]
    stages.add_calibration_group(state, "virtual", 10, str(empty), str(loaded))
    table = stages.groups_md(state, "virtual", "calibrate")
    assert "T₀ / s" in table and "T₁ / s" in table
    assert "注意" not in table
    stages.add_measurement_group(state, "virtual", "shapes", "tube", 10, "12.443, 12.447")
    shape_table = stages.groups_md(state, "virtual", "shapes")
    assert "T / s" in shape_table and "12.445" in shape_table


def test_parameter_version_traceability():
    state = experiment.blank_state()
    experiment.set_mode(state, "real")
    form = experiment.blank_form()
    form.update(p_cylinder_mass="620.0", p_cylinder_diameter="99.98, 100.02, 100.00")
    param = experiment.form_to_param(form)
    experiment.add_version(state, "real", param)
    group = stages.add_calibration_group(state, "real", 10, "7.695", "12.443")
    assert group["param_label"] == "v1"
    assert "注意" not in stages.groups_md(state, "real", "calibrate")
    experiment.add_version(state, "real", param)
    assert "统一按" in stages.param_change_note(state, "real")
    assert "注意" in stages.groups_md(state, "real", "calibrate")


def test_charts_draw_errorbars_and_residuals():
    assert charts.shapes_figure([]) is None
    figure = charts.shapes_figure([("金属圆筒", 1.4e-3, 1.4e-3, 0.1)],
                                  {"金属圆筒": (6e-7, 3e-7)})
    assert figure is not None and len(figure.axes) == 1
    assert charts.parallel_figure([], []) is None
    points = [(0.0025, 0.0056), (0.01, 0.0084), (0.0225, 0.0144)]
    parallel = charts.parallel_figure(points, [], errors=([1e-4, 1e-4, 1e-4], []))
    assert parallel is not None and len(parallel.axes) == 4
