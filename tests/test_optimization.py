from src.common import load_config
from src.validation.synthetic_model_tests import flat_carbon_test, zero_flexibility_test


def test_flat_carbon():
    assert flat_carbon_test(load_config())["pass"]


def test_zero_flexibility():
    assert zero_flexibility_test(load_config())["pass"]

