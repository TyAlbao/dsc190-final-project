import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
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

BALLPARK_DIMENSIONS = {
    "ARI": {"lf": 330, "lc": 376, "cf": 407, "rc": 376, "rf": 335},
    "ATL": {"lf": 335, "lc": 385, "cf": 400, "rc": 375, "rf": 325},
    "BAL": {"lf": 333, "lc": 364, "cf": 410, "rc": 373, "rf": 318},
    "BOS": {"lf": 310, "lc": 379, "cf": 390, "rc": 380, "rf": 302},
    "CHC": {"lf": 355, "lc": 368, "cf": 400, "rc": 368, "rf": 353},
    "CWS": {"lf": 330, "lc": 375, "cf": 400, "rc": 375, "rf": 335},
    "CIN": {"lf": 328, "lc": 379, "cf": 404, "rc": 370, "rf": 325},
    "CLE": {"lf": 325, "lc": 370, "cf": 400, "rc": 375, "rf": 325},
    "COL": {"lf": 347, "lc": 390, "cf": 415, "rc": 375, "rf": 350},
    "DET": {"lf": 345, "lc": 370, "cf": 420, "rc": 365, "rf": 330},
    "HOU": {"lf": 315, "lc": 362, "cf": 409, "rc": 373, "rf": 326},
    "KC": {"lf": 330, "lc": 387, "cf": 410, "rc": 387, "rf": 330},
    "LAA": {"lf": 330, "lc": 382, "cf": 400, "rc": 365, "rf": 330},
    "LAD": {"lf": 330, "lc": 385, "cf": 395, "rc": 385, "rf": 330},
    "MIA": {"lf": 344, "lc": 386, "cf": 400, "rc": 392, "rf": 335},
    "MIL": {"lf": 344, "lc": 370, "cf": 400, "rc": 374, "rf": 337},
    "MIN": {"lf": 339, "lc": 377, "cf": 404, "rc": 367, "rf": 328},
    "NYM": {"lf": 335, "lc": 379, "cf": 408, "rc": 383, "rf": 330},
    "NYY": {"lf": 318, "lc": 399, "cf": 408, "rc": 385, "rf": 314},
    "OAK": {"lf": 330, "lc": 362, "cf": 400, "rc": 362, "rf": 330},
    "ATH": {"lf": 330, "lc": 362, "cf": 400, "rc": 362, "rf": 330},
    "PHI": {"lf": 329, "lc": 355, "cf": 401, "rc": 357, "rf": 330},
    "PIT": {"lf": 325, "lc": 383, "cf": 399, "rc": 375, "rf": 320},
    "SD": {"lf": 336, "lc": 390, "cf": 396, "rc": 391, "rf": 322},
    "SEA": {"lf": 331, "lc": 378, "cf": 401, "rc": 381, "rf": 326},
    "SF": {"lf": 339, "lc": 399, "cf": 391, "rc": 421, "rf": 309},
    "STL": {"lf": 335, "lc": 375, "cf": 400, "rc": 375, "rf": 335},
    "TB": {"lf": 315, "lc": 370, "cf": 404, "rc": 370, "rf": 322},
    "TEX": {"lf": 329, "lc": 372, "cf": 407, "rc": 374, "rf": 326},
    "TOR": {"lf": 328, "lc": 375, "cf": 400, "rc": 375, "rf": 328},
    "WSH": {"lf": 337, "lc": 377, "cf": 402, "rc": 370, "rf": 335},
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


BATTED_BALL_OUT_EVENTS = {
    "field_out",
    "force_out",
    "fielders_choice_out",
    "double_play",
    "grounded_into_double_play",
    "sac_fly",
    "sac_bunt",
    "sac_bunt_double_play",
    "sac_fly_double_play",
    "triple_play",
}


BATTED_BALL_NON_OUT_EVENTS = {
    "single",
    "double",
    "triple",
    "home_run",
    "field_error",
    "fielders_choice",
}

CATCH_NUMERIC_COLUMNS = [
    "launch_speed",
    "launch_angle",
    "hit_distance_sc",
    "hc_x",
    "hc_y",
    "estimated_ba_using_speedangle",
    "estimated_woba_using_speedangle",
    "estimated_slg_using_speedangle",
    "estimated_wall_distance",
    "distance_to_wall",
    "park_lf",
    "park_lc",
    "park_cf",
    "park_rc",
    "park_rf",
]

CATCH_CATEGORICAL_COLUMNS = [
    "bb_type",
    "hit_location",
    "if_fielding_alignment",
    "of_fielding_alignment",
    "home_team",
    "stand",
    "p_throws",
]

CATCH_MODEL_VERSION = 1


BATTER_NAME_PATTERN = re.compile(
    r"^(?P<name>.+?) "
    r"(homers|singles|doubles|triples|grounds|lines|flies|pops|strikes|walks|"
    r"reaches|hits|bunts|fouls|is hit|called out)"
)

FIELDER_NAME_PATTERN = re.compile(
    r"to (?:left|center|right) fielder (?P<name>[^.]+)"
)


def smart_title_name(name):
    titled = str(name).title()
    replacements = {
        " Ii": " II",
        " Iii": " III",
        " Iv": " IV",
        " Jr": " Jr.",
        " Sr": " Sr.",
    }
    for old, new in replacements.items():
        titled = titled.replace(old, new)
    return titled


def make_mlb_video_search_url(
    runner_on_base=None,
    outs=None,
    hit_distance=None,
    hit_results=None,
    seasons=None,
    team_id=None,
    game_dates=None,
    batter_id=None,
    pitcher_id=None,
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

    if pitcher_id is not None:
        clauses.append(f"PitcherId = [{pitcher_id}]")

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
        default=None,
        help="End date in YYYY-MM-DD format. Defaults to --start.",
    )
    parser.add_argument(
        "--catch-train-start",
        default=None,
        help=(
            "Start date for catch-probability training data. Must be 2023-01-01 "
            "or later. Defaults to --start, or 2023-03-30 in training mode."
        ),
    )
    parser.add_argument(
        "--catch-train-end",
        default=None,
        help="End date for catch-probability training data. Defaults to --end.",
    )
    parser.add_argument(
        "--train-catch-model",
        action="store_true",
        help="Train and save a reusable catch-probability model, then exit.",
    )
    parser.add_argument(
        "--catch-model-path",
        default="catch_probability_model.npz",
        help="Path to save/load the reusable catch-probability model.",
    )
    parser.add_argument(
        "--catch-train-chunk-days",
        type=int,
        default=14,
        help="Number of days per Statcast request when training a saved model.",
    )
    args = parser.parse_args()
    if args.end is None:
        args.end = args.start
    return args


def get_batter_names(data):
    batter_ids = (
        data["batter"].dropna().astype(int).drop_duplicates().sort_values().tolist()
    )
    if not batter_ids:
        return {}

    lookup = playerid_reverse_lookup(batter_ids, key_type="mlbam")
    lookup["name"] = (lookup["name_first"] + " " + lookup["name_last"]).map(
        smart_title_name
    )
    return dict(zip(lookup["key_mlbam"], lookup["name"]))


def get_pitcher_names(data):
    pitcher_ids = (
        data["pitcher"].dropna().astype(int).drop_duplicates().sort_values().tolist()
    )
    if not pitcher_ids:
        return {}

    lookup = playerid_reverse_lookup(pitcher_ids, key_type="mlbam")
    lookup["name"] = (lookup["name_first"] + " " + lookup["name_last"]).map(
        smart_title_name
    )
    return dict(zip(lookup["key_mlbam"], lookup["name"]))


def format_statcast_player_name(name):
    if pd.isna(name) or not name:
        return None

    name = str(name)
    if "," in name:
        last, first = [part.strip() for part in name.split(",", maxsplit=1)]
        return smart_title_name(f"{first} {last}")

    return smart_title_name(name)


def player_name_from_description(description):
    if pd.isna(description) or not description:
        return None

    match = BATTER_NAME_PATTERN.search(str(description))
    if not match:
        return None

    return smart_title_name(match.group("name").strip())


def fielder_name_from_description(description):
    if pd.isna(description) or not description:
        return None

    match = FIELDER_NAME_PATTERN.search(str(description))
    if not match:
        return None

    return smart_title_name(match.group("name").strip())


def validate_catch_training_dates(start, end):
    minimum = date(2023, 1, 1)
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    if start_date < minimum:
        raise ValueError("Catch-probability training data must start on 2023-01-01 or later.")
    if end_date < start_date:
        raise ValueError("Catch-probability training end date must be on or after start date.")


def clean_statcast_data(data):
    data = data.copy()
    numeric_columns = [
        "batter",
        "pitcher",
        "delta_home_win_exp",
        "launch_speed",
        "hit_distance_sc",
        "release_speed",
        "api_break_x_arm",
        "pfx_z",
        "outs_when_up",
        "game_year",
        "balls",
        "strikes",
        "inning",
        "hit_location",
        "hc_x",
        "hc_y",
        "launch_angle",
        "estimated_ba_using_speedangle",
        "estimated_woba_using_speedangle",
        "estimated_slg_using_speedangle",
        "babip_value",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    return data


def batting_team_for_play(row):
    if row.get("inning_topbot") == "Top":
        return row.get("away_team")
    return row.get("home_team")


def pitching_team_for_play(row):
    if row.get("inning_topbot") == "Top":
        return row.get("home_team")
    return row.get("away_team")


def win_exp_benefiting_team(row):
    change = row.get("delta_home_win_exp")
    if pd.isna(change):
        return None
    if change > 0:
        return row.get("home_team")
    if change < 0:
        return row.get("away_team")
    return None


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


def video_url_for_pitch(row):
    season = row.get("game_year")
    team_abbr = pitching_team_for_play(row)
    team_id = TEAM_IDS.get(str(team_abbr).upper()) if pd.notna(team_abbr) else None
    pitcher_id = row.get("pitcher")
    outs = row.get("outs_when_up")
    balls = row.get("balls")
    strikes = row.get("strikes")
    inning = row.get("inning")
    game_date = row.get("game_date")

    return make_mlb_video_search_url(
        runner_on_base=runners_on_base(row),
        outs=[int(outs)] if pd.notna(outs) else None,
        seasons=[int(season)] if pd.notna(season) else None,
        team_id=team_id,
        game_dates=[str(game_date)] if pd.notna(game_date) else None,
        pitcher_id=int(pitcher_id) if pd.notna(pitcher_id) else None,
        balls=[int(balls)] if pd.notna(balls) else None,
        strikes=[int(strikes)] if pd.notna(strikes) else None,
        innings=[int(inning)] if pd.notna(inning) else None,
    )


def video_url_for_defensive_play(row):
    season = row.get("game_year")
    team_abbr = pitching_team_for_play(row)
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


def describe_win_exp_play(label, row, batter_names, pitcher_names, metric_text):
    batter_id = int(row["batter"]) if pd.notna(row.get("batter")) else None
    pitcher_id = int(row["pitcher"]) if pd.notna(row.get("pitcher")) else None
    description = row.get("des", "")
    batting_team = batting_team_for_play(row)
    pitching_team = pitching_team_for_play(row)
    benefiting_team = win_exp_benefiting_team(row)

    batter = (
        player_name_from_description(description)
        or batter_names.get(batter_id)
        or (f"MLBAM {batter_id}" if batter_id else "Unknown")
    )
    pitcher = (
        pitcher_names.get(pitcher_id)
        or format_statcast_player_name(row.get("player_name"))
        or (f"MLBAM {pitcher_id}" if pitcher_id else "Unknown")
    )

    if benefiting_team == batting_team:
        impact_player = batter
        impact_role = "batter"
    elif benefiting_team == pitching_team:
        impact_player = pitcher
        impact_role = "pitcher"
    else:
        impact_player = batter
        impact_role = "batter"

    game_date = row.get("game_date", "unknown date")
    matchup = f"{row.get('away_team')} at {row.get('home_team')}"
    event = str(row.get("events", "unknown")).replace("_", " ")

    print(f"\n{label}")
    print(f"Player: {impact_player}")
    print(f"Role: {impact_role}")
    if benefiting_team:
        print(f"Benefiting team: {benefiting_team}")
    print(f"Metric: {metric_text}")
    print(f"Game: {game_date} - {matchup}")
    print(f"Batting team: {batting_team}")
    print(f"Pitching team: {pitching_team}")
    print(f"Result: {event}")
    if pd.notna(description) and description:
        print(f"Play: {description}")
    print(f"MLB video search: {video_url_for_play(row)}")


def describe_pitch(label, row, pitcher_names, metric_text):
    pitcher_id = int(row["pitcher"]) if pd.notna(row.get("pitcher")) else None
    statcast_name = format_statcast_player_name(row.get("player_name"))
    player = (
        pitcher_names.get(pitcher_id)
        or statcast_name
        or (f"MLBAM {pitcher_id}" if pitcher_id else "Unknown")
    )
    game_date = row.get("game_date", "unknown date")
    pitching_team = pitching_team_for_play(row)
    matchup = f"{row.get('away_team')} at {row.get('home_team')}"
    pitch_name = row.get("pitch_name") or row.get("pitch_type") or "unknown pitch"
    description = str(row.get("description", "unknown")).replace("_", " ")

    print(f"\n{label}")
    print(f"Pitcher: {player}")
    print(f"Metric: {metric_text}")
    print(f"Game: {game_date} - {matchup}")
    print(f"Pitching team: {pitching_team}")
    print(f"Pitch: {pitch_name}")
    print(f"Result: {description}")
    print(f"MLB video search: {video_url_for_pitch(row)}")


def describe_defensive_play(label, row, batter_names, metric_text):
    batter_id = int(row["batter"]) if pd.notna(row.get("batter")) else None
    description = row.get("des", "")
    batter = (
        player_name_from_description(description)
        or batter_names.get(batter_id)
        or format_statcast_player_name(row.get("player_name"))
        or (f"MLBAM {batter_id}" if batter_id else "Unknown")
    )
    game_date = row.get("game_date", "unknown date")
    fielding_team = pitching_team_for_play(row)
    fielder = fielder_name_from_description(description)
    matchup = f"{row.get('away_team')} at {row.get('home_team')}"
    event = str(row.get("events", "unknown")).replace("_", " ")

    print(f"\n{label}")
    print(f"Fielding team: {fielding_team}")
    if fielder:
        print(f"Fielder: {fielder}")
    print(f"Batter: {batter}")
    print(f"Metric: {metric_text}")
    print(f"Game: {game_date} - {matchup}")
    print(f"Result: {event}")
    if pd.notna(description) and description:
        print(f"Play: {description}")
    print(f"MLB video search: {video_url_for_defensive_play(row)}")


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


def row_with_smallest_value(data, column):
    values = data[column].dropna()
    if values.empty:
        return None
    return data.loc[values.idxmin()]


def print_result(label, row, batter_names, metric_text):
    if row is None:
        print(f"\n{label}")
        print("No qualifying Statcast row found.")
        return

    describe_play(label, row, batter_names, metric_text(row))


def print_win_exp_result(label, row, batter_names, pitcher_names, metric_text):
    if row is None:
        print(f"\n{label}")
        print("No qualifying Statcast row found.")
        return

    describe_win_exp_play(label, row, batter_names, pitcher_names, metric_text(row))


def print_pitch_result(label, row, pitcher_names, metric_text):
    if row is None:
        print(f"\n{label}")
        print("No qualifying Statcast row found.")
        return

    describe_pitch(label, row, pitcher_names, metric_text(row))


def print_defensive_result(label, row, batter_names, metric_text):
    if row is None:
        print(f"\n{label}")
        print("No qualifying Statcast row found.")
        return

    describe_defensive_play(label, row, batter_names, metric_text(row))


def bounded_score(value, low, high):
    if pd.isna(value):
        return 0
    return float(np.clip((value - low) / (high - low), 0, 1))


def wall_distance_for_row(row):
    dimensions = BALLPARK_DIMENSIONS.get(str(row.get("home_team")).upper())
    if dimensions is None:
        return np.nan

    hit_location = row.get("hit_location")
    if pd.notna(hit_location):
        hit_location = int(hit_location)
        if hit_location == 7:
            return dimensions["lf"]
        if hit_location == 8:
            return dimensions["cf"]
        if hit_location == 9:
            return dimensions["rf"]

    hc_x = row.get("hc_x")
    if pd.isna(hc_x):
        return dimensions["cf"]

    if hc_x < 110:
        return dimensions["lf"]
    if hc_x < 150:
        return dimensions["lc"]
    if hc_x < 190:
        return dimensions["cf"]
    if hc_x < 230:
        return dimensions["rc"]
    return dimensions["rf"]


def add_ballpark_features(data):
    data = data.copy()
    for key in ["lf", "lc", "cf", "rc", "rf"]:
        data[f"park_{key}"] = data["home_team"].map(
            lambda team: BALLPARK_DIMENSIONS.get(str(team).upper(), {}).get(key, np.nan)
        )
    data["estimated_wall_distance"] = data.apply(wall_distance_for_row, axis=1)
    data["distance_to_wall"] = data["estimated_wall_distance"] - data["hit_distance_sc"]
    return data


def prepare_catch_probability_data(data):
    batted_balls = data[
        data["events"].isin(BATTED_BALL_OUT_EVENTS | BATTED_BALL_NON_OUT_EVENTS)
        & data["bb_type"].isin(["fly_ball", "line_drive", "popup"])
    ].copy()
    batted_balls = batted_balls.dropna(
        subset=["launch_speed", "launch_angle", "hit_distance_sc"]
    )
    if batted_balls.empty:
        return batted_balls

    batted_balls = add_ballpark_features(batted_balls)
    batted_balls["is_catch_out"] = batted_balls["events"].isin(
        {"field_out", "sac_fly", "double_play", "sac_fly_double_play"}
    )
    return batted_balls


def fit_catch_feature_matrix(data):
    numeric_features = data[CATCH_NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    medians = numeric_features.median(numeric_only=True).fillna(0)
    numeric_features = numeric_features.fillna(medians).fillna(0)

    categorical_values = data[CATCH_CATEGORICAL_COLUMNS].astype("object")
    categorical_values = categorical_values.where(pd.notna(categorical_values), "unknown")
    categorical_features = pd.get_dummies(
        categorical_values.astype(str),
        columns=CATCH_CATEGORICAL_COLUMNS,
        prefix=CATCH_CATEGORICAL_COLUMNS,
        prefix_sep="=",
    )

    feature_frame = pd.concat([numeric_features, categorical_features], axis=1)
    feature_names = feature_frame.columns.to_numpy(dtype=str)
    feature_matrix = feature_frame.to_numpy(dtype=np.float64)
    means = feature_matrix.mean(axis=0)
    stds = feature_matrix.std(axis=0)
    stds[stds == 0] = 1

    schema = {
        "feature_names": feature_names,
        "numeric_medians": medians.reindex(CATCH_NUMERIC_COLUMNS).to_numpy(dtype=np.float64),
        "means": means,
        "stds": stds,
    }
    return (feature_matrix - means) / stds, schema


def transform_catch_feature_matrix(data, schema):
    medians = pd.Series(schema["numeric_medians"], index=CATCH_NUMERIC_COLUMNS)
    numeric_features = data[CATCH_NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    numeric_features = numeric_features.fillna(medians).fillna(0)

    categorical_values = data[CATCH_CATEGORICAL_COLUMNS].astype("object")
    categorical_values = categorical_values.where(pd.notna(categorical_values), "unknown")
    categorical_features = pd.get_dummies(
        categorical_values.astype(str),
        columns=CATCH_CATEGORICAL_COLUMNS,
        prefix=CATCH_CATEGORICAL_COLUMNS,
        prefix_sep="=",
    )

    feature_frame = pd.concat([numeric_features, categorical_features], axis=1)
    feature_frame = feature_frame.reindex(columns=schema["feature_names"], fill_value=0)
    feature_matrix = feature_frame.to_numpy(dtype=np.float64)
    return (feature_matrix - schema["means"]) / schema["stds"]


def save_catch_model(model_path, weights, schema, metadata):
    model_path = Path(model_path)
    np.savez_compressed(
        model_path,
        weights=weights,
        feature_names=schema["feature_names"],
        numeric_medians=schema["numeric_medians"],
        means=schema["means"],
        stds=schema["stds"],
        metadata=np.array(json.dumps(metadata)),
    )


def load_catch_model(model_path):
    model_path = Path(model_path)
    if not model_path.exists():
        return None

    loaded = np.load(model_path, allow_pickle=False)
    metadata = json.loads(str(loaded["metadata"]))
    schema = {
        "feature_names": loaded["feature_names"].astype(str),
        "numeric_medians": loaded["numeric_medians"],
        "means": loaded["means"],
        "stds": loaded["stds"],
    }
    return {
        "weights": loaded["weights"],
        "schema": schema,
        "metadata": metadata,
    }


def train_catch_model_from_data(training_data):
    train_batted_balls = prepare_catch_probability_data(training_data)
    return train_catch_model_from_prepared_data(train_batted_balls)


def train_catch_model_from_prepared_data(train_batted_balls):
    if train_batted_balls.empty:
        raise ValueError("No qualifying batted balls found for catch-model training.")

    features, schema = fit_catch_feature_matrix(train_batted_balls)
    labels = train_batted_balls["is_catch_out"].to_numpy(dtype=float)
    weights = train_logistic_regression(
        features,
        labels,
        iterations=2500,
        learning_rate=0.05,
    )
    if weights is None:
        raise ValueError("Catch-model training data needs both catch outs and non-outs.")

    return weights, schema, train_batted_balls


def fetch_catch_training_data_in_chunks(start, end, chunk_days):
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    chunks = []
    current = start_date

    while current <= end_date:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end_date)
        print(f"Fetching training chunk {current} through {chunk_end}...")
        chunk = statcast(start_dt=current.isoformat(), end_dt=chunk_end.isoformat())
        if not chunk.empty:
            prepared = prepare_catch_probability_data(clean_statcast_data(chunk))
            if not prepared.empty:
                chunks.append(prepared)
        current = chunk_end + timedelta(days=1)

    if not chunks:
        return pd.DataFrame()

    return pd.concat(chunks, ignore_index=True)


def train_and_save_catch_model(start, end, chunk_days, model_path):
    validate_catch_training_dates(start, end)
    train_batted_balls = fetch_catch_training_data_in_chunks(start, end, chunk_days)
    weights, schema, train_batted_balls = train_catch_model_from_prepared_data(
        train_batted_balls
    )
    metadata = {
        "version": CATCH_MODEL_VERSION,
        "trained_start": start,
        "trained_end": end,
        "training_rows": int(len(train_batted_balls)),
        "catch_out_rate": float(train_batted_balls["is_catch_out"].mean()),
        "feature_count": int(len(schema["feature_names"])),
    }
    save_catch_model(model_path, weights, schema, metadata)
    return metadata


def catch_probability_features(train_data, predict_data):
    required_columns = [
        "events",
        "bb_type",
        "launch_speed",
        "launch_angle",
        "hit_distance_sc",
        "estimated_wall_distance",
        "distance_to_wall",
        "park_lf",
        "park_lc",
        "park_cf",
        "park_rc",
        "park_rf",
        "hc_y",
        "estimated_ba_using_speedangle",
        "estimated_woba_using_speedangle",
        "estimated_slg_using_speedangle",
        "if_fielding_alignment",
        "of_fielding_alignment",
        "home_team",
        "stand",
        "p_throws",
    ]
    missing_columns = [column for column in required_columns if column not in train_data.columns]
    if missing_columns:
        raise ValueError(f"Missing columns for catch model: {missing_columns}")

    numeric_columns = [
        "launch_speed",
        "launch_angle",
        "hit_distance_sc",
        "hc_x",
        "hc_y",
        "estimated_ba_using_speedangle",
        "estimated_woba_using_speedangle",
        "estimated_slg_using_speedangle",
        "estimated_wall_distance",
        "distance_to_wall",
        "park_lf",
        "park_lc",
        "park_cf",
        "park_rc",
        "park_rf",
    ]
    categorical_columns = [
        "bb_type",
        "hit_location",
        "if_fielding_alignment",
        "of_fielding_alignment",
        "home_team",
        "stand",
        "p_throws",
    ]

    combined = pd.concat(
        [train_data[numeric_columns + categorical_columns], predict_data[numeric_columns + categorical_columns]],
        axis=0,
        ignore_index=True,
    )
    numeric_features = combined[numeric_columns].apply(pd.to_numeric, errors="coerce")
    numeric_features = numeric_features.fillna(numeric_features.median(numeric_only=True))
    numeric_features = numeric_features.fillna(0)
    categorical_values = combined[categorical_columns].astype("object")
    categorical_features = pd.get_dummies(
        categorical_values.where(pd.notna(categorical_values), "unknown").astype(str),
        columns=categorical_columns,
    )
    features = pd.concat([numeric_features, categorical_features], axis=1)
    feature_matrix = features.to_numpy(dtype=np.float64)

    train_count = len(train_data)
    train_features = feature_matrix[:train_count]
    predict_features = feature_matrix[train_count:]

    means = train_features.mean(axis=0)
    stds = train_features.std(axis=0)
    stds[stds == 0] = 1
    return (train_features - means) / stds, (predict_features - means) / stds


def train_logistic_regression(features, labels, iterations=1200, learning_rate=0.08):
    if len(np.unique(labels)) < 2:
        return None

    features = np.column_stack([np.ones(len(features)), features])
    weights = np.zeros(features.shape[1])
    labels = labels.astype(np.float64)

    for _ in range(iterations):
        logits = np.clip(features @ weights, -30, 30)
        probabilities = 1 / (1 + np.exp(-logits))
        gradient = features.T @ (probabilities - labels) / len(labels)
        weights -= learning_rate * gradient

    return weights


def predict_logistic_regression(features, weights):
    features = np.column_stack([np.ones(len(features)), features])
    logits = np.clip(features @ weights, -30, 30)
    return 1 / (1 + np.exp(-logits))


def best_defensive_play_candidate(day_data, training_data=None, catch_model=None):
    day_batted_balls = prepare_catch_probability_data(day_data)
    candidates = day_batted_balls[
        day_batted_balls["is_catch_out"]
        & day_batted_balls["hit_location"].isin([7, 8, 9])
    ].copy()

    if candidates.empty:
        return None

    if catch_model is not None:
        candidate_features = transform_catch_feature_matrix(
            candidates,
            catch_model["schema"],
        )
        candidates["catch_probability"] = predict_logistic_regression(
            candidate_features,
            catch_model["weights"],
        )
        best_row = candidates.loc[candidates["catch_probability"].idxmin()].copy()
        best_row["catch_training_rows"] = catch_model["metadata"].get("training_rows", 0)
        return best_row

    train_batted_balls = prepare_catch_probability_data(training_data)
    if train_batted_balls.empty:
        return None

    train_features, candidate_features = catch_probability_features(
        train_batted_balls, candidates
    )
    labels = train_batted_balls["is_catch_out"].to_numpy(dtype=float)
    weights = train_logistic_regression(train_features, labels)
    if weights is None:
        return None

    candidates["catch_probability"] = predict_logistic_regression(
        candidate_features, weights
    )
    best_row = candidates.loc[candidates["catch_probability"].idxmin()].copy()
    best_row["catch_training_rows"] = len(train_batted_balls)
    return best_row


def main():
    args = parse_args()
    if args.train_catch_model:
        catch_train_start = args.catch_train_start or "2023-03-30"
        catch_train_end = args.catch_train_end or args.end
        metadata = train_and_save_catch_model(
            catch_train_start,
            catch_train_end,
            args.catch_train_chunk_days,
            args.catch_model_path,
        )
        print(f"Saved catch-probability model to {args.catch_model_path}")
        print(
            "Training summary: "
            f"{metadata['training_rows']} batted balls, "
            f"{metadata['feature_count']} features, "
            f"{metadata['catch_out_rate']:.1%} catch-out rate"
        )
        return

    catch_model = load_catch_model(args.catch_model_path)
    catch_train_start = args.catch_train_start or args.start
    catch_train_end = args.catch_train_end or args.end
    validate_catch_training_dates(catch_train_start, catch_train_end)

    print(f"Fetching Statcast data from {args.start} through {args.end}...")
    data = clean_statcast_data(statcast(start_dt=args.start, end_dt=args.end))
    if catch_model is not None:
        catch_training_data = None
        metadata = catch_model["metadata"]
        print(
            "Loaded catch-probability model from "
            f"{args.catch_model_path} "
            f"({metadata.get('training_rows', 0)} training rows, "
            f"{metadata.get('trained_start')} to {metadata.get('trained_end')})"
        )
    elif catch_train_start == args.start and catch_train_end == args.end:
        catch_training_data = data
    else:
        print(
            "Fetching catch-probability training data from "
            f"{catch_train_start} through {catch_train_end}..."
        )
        catch_training_data = clean_statcast_data(
            statcast(start_dt=catch_train_start, end_dt=catch_train_end)
        )

    if data.empty:
        print("No Statcast data found for that date range.")
        return

    batter_names = get_batter_names(data)
    pitcher_names = get_pitcher_names(data)
    completed_plays = data[data["events"].notna()]
    videoable_plays = completed_plays[
        completed_plays["events"].map(HIT_RESULT_BY_EVENT).notna()
    ]
    pitches = data[data["pitcher"].notna()]
    pitches = pitches.assign(
        horizontal_break_inches=pitches["api_break_x_arm"] * 12,
        ivb_inches=pitches["pfx_z"] * 12,
    )

    win_exp_row = row_with_largest_abs_value(videoable_plays, "delta_home_win_exp")
    hardest_hit_row = row_with_largest_value(videoable_plays, "launch_speed")
    farthest_hit_row = row_with_largest_value(videoable_plays, "hit_distance_sc")
    hardest_pitch_row = row_with_largest_value(pitches, "release_speed")
    horizontal_break_row = row_with_largest_abs_value(pitches, "horizontal_break_inches")
    vertical_drop_row = row_with_smallest_value(pitches, "ivb_inches")
    vertical_rise_row = row_with_largest_value(pitches, "ivb_inches")
    defensive_play_row = best_defensive_play_candidate(
        data,
        training_data=catch_training_data,
        catch_model=catch_model,
    )

    print_win_exp_result(
        "Biggest swing in win expectancy",
        win_exp_row,
        batter_names,
        pitcher_names,
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
    print_pitch_result(
        "Hardest-thrown pitch",
        hardest_pitch_row,
        pitcher_names,
        lambda row: f"{format_value(row.get('release_speed'), ' mph', 1)} velocity",
    )
    print_pitch_result(
        "Pitch with most horizontal break",
        horizontal_break_row,
        pitcher_names,
        lambda row: f"{format_value(abs(row.get('horizontal_break_inches')), ' in', 1)} horizontal break",
    )
    print_pitch_result(
        "Pitch with most vertical drop",
        vertical_drop_row,
        pitcher_names,
        lambda row: f"{format_value(row.get('ivb_inches'), ' in', 1)} IVB",
    )
    print_pitch_result(
        "Pitch with most vertical rise",
        vertical_rise_row,
        pitcher_names,
        lambda row: f"{format_value(row.get('ivb_inches'), ' in', 1)} IVB",
    )
    print_defensive_result(
        "Lowest catch-probability defensive play",
        defensive_play_row,
        batter_names,
        lambda row: (
            f"{format_value(row.get('catch_probability') * 100, '%', 1)} model catch probability; "
            f"trained on {int(row.get('catch_training_rows'))} balls in play; "
            f"{format_value(row.get('hit_distance_sc'), ' ft', 0)}, "
            f"{format_value(row.get('launch_speed'), ' mph', 1)}, "
            f"{format_value(row.get('launch_angle'), ' deg', 0)} LA, "
            f"{format_value(row.get('distance_to_wall'), ' ft to wall', 0)}"
        ),
    )


if __name__ == "__main__":
    main()
