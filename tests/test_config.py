from predictor.config import is_shown, load_coverage, training_leagues

cov = load_coverage()


def test_full_coverage_league_always_shown():
    assert is_shown("premier_league", "Brentford", "Fulham", cov)
    assert is_shown("champions_league", "Celtic", "Club Brugge", cov)


def test_big_club_filter():
    assert is_shown("serie_a", "Juventus", "Empoli", cov)
    assert is_shown("serie_a", "Empoli", "Juventus", cov)
    assert not is_shown("serie_a", "Empoli", "Lecce", cov)


def test_uncovered_league_hidden():
    assert not is_shown("eredivisie", "Ajax", "PSV", cov)


def test_training_includes_all_big_club_leagues():
    assert training_leagues(cov) == {
        "premier_league", "champions_league",
        "bundesliga", "serie_a", "ligue_1", "la_liga",
    }
