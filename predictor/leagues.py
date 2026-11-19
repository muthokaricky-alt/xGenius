"""Leagues we ingest, and their codes in each data source.

`fduk` = football-data.co.uk file code. `fduk_format` is "main" (one CSV per
season under mmz4281/) or "extra" (one CSV with all seasons under new/).
`fdorg` = football-data.org competition code (None = not on the free tier).

Leagues not in config/coverage.json are still trained on: their clubs play in
the Champions League, so we need their ratings (milestone 7).
"""

LEAGUES = {
    # Covered leagues (see config/coverage.json)
    "premier_league":   {"country": "England",     "fduk": "E0",  "fduk_format": "main",  "fdorg": "PL"},
    "bundesliga":       {"country": "Germany",     "fduk": "D1",  "fduk_format": "main",  "fdorg": "BL1"},
    "serie_a":          {"country": "Italy",       "fduk": "I1",  "fduk_format": "main",  "fdorg": "SA"},
    "ligue_1":          {"country": "France",      "fduk": "F1",  "fduk_format": "main",  "fdorg": "FL1"},
    "la_liga":          {"country": "Spain",       "fduk": "SP1", "fduk_format": "main",  "fdorg": "PD"},
    "champions_league": {"country": None,          "fduk": None,  "fduk_format": None,    "fdorg": "CL"},
    # Training-only leagues: regular Champions League participants
    "eredivisie":       {"country": "Netherlands", "fduk": "N1",  "fduk_format": "main",  "fdorg": "DED"},
    "primeira_liga":    {"country": "Portugal",    "fduk": "P1",  "fduk_format": "main",  "fdorg": "PPL"},
    "belgian_pro":      {"country": "Belgium",     "fduk": "B1",  "fduk_format": "main",  "fdorg": None},
    "scottish_prem":    {"country": "Scotland",    "fduk": "SC0", "fduk_format": "main",  "fdorg": None},
    "super_lig":        {"country": "Turkey",      "fduk": "T1",  "fduk_format": "main",  "fdorg": None},
    "greek_super":      {"country": "Greece",      "fduk": "G1",  "fduk_format": "main",  "fdorg": None},
    "austrian_bl":      {"country": "Austria",     "fduk": "AUT", "fduk_format": "extra", "fdorg": None},
    "swiss_super":      {"country": "Switzerland", "fduk": "SWZ", "fduk_format": "extra", "fdorg": None},
    "danish_super":     {"country": "Denmark",     "fduk": "DNK", "fduk_format": "extra", "fdorg": None},
    "eliteserien":      {"country": "Norway",      "fduk": "NOR", "fduk_format": "extra", "fdorg": None},
}

FIRST_SEASON = 2014  # 2014/15. Seasons are identified by their starting year.


def current_season(today=None) -> int:
    """European seasons start in July/August; Jan-Jun belongs to last year's season."""
    import datetime as dt
    today = today or dt.date.today()
    return today.year if today.month >= 7 else today.year - 1
