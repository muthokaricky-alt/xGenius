import json

from predictor.config import COVERAGE_PATH, is_shown, load_coverage, training_leagues

cov = load_coverage()


def test_every_coverage_team_resolves():
    raw = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    for league, names in raw["big_clubs"].items():
        assert len(cov["big_clubs"][league]) == len(names), league


def test_full_coverage_league_always_shown():
    assert is_shown("premier_league", "brentford", "fulham", cov)
    assert is_shown("champions_league", "celtic", "club-brugge", cov)


def test_big_club_filter():
    assert is_shown("serie_a", "juventus", "empoli", cov)
    assert is_shown("serie_a", "empoli", "juventus", cov)
    assert not is_shown("serie_a", "empoli", "lecce", cov)
    assert is_shown("ligue_1", "paris-saint-germain", "lens", cov)


def test_uncovered_league_hidden():
    assert not is_shown("eredivisie", "ajax", "psv", cov)


def test_training_includes_all_big_club_leagues():
    assert training_leagues(cov) == {
        "premier_league", "champions_league",
        "bundesliga", "serie_a", "ligue_1", "la_liga",
    }
