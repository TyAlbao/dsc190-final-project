# MLB Statcast Highlight Finder

This command-line tool pulls MLB Statcast data for a date or date range and
prints a readable daily highlight report. It finds notable games, hitter
performances, pitcher performances, pitch-level extremes, and the lowest
catch-probability defensive play, then includes specific MLB Film Room search
links for play-level highlights.

## Usage

Run a single day:

```powershell
python main.py --start 2026-05-31
```

When `--end` is omitted, it defaults to the same date as `--start`.

Run a date range:

```powershell
python main.py --start 2026-05-31 --end 2026-06-09
```

Run yesterday's games:

```powershell
python main.py
```

## Expected Output

The report is split into four sections:

- `Games`: biggest win-expectancy swing, most lead changes, most/fewest
  total runs, and most/fewest total hits.
- `Hitters`: best overall hitter game by game wOBA, hardest-hit ball, and
  farthest-hit ball.
- `Pitchers`: best and worst pitcher games by wOBA allowed, most strikeouts,
  hardest-thrown pitch, most horizontal break, most vertical drop, and most
  vertical rise.
- `Defense`: successful defensive play made with the lowest catch-probability using the saved model.

Play-level entries include game context, player/team info, the key metric, a
play description, and an MLB Film Room search link.

## Catch-Probability Model

If `catch_probability_model.npz` exists, the script loads it automatically for
the defensive section. The included model was trained on post-shift-ban Statcast
data from `2023-03-30` through `2026-06-10`.

Retrain and save the model:

```powershell
python main.py --train-catch-model --catch-train-start 2023-03-30 --catch-train-end 2026-06-10 --catch-model-path catch_probability_model.npz
```

Training uses 14-day Statcast chunks by default. To change the chunk size:

```powershell
python main.py --train-catch-model --catch-train-start 2023-03-30 --catch-train-end 2026-06-10 --catch-train-chunk-days 7
```

## Notes

All summary stats are calculated from Statcast data so the numbers stay
consistent with the play-level records and Film Room links.
