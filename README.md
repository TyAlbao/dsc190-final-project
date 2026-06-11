# MLB Statcast Highlight Finder

This tool finds the player responsible for the biggest win-expectancy swing, the
hardest-hit ball, and the farthest-hit ball in a Statcast date range. It prints
the matching play details and builds an MLB.com video search link for each play.

## Usage

Run the script with Python and pass a start and end date in `YYYY-MM-DD` format:

```powershell
python main.py --start 2024-04-01 --end 2024-04-01
```

This fetches Statcast data for April 1, 2024 and prints the top play for each
category.

The script also loads `catch_probability_model.npz` automatically when it is
present. That saved model is used to choose the lowest catch-probability
defensive play of the day.

You can also run it without arguments:

```powershell
python main.py
```

By default, the script searches yesterday's games.

If you pass `--start` without `--end`, the script searches only that start date:

```powershell
python main.py --start 2026-05-31
```

To retrain the catch-probability model with post-shift-ban Statcast data and
save it for later runs:

```powershell
python main.py --train-catch-model --catch-train-start 2023-03-30 --catch-train-end 2026-06-10 --catch-model-path catch_probability_model.npz
```

Training uses 14-day Statcast chunks by default. You can change that chunk size:

```powershell
python main.py --train-catch-model --catch-train-start 2023-03-30 --catch-train-end 2026-06-10 --catch-train-chunk-days 7
```
