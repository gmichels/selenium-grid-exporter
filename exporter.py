#!/usr/bin/env python
import argparse
import json
import logging
import sys
import time

import requests
from prometheus_client import Gauge, start_http_server

# grid metrics
GRID_TOTAL_SLOTS = Gauge('grid_total_slots', 'Total number of slots in the grid')
GRID_NODE_COUNT = Gauge('grid_node_count', 'Number of nodes in grid')
GRID_SESSION_COUNT = Gauge('grid_session_count', 'Number of running sessions')
GRID_SESSION_QUEUE_SIZE = Gauge('grid_session_queue_size', 'Number of queued sessions')

# node metrics
# chrome
NODE_SLOT_COUNT_CHROME = Gauge('node_slot_count_chrome', 'Total number of Chrome slots')
NODE_SESSION_COUNT_CHROME = Gauge('node_session_count_chrome', 'Number of running Chrome sessions')
# firefox
NODE_SLOT_COUNT_FIREFOX = Gauge('node_slot_count_firefox', 'Total number of Firefox slots')
NODE_SESSION_COUNT_FIREFOX = Gauge('node_session_count_firefox', 'Number of running Firefox sessions')


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


def generate_grid_metrics(data: dict) -> None:
    """
    Parse the grid data from the stats response and set the Prometheus gauges

    :param data: the grid data dict
    """
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
    all_nodes = {'chrome': node_stats.copy(), 'firefox': node_stats.copy()}
    # generate the consolidated information about all nodes
    for node in data:
        browser = json.loads(node['stereotypes'])[0]['stereotype']['browserName']
        all_nodes[browser]['slot_count'] += node['slotCount']
        all_nodes[browser]['session_count'] += node['sessionCount']

    # publish Chrome metrics
    NODE_SLOT_COUNT_CHROME.set(all_nodes['chrome']['slot_count'])
    NODE_SESSION_COUNT_CHROME.set(all_nodes['chrome']['session_count'])
    # publish Firefox metrics
    NODE_SLOT_COUNT_FIREFOX.set(all_nodes['firefox']['slot_count'])
    NODE_SESSION_COUNT_FIREFOX.set(all_nodes['firefox']['session_count'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-g', '--grid-url', type=str, default='http://localhost:4444', help='the grid URL with port')
    parser.add_argument('-p', '--metrics-port', type=int, default=8000, help='port where the metrics will be published')
    parser.add_argument('-i', '--publish-interval', type=int, default=30,
                        help='how frequent (in seconds) metrics are generated')
    parser.add_argument('-w', '--wait', type=int, default=15,
                        help='how long to wait for grid to initialize before polling starts')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s --- %(levelname)s --- %(message)s', level=logging.DEBUG)
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
