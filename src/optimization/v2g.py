from src.optimization.model import solve_optimized_day


def solve_v2g_day(vehicles, carbon_intensity, config, v2g_eligible=None):
    return solve_optimized_day(
        vehicles, carbon_intensity, config, strategy="v2g", v2g_eligible=v2g_eligible
    )
