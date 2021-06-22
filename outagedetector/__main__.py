from outagedetector import initial_config as config
from outagedetector import outage_detector as outage

import argparse


def main(sysargv=None):
    parser = argparse.ArgumentParser(description="Find out internet or power outage downtime!")
    parser.add_argument('--init', dest='init', help='Meant for first run only', action='store_true')
    parser.add_argument('--help', help='Show help')
    args = parser.parse_args()

    if not args.help:
        if args.init:
            config.initialize()
        else:
            outage.check_power_and_internet(args.run, args.notify)


if __name__ == "__main__":
    main()
