# Global year - update once per year
YEAR = 2025


# Periods to download per platform
# Format: "platform_name": (start_period, end_period)
# Periods are inclusive: (4, 6) downloads PERIOD_4, PERIOD_5, PERIOD_6
PERIODS_CONFIG = {
    # Bi-monthly scanners (6 periods per year)
    "arnona": (4, 6),
    "meitav": (4, 6),
    # Monthly scanners (12 periods per year)
    "partner": (7, 11),
}


def get_periods_to_download(platform: str) -> list[str]:
    if platform not in PERIODS_CONFIG:
        raise KeyError(
            f"Platform '{platform}' not found in PERIODS_CONFIG. "
            f"Available platforms: {list(PERIODS_CONFIG.keys())}"
        )

    start_period, end_period = PERIODS_CONFIG[platform]
    return [f"PERIOD_{i}" for i in range(start_period, end_period + 1)]
