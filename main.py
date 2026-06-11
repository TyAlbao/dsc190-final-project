import argparse
import json
import re
from datetime import date, timedelta
from urllib.parse import urlencode

import numpy as np
import pandas as pd
from pybaseball import playerid_reverse_lookup, statcast


TEAM_IDS = {
    "ARI": 109,
    "ATL": 144,
    "BAL": 110,
    "BOS": 111,
    "CHC": 112,
    "CHW": 145,
    "CWS": 145,
    "CIN": 113,
    "CLE": 114,
    "COL": 115,
    "DET": 116,
    "HOU": 117,
    "KC": 118,
    "KCR": 118,
    "LAA": 108,
    "LAD": 119,
    "MIA": 146,
    "MIL": 158,
    "MIN": 142,
    "NYM": 121,
    "NYY": 147,
    "OAK": 133,
    "ATH": 133,
    "PHI": 143,
    "PIT": 134,
    "SD": 135,
    "SDP": 135,
    "SEA": 136,
    "SF": 137,
    "SFG": 137,
    "STL": 138,
    "TB": 139,
    "TBR": 139,
    "TEX": 140,
    "TOR": 141,
    "WSH": 120,
}


HIT_RESULT_BY_EVENT = {
    "single": "Single",
    "double": "Double",
    "triple": "Triple",
    "home_run": "Home Run",
    "field_out": "Out",
    "force_out": "Out",
    "fielders_choice_out": "Fielders Choice",
    "other_out": "Out",
    "strikeout": "Strikeout",
    "strikeout_double_play": "Double Play",
    "field_error": "Error",
    "catcher_interf": "Catcher Interference",
    "hit_by_pitch": "Hit By Pitch",
    "double_play": "Double Play",
    "grounded_into_double_play": "Double Play",
    "sac_fly_double_play": "Double Play",
    "fielders_choice": "Fielders Choice",
    "sac_bunt": "Sacrifice",
    "sac_fly": "Sacrifice",
    "sac_bunt_double_play": "Double Play",
    "triple_play": "Triple Play",
    "walk": "Walk",
    "intent_walk": "Walk",
}


BATTER_NAME_PATTERN = re.compile(
    r"^(?P<name>.+?) "
    r"(homers|singles|doubles|triples|grounds|lines|flies|pops|strikes|walks|"
    r"reaches|hits|bunts|fouls|is hit|called out)"
)


def make_mlb_video_search_url(
    runner_on_base=None,
    outs=None,
    hit_distance=None,
    hit_results=None,
    seasons=None,
    team_id=None,
    game_dates=None,
    batter_id=None,
    balls=None,
    strikes=None,
    innings=None,
    page=0,
):
    clauses = []

    if runner_on_base is not None:
        values = ",".join(str(base) for base in runner_on_base)
        clauses.append(f"RunnerOnBase == [{values}]")

    if outs is not None:
        values = ",".join(str(out) for out in outs)
        clauses.append(f"Outs = [{values}]")

    if hit_distance is not None:
        minimum, maximum = hit_distance
        clauses.append(f"HitDistance = {{{{ {minimum}, {maximum} }}}}")

    if hit_results is not None:
        values = json.dumps(hit_results, separators=(",", ":"))
        clauses.append(f"HitResult = {values}")

    if seasons is not None:
        values = ",".join(str(season) for season in seasons)
        clauses.append(f"Season = [{values}]")

    if team_id is not None:
        clauses.append(f"TeamId == [{team_id}]")

    if game_dates is not None:
        values = json.dumps(game_dates, separators=(",", ":"))
        clauses.append(f"Date = {values}")

    if batter_id is not None:
        clauses.append(f"BatterId = [{batter_id}]")

    if balls is not None:
        values = ",".join(str(ball) for ball in balls)
        clauses.append(f"Balls = [{values}]")

    if strikes is not None:
        values = ",".join(str(strike) for strike in strikes)
        clauses.append(f"Strikes = [{values}]")

    if innings is not None:
        values = ",".join(str(inning) for inning in innings)
        clauses.append(f"Inning = [{values}]")

    query = " AND ".join(clauses)
    if query:
        query += " "
    query += "Order By Timestamp DESC"

    parameters = {
        "q": query,
        "cp": "MIXED",
        "p": page,
        "of": 1,
    }

    return "https://www.mlb.com/video/?" + urlencode(parameters)


def parse_args():
    yesterday = date.today() - timedelta(days=1)

    parser = argparse.ArgumentParser(
        description=(
            "Print the biggest win-expectancy swing, hardest-hit ball, and "
            "farthest-hit ball for a Statcast date range."
        )
    )
    parser.add_argument(
        "--start",
        default=yesterday.isoformat(),
        help="Start date in YYYY-MM-DD format. Defaults to yesterday.",
    )
    parser.add_argument(
        "--end",
        default=yesterday.isoformat(),
        help="End date in YYYY-MM-DD format. Defaults to yesterday.",
    )
    return parser.parse_args()


def get_batter_names(data):
    batter_ids = (
        data["batter"].dropna().astype(int).drop_duplicates().sort_values().tolist()
    )
    if not batter_ids:
        return {}

    lookup = playerid_reverse_lookup(batter_ids, key_type="mlbam")
    lookup["name"] = (lookup["name_first"] + " " + lookup["name_last"]).str.title()
    return dict(zip(lookup["key_mlbam"], lookup["name"]))


def format_statcast_player_name(name):
    if pd.isna(name) or not name:
        return None

    name = str(name)
    if "," in name:
        last, first = [part.strip() for part in name.split(",", maxsplit=1)]
        return f"{first} {last}".title()

    return name.title()


def player_name_from_description(description):
    if pd.isna(description) or not description:
        return None

    match = BATTER_NAME_PATTERN.search(str(description))
    if not match:
        return None

    return match.group("name").strip().title()


def clean_statcast_data(data):
    data = data.copy()
    numeric_columns = [
        "batter",
        "delta_home_win_exp",
        "launch_speed",
        "hit_distance_sc",
        "outs_when_up",
        "game_year",
        "balls",
        "strikes",
        "inning",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    return data


def batting_team_for_play(row):
    if row.get("inning_topbot") == "Top":
        return row.get("away_team")
    return row.get("home_team")


def runners_on_base(row):
    bases = []
    for base, column in [(1, "on_1b"), (2, "on_2b"), (3, "on_3b")]:
        if pd.notna(row.get(column)):
            bases.append(base)
    return bases or None


def hit_distance_window(row, padding=3):
    distance = row.get("hit_distance_sc")
    if pd.isna(distance):
        return None

    rounded = int(round(distance))
    return max(0, rounded - padding), rounded + padding


def hit_result_for_video(row):
    event = row.get("events")
    if pd.isna(event):
        return None

    return HIT_RESULT_BY_EVENT.get(str(event))


def video_url_for_play(row):
    season = row.get("game_year")
    team_abbr = batting_team_for_play(row)
    team_id = TEAM_IDS.get(str(team_abbr).upper()) if pd.notna(team_abbr) else None
    batter_id = row.get("batter")
    outs = row.get("outs_when_up")
    balls = row.get("balls")
    strikes = row.get("strikes")
    inning = row.get("inning")
    game_date = row.get("game_date")
    hit_result = hit_result_for_video(row)

    return make_mlb_video_search_url(
        runner_on_base=runners_on_base(row),
        outs=[int(outs)] if pd.notna(outs) else None,
        hit_distance=hit_distance_window(row),
        hit_results=[hit_result] if hit_result is not None else None,
        seasons=[int(season)] if pd.notna(season) else None,
        team_id=team_id,
        game_dates=[str(game_date)] if pd.notna(game_date) else None,
        batter_id=int(batter_id) if pd.notna(batter_id) else None,
        balls=[int(balls)] if pd.notna(balls) else None,
        strikes=[int(strikes)] if pd.notna(strikes) else None,
        innings=[int(inning)] if pd.notna(inning) else None,
    )


def format_value(value, unit="", decimals=1):
    if pd.isna(value):
        return "unknown"
    return f"{value:.{decimals}f}{unit}"


def describe_play(label, row, batter_names, metric_text):
    batter_id = int(row["batter"]) if pd.notna(row.get("batter")) else None
    statcast_name = format_statcast_player_name(row.get("player_name"))
    description = row.get("des", "")
    description_name = player_name_from_description(description)
    player = (
        description_name
        or batter_names.get(batter_id)
        or statcast_name
        or (f"MLBAM {batter_id}" if batter_id else "Unknown")
    )
    game_date = row.get("game_date", "unknown date")
    batting_team = batting_team_for_play(row)
    matchup = f"{row.get('away_team')} at {row.get('home_team')}"
    event = str(row.get("events", "unknown")).replace("_", " ")

    print(f"\n{label}")
    print(f"Player: {player}")
    print(f"Metric: {metric_text}")
    print(f"Game: {game_date} - {matchup}")
    print(f"Batting team: {batting_team}")
    print(f"Result: {event}")
    if pd.notna(description) and description:
        print(f"Play: {description}")
    print(f"MLB video search: {video_url_for_play(row)}")


def row_with_largest_abs_value(data, column):
    values = data[column].dropna()
    if values.empty:
        return None
    return data.loc[values.abs().idxmax()]


def row_with_largest_value(data, column):
    values = data[column].dropna()
    if values.empty:
        return None
    return data.loc[values.idxmax()]


def print_result(label, row, batter_names, metric_text):
    if row is None:
        print(f"\n{label}")
        print("No qualifying Statcast row found.")
        return

    describe_play(label, row, batter_names, metric_text(row))


def main():
    args = parse_args()

    print(f"Fetching Statcast data from {args.start} through {args.end}...")
    data = clean_statcast_data(statcast(start_dt=args.start, end_dt=args.end))

    if data.empty:
        print("No Statcast data found for that date range.")
        return

    batter_names = get_batter_names(data)
    completed_plays = data[data["events"].notna()]
    videoable_plays = completed_plays[
        completed_plays["events"].map(HIT_RESULT_BY_EVENT).notna()
    ]

    win_exp_row = row_with_largest_abs_value(videoable_plays, "delta_home_win_exp")
    hardest_hit_row = row_with_largest_value(videoable_plays, "launch_speed")
    farthest_hit_row = row_with_largest_value(videoable_plays, "hit_distance_sc")

    print_result(
        "Biggest swing in win expectancy",
        win_exp_row,
        batter_names,
        lambda row: (
            f"{format_value(np.abs(row.get('delta_home_win_exp')) * 100, '%', 1)} "
            "change in home win expectancy"
        ),
    )
    print_result(
        "Hardest-hit ball",
        hardest_hit_row,
        batter_names,
        lambda row: f"{format_value(row.get('launch_speed'), ' mph', 1)} exit velocity",
    )
    print_result(
        "Farthest-hit ball",
        farthest_hit_row,
        batter_names,
        lambda row: f"{format_value(row.get('hit_distance_sc'), ' ft', 0)} projected distance",
    )


if __name__ == "__main__":
    main()
