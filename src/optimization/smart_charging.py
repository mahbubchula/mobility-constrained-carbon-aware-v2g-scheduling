from src.optimization.model import solve_optimized_day


def solve_smart_charging_day(vehicles, carbon_intensity, config):
    return solve_optimized_day(vehicles, carbon_intensity, config, strategy="smart")

