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
GRID_TOTAL_SLOTS = Gauge('selenium_grid_total_slots', 'Total number of slots in the grid')
GRID_NODE_COUNT = Gauge('selenium_grid_node_count', 'Number of nodes in grid')
GRID_SESSION_COUNT = Gauge('selenium_grid_session_count', 'Number of running sessions')
GRID_SESSION_QUEUE_SIZE = Gauge('selenium_grid_session_queue_size', 'Number of queued sessions')

# node metrics
NODE_SLOT_COUNT = Gauge('selenium_node_slot_count', 'Total number of node slots', labelnames=['node', 'deployment'])
NODE_SESSION_COUNT = Gauge('selenium_node_session_count', 'Total number of node slots',
                           labelnames=['node', 'deployment'])
NODE_USAGE_PERCENT = Gauge('selenium_node_usage_percent', '% of used node slots', labelnames=['node', 'deployment'])

# supported browsers
BROWSERS = ['chrome', 'firefox']


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
    GRID_TOTAL_SLOTS.set(data['totalSlots'])
    GRID_NODE_COUNT.set(data['nodeCount'])
    GRID_SESSION_COUNT.set(data['sessionCount'])
    GRID_SESSION_QUEUE_SIZE.set(data['sessionQueueSize'])


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

    # publish available browser metrics
    for browser in BROWSERS:
        logging.debug(f'Publishing {browser.capitalize()} metrics')
        NODE_SLOT_COUNT.labels(browser, f'selenium-node-{browser}').set(all_nodes[browser]['slot_count'])
        NODE_SESSION_COUNT.labels(browser, f'selenium-node-{browser}').set(all_nodes[browser]['session_count'])
        if all_nodes[browser]['slot_count'] > 0:
            browser_usage_percent = (all_nodes[browser]['session_count'] / all_nodes[browser]['slot_count']) * 100
        else:
            browser_usage_percent = 0
        NODE_USAGE_PERCENT.labels(browser, f'selenium-node-{browser}').set(browser_usage_percent)


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
