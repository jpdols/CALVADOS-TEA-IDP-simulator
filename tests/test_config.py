import pytest
from calvados_library_builder.config import SimulationConfig, validate_config


def test_default_platform_cpu():
    assert SimulationConfig(name='example', sequence='VPGVG').platform == 'CPU'


def test_invalid_platform_fails_before_missing_parameters(tmp_path):
    c = SimulationConfig(name='example', sequence='VPGVG', platform='OpenCL', residue_file=tmp_path / 'missing.csv')
    with pytest.raises(ValueError, match='CPU'):
        validate_config(c)
