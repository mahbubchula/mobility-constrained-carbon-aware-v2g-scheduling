from src.common import load_config
from src.validation.synthetic_model_tests import break_even_test


def test_two_period_break_even():
    assert break_even_test(load_config())["pass"]
