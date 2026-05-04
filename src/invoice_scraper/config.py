from enum import StrEnum

from dotenv import load_dotenv

YEAR = 2026


class Platform(StrEnum):
    PARTNER = "partner"
    MEITAV = "meitav"
    ARNONA = "arnona"
    AMISRAGAS = "amisragas"
    GOOGLE_WORKSPACE = "google_workspace"
    CHATGPT = "chatgpt"
    CLAUDECODE = "claudecode"


# Periods are inclusive: (4, 6) downloads periods 4, 5, 6
PERIODS_CONFIG = {
    ##### Monthly scanners (12 periods per year) #####
    # Current month is downloadable only at the 18th of the next month (e.g., Oct at Nov 18th)
    ###### THIS IS NOT TRUE, CHECK THE DATES AGAIN #######
    Platform.AMISRAGAS: (2, 3),
    # Current month is downloadable only at the 18th of the current month (e.g., Oct at Oct 18th)
    # Token expires every 90 days (To be sure today is 5th of May, check if 4th of Aug we don't have access)
    Platform.CHATGPT: (3, 4),
    # Current month is downloadable only at the 2nd of the next month (e.g., Oct at Nov 2nd)
    Platform.GOOGLE_WORKSPACE: (3, 4),
    # Can only download the last 6 months!
    # Current month is downloadable only at the 14th of the current month (e.g., Oct at Oct 14th)
    Platform.PARTNER: (3, 4),
    ##### Bi-monthly scanners (6 periods per year) #####
    # Current period is downloadable only at the 1st month of the current bimonthly period (e.g., Jan-Feb at Jan 1st)
    Platform.ARNONA: (2, 3),
    # A period is downloadable only at the 1st day of the next bimonthly period (e.g., 15th Jan- 15th Mar at Apr 1st)
    # Period 1 = 15th of Nov - 15th of Jan ; Period 6 = 15th of Sep - 15th of Nov
    Platform.MEITAV: (2, 2),
    # Current month is downloadable only at the 12th of the current month (e.g., Oct at Oct 12th)
    ###### Not relevant no more #######
    # Platform.CLAUDECODE: (1, 2),
    ###########################################################################################################################
    ######## FOR CANVA, go to https://www.canva.com/settings/purchase-history and download the invoice at 4th of August #######
    ###########################################################################################################################
    ###########################################################################################################################
    ######## FOR FREEPIK, go to email inbox and download the invoice at 2nd of December #######################################
    ###########################################################################################################################
}

_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTH_HEBREW = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]

PERIOD_VALUES: dict[Platform, list[str]] = {
    Platform.ARNONA: [f"ארנונה תקופתי {i}" for i in range(1, 7)],
    Platform.MEITAV: [f"{i}-{YEAR}" for i in range(1, 7)],
    Platform.PARTNER: [f"{month} {YEAR}" for month in _MONTH_HEBREW],
    Platform.AMISRAGAS: [f"{i:02d}" for i in range(1, 13)],
    Platform.GOOGLE_WORKSPACE: list(_MONTH_ABBR),
    Platform.CHATGPT: list(_MONTH_ABBR),
    Platform.CLAUDECODE: list(_MONTH_ABBR),
}


def get_periods_to_download(platform: Platform) -> list[str]:
    if platform not in PERIODS_CONFIG:
        raise KeyError(f"Platform '{platform}' not found in PERIODS_CONFIG. Available platforms: {list(PERIODS_CONFIG.keys())}")

    start, end = PERIODS_CONFIG[platform]
    return PERIOD_VALUES[platform][start - 1 : end]


def load_config():
    load_dotenv(".env.defaults")
    load_dotenv(".env", override=True)
