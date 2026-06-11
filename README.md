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

You can also run it without arguments:

```powershell
python main.py
```

By default, the script searches yesterday's games.
