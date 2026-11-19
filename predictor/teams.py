"""Team-name mapping: every source's spelling -> one canonical team_id.

config/teams.csv is the single source of truth (hand-editable):
  team_id, name (display), country, aliases ("|"-separated)

Names are compared after `normalise()`, which strips accents, punctuation, club
suffixes (FC, AFC, CF, SSC...) and numbers, so "Arsenal FC" == "Arsenal" and
"Club Atlético de Madrid" == "Atletico Madrid" without needing an alias. Aliases
only cover genuinely different names ("Man United", "Barca", "Inter").

    python -m predictor.teams check   # list names in the data with no mapping
"""
import csv
import difflib
import re
import unicodedata
from functools import lru_cache

from predictor.config import TEAMS_PATH

# Club-type tokens that carry no identity. Kept deliberately short: each one
# risks merging different clubs, and tests check that no two teams collide.
_NOISE = {
    "fc", "afc", "cf", "sc", "ssc", "ac", "as", "ss", "us", "sv", "sk", "fk", "bk",
    "if", "cd", "ud", "rcd", "sd", "ca", "club", "de", "calcio", "tsg", "vfl", "vfb",
    "fsv", "bsc", "kv", "kaa", "krc", "osc", "ogc", "the",
}


# Letters NFKD can't split into base + accent; without this "København" -> "kbenhavn"
_TRANSLIT = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "Ae", "ß": "ss", "đ": "d",
                           "Đ": "D", "ł": "l", "Ł": "L", "ı": "i", "œ": "oe", "Œ": "Oe"})


def normalise(name: str) -> str:
    s = unicodedata.normalize("NFKD", name.translate(_TRANSLIT)).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(t for t in s.split() if t not in _NOISE and not t.isdigit())


@lru_cache(maxsize=1)
def load_teams(path=TEAMS_PATH) -> tuple[dict, dict]:
    """Returns (teams_by_id, alias_lookup). Raises if two teams share an alias."""
    teams, lookup = {}, {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            tid = row["team_id"]
            teams[tid] = row
            for alias in [row["name"], *filter(None, row["aliases"].split("|"))]:
                key = (normalise(alias), row["country"])
                if lookup.get(key, tid) != tid:
                    raise ValueError(f"alias '{alias}' maps to both {lookup[key]} and {tid}")
                lookup[key] = tid
    return teams, lookup


def resolve(name: str, country: str | None = None) -> str | None:
    """Map any spelling to a team_id. `country` disambiguates; None = any country.
    Returns None if unknown (callers decide whether that's an error)."""
    _, lookup = load_teams()
    key = normalise(name)
    if country is not None:
        return lookup.get((key, country))
    hits = {tid for (k, _), tid in lookup.items() if k == key}
    return hits.pop() if len(hits) == 1 else None


def suggest(name: str, n: int = 3) -> list[str]:
    """Closest known teams to an unmapped name (to help fill in aliases)."""
    teams, lookup = load_teams()
    keys = {k: tid for (k, _), tid in lookup.items()}
    close = difflib.get_close_matches(normalise(name), keys, n=n, cutoff=0.5)
    return [teams[keys[k]]["name"] for k in close]


def _check():
    from predictor.ingest.football_data_uk import load_all
    from predictor.leagues import LEAGUES
    df = load_all(refresh=False)
    missing = set()
    for col in ("home_raw", "away_raw"):
        for league, name in df[["league", col]].drop_duplicates().itertuples(index=False):
            if resolve(name, LEAGUES[league]["country"]) is None:
                missing.add((LEAGUES[league]["country"], name))
    for country, name in sorted(missing):
        print(f"UNMAPPED {country}: {name!r}  suggestions: {suggest(name)}")
    print(f"{len(missing)} unmapped names")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["check"]:
        _check()
    else:
        print(__doc__)
