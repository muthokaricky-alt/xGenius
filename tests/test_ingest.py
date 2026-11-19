import pandas as pd

from predictor.ingest.football_data_org import parse_matches
from predictor.ingest.football_data_uk import _normalise, season_code
from predictor.leagues import current_season


def test_season_code():
    assert season_code(2014) == "1415"
    assert season_code(2099) == "9900"


def test_current_season_boundary():
    import datetime as dt
    assert current_season(dt.date(2026, 6, 30)) == 2025
    assert current_season(dt.date(2026, 7, 1)) == 2026


def test_old_and_new_csv_formats():
    old = pd.DataFrame({"Date": ["22/08/14"], "HomeTeam": ["Bayern Munich"], "AwayTeam": ["Wolfsburg"],
                        "FTHG": [2], "FTAG": [1], "BbAvH": [1.25], "BbAvD": [6.0], "BbAvA": [11.0],
                        "PSCH": [1.24], "PSCD": [6.5], "PSCA": [12.0]})
    out = _normalise(old, "bundesliga", 2014).iloc[0]
    assert out.date == pd.Timestamp("2014-08-22")
    assert out.odds_pre_h == 1.25 and out.pin_close_a == 12.0
    assert pd.isna(out.odds_close_h) and pd.isna(out.home_xg)

    extra = pd.DataFrame({"Season": ["2023/2024"], "Date": ["21/07/2023"], "Home": ["Salzburg"],
                          "Away": ["Ried"], "HG": [3], "AG": [0], "AvgCH": [1.2], "AvgCD": [6.0], "AvgCA": [12.0]})
    out = _normalise(extra, "austrian_bl", None).iloc[0]
    assert out.season == 2023 and out.odds_close_h == 1.2


def test_api_uses_90_minute_score_in_knockouts():
    payload = {"matches": [{
        "id": 1, "utcDate": "2025-03-11T20:00:00Z", "status": "FINISHED", "stage": "LAST_16",
        "homeTeam": {"name": "Club Atlético de Madrid"}, "awayTeam": {"name": "Real Madrid CF"},
        "score": {"duration": "PENALTY_SHOOTOUT", "fullTime": {"home": 5, "away": 5},
                  "regularTime": {"home": 1, "away": 0}},
    }]}
    row = parse_matches(payload, "champions_league").iloc[0]
    assert (row.home_goals, row.away_goals) == (1, 0)
    assert (row.home_id, row.away_id) == ("atletico-madrid", "real-madrid")
