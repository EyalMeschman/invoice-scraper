# Global year - update once per year
YEAR = 2025


# Periods are inclusive: (4, 6) downloads PERIOD_4, PERIOD_5, PERIOD_6
PERIODS_CONFIG = {
    ##### Bi-monthly scanners (6 periods per year) #####
    # Current period is downloadable only at the 1st month of the current bimonthly period (e.g., Jan-Feb at Jan 1st)
    "arnona": (4, 6),
    # A period is downloadable only at the 1st day of the next bimonthly period (e.g., 15th Jan- 15th Mar at Apr 1st)
    # Period 1 = 15th of Nov - 15th of Jan ; Period 6 = 15th of Sep - 15th of Nov
    "meitav": (4, 6),
    ##### Monthly scanners (12 periods per year) #####
    # Can only download the last 6 months
    # Current month is downloadable only at the 14th of the current month (e.g., October at Oct 14th)
    "partner": (4, 11),
    # Current month is downloadable only at the 2nd of the next month (e.g., October at Nov 2nd)
    "google_workspace": (7, 11),
}


def get_periods_to_download(platform: str) -> list[str]:
    if platform not in PERIODS_CONFIG:
        raise KeyError(
            f"Platform '{platform}' not found in PERIODS_CONFIG. "
            f"Available platforms: {list(PERIODS_CONFIG.keys())}"
        )

    start_period, end_period = PERIODS_CONFIG[platform]
    return [f"PERIOD_{i}" for i in range(start_period, end_period + 1)]
