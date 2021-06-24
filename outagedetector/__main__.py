from outagedetector import initial_config as config
from outagedetector import outage_detector as outage

import argparse


def main():
    parser = argparse.ArgumentParser(description="Find out internet or power outage downtime!")
    parser.add_argument('--init', dest='init', help='Meant for first run only', action='store_true')
    args = parser.parse_args()

    if args.init:
        config.initialize()
    else:
        outage.init()


if __name__ == "__main__":
    main()
