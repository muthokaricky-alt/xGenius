import pytest

from predictor.teams import load_teams, normalise, resolve


@pytest.mark.parametrize("name,country,expected", [
    # football-data.co.uk spellings
    ("Man United", "England", "manchester-united"),
    ("Nott'm Forest", "England", "nottingham-forest"),
    ("Ath Madrid", "Spain", "atletico-madrid"),
    ("Paris SG", "France", "paris-saint-germain"),
    ("Milan", "Italy", "milan"),
    # football-data.org official names (suffix stripping, accents)
    ("Manchester United FC", "England", "manchester-united"),
    ("Club Atlético de Madrid", "Spain", "atletico-madrid"),
    ("FC Bayern München", "Germany", "bayern-munich"),
    ("FC Internazionale Milano", "Italy", "inter"),
    ("1. FC Köln", "Germany", "koln"),
    ("Paris Saint-Germain FC", "France", "paris-saint-germain"),
    # user-style nicknames (Postel's law)
    ("Barca", "Spain", "barcelona"),
    ("Man U", "England", "manchester-united"),
    ("PSG", "France", "paris-saint-germain"),
])
def test_resolve(name, country, expected):
    assert resolve(name, country) == expected


def test_paris_fc_is_not_psg():
    assert resolve("Paris FC", "France") != resolve("PSG", "France")


def test_different_clubs_stay_separate():
    assert resolve("Ajaccio", "France") != resolve("Ajaccio GFCO", "France")
    assert resolve("Gaziantep", "Turkey") != resolve("Gaziantepspor", "Turkey")


def test_renamed_club_merged():
    assert resolve("Waasland-Beveren", "Belgium") == resolve("Beveren", "Belgium")


def test_country_free_lookup_for_champions_league():
    assert resolve("Real Madrid CF") == "real-madrid"
    assert resolve("FK Shakhtar Donetsk") == "shakhtar-donetsk"  # CL-only club
    assert resolve("Some Unknown Club") is None


def test_ids_unique():
    teams, _ = load_teams()
    assert len(teams) == len(set(teams))


def test_normalise():
    assert normalise("Brighton & Hove Albion FC") == "brighton and hove albion"
    assert normalise("TSG 1899 Hoffenheim") == "hoffenheim"
    assert normalise("FC København") == "kobenhavn"
    assert normalise("FK Bodø/Glimt") == "bodo glimt"
