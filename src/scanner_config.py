from enum import StrEnum

# Global year - update once per year
YEAR = 2025


class Platform(StrEnum):
    PARTNER = "partner"
    MEITAV = "meitav"
    ARNONA = "arnona"
    GOOGLE_WORKSPACE = "google_workspace"
    CHATGPT = "chatgpt"
    CLAUDECODE = "claudecode"


# Periods are inclusive: (4, 6) downloads PERIOD_4, PERIOD_5, PERIOD_6
PERIODS_CONFIG = {
    ##### Bi-monthly scanners (6 periods per year) #####
    # Current period is downloadable only at the 1st month of the current bimonthly period (e.g., Jan-Feb at Jan 1st)
    Platform.ARNONA: (4, 6),
    # A period is downloadable only at the 1st day of the next bimonthly period (e.g., 15th Jan- 15th Mar at Apr 1st)
    # Period 1 = 15th of Nov - 15th of Jan ; Period 6 = 15th of Sep - 15th of Nov
    Platform.MEITAV: (4, 6),
    ##### Monthly scanners (12 periods per year) #####
    # Can only download the last 6 months
    # Current month is downloadable only at the 14th of the current month (e.g., Oct at Oct 14th)
    Platform.PARTNER: (4, 11),
    # Current month is downloadable only at the 2nd of the next month (e.g., Oct at Nov 2nd)
    Platform.GOOGLE_WORKSPACE: (8, 11),
    # Current month is downloadable only at the 18th of the current month (e.g., Oct at Oct 18th)
    # Token expires every 90 days (To be sure today is 13th of Dec, check if 14th of Mar we don't have access)
    # Note to myself: Next invoice will be at Feb 18th, 2026 for Feb only, delete after this date
    Platform.CHATGPT: (8, 11),
    # Current month is downloadable only at the 12th of the current month (e.g., Oct at Oct 12th)
    Platform.CLAUDECODE: (8, 12),
}


def get_periods_to_download(platform: str) -> list[str]:
    if platform not in PERIODS_CONFIG:
        raise KeyError(
            f"Platform '{platform}' not found in PERIODS_CONFIG. "
            f"Available platforms: {list(PERIODS_CONFIG.keys())}"
        )

    start_period, end_period = PERIODS_CONFIG[platform]
    return [f"PERIOD_{i}" for i in range(start_period, end_period + 1)]
