# selenium-grid-exporter
Export Selenium Grid (v4) metrics to Prometheus

# Usage
```
$ python ./exporter.py --help
usage: exporter.py [-h] [-g GRID_URL] [-p METRICS_PORT] [-i PUBLISH_INTERVAL] [-w WAIT] [-l {debug,info,warning,error,critical}]

Process some integers.

optional arguments:
  -h, --help            show this help message and exit
  -g GRID_URL, --grid-url GRID_URL
                        the grid URL with port
  -p METRICS_PORT, --metrics-port METRICS_PORT
                        port where the metrics will be published
  -i PUBLISH_INTERVAL, --publish-interval PUBLISH_INTERVAL
                        how frequent (in seconds) metrics are generated
  -w WAIT, --wait WAIT  how long to wait for grid to initialize before polling starts
  -l {debug,info,warning,error,critical}, --log-level {debug,info,warning,error,critical}
                        set the logging level


```

# Metrics
Sample scrape output:
```
# HELP selenium_grid_total_slots Total number of slots in the grid
# TYPE selenium_grid_total_slots gauge
selenium_grid_total_slots 4.0
# HELP selenium_grid_node_count Number of nodes in grid
# TYPE selenium_grid_node_count gauge
selenium_grid_node_count 4.0
# HELP selenium_grid_session_count Number of running sessions
# TYPE selenium_grid_session_count gauge
selenium_grid_session_count 0.0
# HELP selenium_grid_session_queue_size Number of queued sessions
# TYPE selenium_grid_session_queue_size gauge
selenium_grid_session_queue_size 0.0
# HELP selenium_node_slot_count Total number of node slots
# TYPE selenium_node_slot_count gauge
selenium_node_slot_count{deployment="selenium-node-chrome",node="chrome"} 3.0
selenium_node_slot_count{deployment="selenium-node-firefox",node="firefox"} 1.0
# HELP selenium_node_session_count Total number of node slots
# TYPE selenium_node_session_count gauge
selenium_node_session_count{deployment="selenium-node-chrome",node="chrome"} 0.0
selenium_node_session_count{deployment="selenium-node-firefox",node="firefox"} 0.0
# HELP selenium_node_usage_percent % of used node slots
# TYPE selenium_node_usage_percent gauge
selenium_node_usage_percent{deployment="selenium-node-chrome",node="chrome"} 0.0
selenium_node_usage_percent{deployment="selenium-node-firefox",node="firefox"} 0.0
```
