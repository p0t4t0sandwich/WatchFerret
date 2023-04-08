# WatchFerret

Credit to sneakysnek#8707 for thinking of the name

## Getting Started

Downloading files:

`wget --no-check-certificate --content-disposition https://raw.githubusercontent.com/p0t4t0sandwich/WatchFerret/main/watchferret/WatchFerret.py`

`wget --no-check-certificate --content-disposition https://raw.githubusercontent.com/p0t4t0sandwich/WatchFerret/main/watchferret/config.yml`

Installing dependencies:

`python -m pip install ampapi requests aiohttp pyyaml`

Running the program:

`python WatchFerret.py`

## How to find `Instance Name`

You can find the instance's name by running `ampinstmgr status` in your CLI/SSH window, or on the right hand side of the AMP web ui when selecting an instance.

## How to find `Instance ID`

You can find the instance's ID by right clicking on the instance in the AMP web ui, and selecting `Manage in New Tab`. The ID will be in the URL after `?instance=`.

## Example Config

```yaml
---
# Global default config for instance management.
global:
  # The address to your AMP instance web port.
  host: "http://localhost:8080"
  username: "username"
  password: "password"
  # Path to logs
  logging_path: "./"
  # Time in seconds for how often you want to ping the server.
  sample_interval: 300
  # Average rescue threshold in minutes: INTERVAL*THRESHOLD/60 (plus or minus ~0.95*INTERVAL/60).
  # How many pings during a server restart before rescuing the server.
  restart_threshold: 2
  # How many pings during a server start before rescuing the server.
  start_threshold: -1
  # How many pings during a server stop before rescuing the server.
  stop_threshold: -1

# Instances are identified using the instance name listed in the AMP web ui.
instances:
  Lobby: # <- Doesn't have to be the same as the instance name, but it's recommended for sanity's sake.
    name: Lobby01
  # Any entry listed here will override the global config, and any unspecified entries will be pulled from the global config.
  CoolSMP:
    name: CoolSMP01
    id: 9jhb9t6
    start_threshold: 3
```
