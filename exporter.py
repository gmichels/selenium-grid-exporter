#!/usr/bin/env python
"""Selenium Grid (v4) Metrics Exporter"""
import argparse
import json
import logging
import sys
import time

import requests
from prometheus_client import Gauge, start_http_server

# grid metrics
SELENIUM_GRID_TOTAL_SLOTS = Gauge('grid_total_slots', 'Total number of slots in the grid')
SELENIUM_GRID_NODE_COUNT = Gauge('grid_node_count', 'Number of nodes in grid')
SELENIUM_GRID_SESSION_COUNT = Gauge('grid_session_count', 'Number of running sessions')
SELENIUM_GRID_SESSION_QUEUE_SIZE = Gauge('grid_session_queue_size', 'Number of queued sessions')

# supported browsers
BROWSERS = ['chrome', 'firefox', 'edge', 'opera']
# node metrics
for entry in BROWSERS:
    # dynamically create metric container for each browser
    globals()[f'SELENIUM_NODE_SLOT_COUNT_{entry.upper()}'] = Gauge(f'selenium_node_slot_count_{entry}',
                                                                   f'Total number of {entry.capitalize()} slots')
    globals()[f'SELENIUM_NODE_SESSION_COUNT_{entry.upper()}'] = Gauge(f'selenium_node_session_count_{entry}',
                                                                      f'Total number of {entry.capitalize()} slots')


def process_metrics() -> None:
    """
    Entry point to retrieve the stats from the grid and invoke the metric generation methods
    """
    req_body = {'query': '{ grid {totalSlots, nodeCount, sessionCount, sessionQueueSize},'
                         ' nodesInfo { nodes { slotCount, sessionCount, stereotypes } } ''}'}
    resp = requests.post(f'{args.grid_url}/graphql', data=json.dumps(req_body))
    if resp.status_code == 200:
        resp_body = resp.json()
        # generate the grid metrics
        generate_grid_metrics(resp_body['data']['grid'])
        # generate the node metrics
        generate_node_metrics(resp_body['data']['nodesInfo']['nodes'])
    else:
        logging.warning(f'Unable to retrieve metrics from the grid (response status code {resp.status_code})')


def generate_grid_metrics(data: dict) -> None:
    """
    Parse the grid data from the stats response and set the Prometheus gauges

    :param data: the grid data dict
    """
    logging.debug('Publishing Grid metrics')
    SELENIUM_GRID_TOTAL_SLOTS.set(data['totalSlots'])
    SELENIUM_GRID_NODE_COUNT.set(data['nodeCount'])
    SELENIUM_GRID_SESSION_COUNT.set(data['sessionCount'])
    SELENIUM_GRID_SESSION_QUEUE_SIZE.set(data['sessionQueueSize'])


def generate_node_metrics(data: dict) -> None:
    """
    Parse the node data from the stats response and set the Prometheus gauges

    :param data: the nodesInfo:nodes data dict
    """
    # initialize stats
    node_stats = {'slot_count': 0, 'session_count': 0}
    all_nodes = dict()
    for browser in BROWSERS:
        all_nodes.update({browser: node_stats.copy()})

    # generate the consolidated information about all nodes
    for node in data:
        browser = json.loads(node['stereotypes'])[0]['stereotype']['browserName']
        all_nodes[browser]['slot_count'] += node['slotCount']
        all_nodes[browser]['session_count'] += node['sessionCount']

    # publish browser metrics
    for browser in BROWSERS:
        logging.debug(f'Publishing {browser.capitalize()} metrics')
        globals()[f'SELENIUM_NODE_SLOT_COUNT_{browser.upper()}'].set(all_nodes[browser]['slot_count'])
        globals()[f'SELENIUM_NODE_SESSION_COUNT_{browser.upper()}'].set(all_nodes[browser]['session_count'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-g', '--grid-url', type=str, default='http://localhost:4444', help='the grid URL with port')
    parser.add_argument('-p', '--metrics-port', type=int, default=8000, help='port where the metrics will be published')
    parser.add_argument('-i', '--publish-interval', type=int, default=30,
                        help='how frequent (in seconds) metrics are generated')
    parser.add_argument('-w', '--wait', type=int, default=15,
                        help='how long to wait for grid to initialize before polling starts')
    parser.add_argument('-l', '--log-level', type=str, default='info',
                        choices=['debug', 'info', 'warning', 'error', 'critical'], help='set the logging level')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s --- %(levelname)s --- %(message)s',
                        level=getattr(logging, args.log_level.upper()))
    try:
        logging.info(f'Starting Selenium Grid Exporter')
        # start up the server to expose the metrics
        start_http_server(args.metrics_port)
        logging.info(f'Waiting {args.wait} seconds for grid to initialize...')
        time.sleep(args.wait)
        # generate metrics every --publish-interval seconds
        logging.info(f'Metrics will be polled for grid url {args.grid_url} every {args.publish_interval} seconds '
                     f'and available for scraping on port {args.metrics_port}')
        while True:
            process_metrics()
            time.sleep(args.publish_interval)
    except KeyboardInterrupt:
        logging.info('Exiting now')
        sys.exit()
    except Exception:
        logging.error('Unhandled exception', exc_info=True)
