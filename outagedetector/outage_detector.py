from datetime import datetime
import json
import os
import socket
import traceback
from time import sleep

import keyring

from outagedetector import send_mail as mail

import gspread


def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds


def check_tcp():
    try:
        sock = socket.create_connection(
            ("www.google.com", 80))  # if connection to google fails, we assume internet is down
        sock.close()
        return True
    except OSError:
        pass
    return False


def check_icmp():
    try:
        hostname = "google.com"  # example
        response = os.system("ping -c 1 " + hostname)
        if response == 0:
            return True
        return False
    except OSError:
        pass
    return False


def loop():
    just_booted = True

    config_path = os.path.join(os.path.expanduser("~"), ".config/outagedetector")
    tmp_path = os.path.realpath("/tmp/")
    timestamp_format = "%d-%m-%Y %H-%M-%S"
    hour_minute_format = "%H:%M"

    try:
        with open(os.path.join(config_path, "config.json")) as json_file:
            config = json.load(json_file)
            google = config["google"]
            mail_enabled = config["mail"]
            timeout = config["timeout"]
            if mail_enabled:
                sender = config["mail_sender"]
                receivers = config["mail_receivers"]
                smtp_server = config["mail_smtp_server"]
                password = keyring.get_password("Mail-OutageDetector", sender)
                if password is None:
                    print("Mail password not found, try running initial configuration again!")
                    exit(1)
            if google:
                client = gspread.service_account(os.path.join(config_path, "client_secret.json"))
                sheet = client.open_by_key(config["google_doc"]).sheet1

    except FileNotFoundError:
        print(os.path.join(config_path, "config.json") + " does not exist!")
        exit(1)
    except KeyError:
        print("Configuration error:")
        traceback.print_exc()
        exit(1)

    while True:

        # we get the current time.
        # {datetime} 2021-06-22 20:51:54.429255
        current_timestamp = datetime.now()
        # {str} '22-06-2021 20-51-54'
        current_timestring = datetime.strftime(current_timestamp, timestamp_format)
        # {str} '20:51'
        current_hour_min = datetime.strftime(current_timestamp, hour_minute_format)

        # we get the last written timestamps.
        try:
            with open(os.path.join(tmp_path, "last_timestamp.txt")) as file:
                read_string = file.read()
        except FileNotFoundError:
            read_string = ""

        file_data = read_string.split(",")

        try:
            last_power_timestring = file_data[0]
            last_tcp_timestring = file_data[1]
            last_icmp_timestring = file_data[2]
        except IndexError:
            last_power_timestring = current_timestring
            last_tcp_timestring = current_timestring
            last_icmp_timestring = current_timestring

        tcp_working = check_tcp()
        icmp_working = check_icmp()

        # logline computation
        value1 = current_timestring
        value2 = current_timestring
        value3 = current_timestring
        if not tcp_working:
            value2 = last_tcp_timestring
        if not icmp_working:
            value3 = last_icmp_timestring
        logline = print("{},{},{}".format(value1, value2, value3))

        # write to logfile
        with open(os.path.join(tmp_path, "last_timestamp.txt"), 'w+') as file:
            file.write(logline)

        if just_booted:
            # We assume power is gone
            power_outage_time = int(
                (current_timestamp - datetime.strptime(last_power_timestring, timestamp_format)).total_seconds() / 60)
            min_outage_time = 0
            if power_outage_time > min_outage_time:
                if mail_enabled:
                    notification = "Power was out for {} to {} minutes at {}.".format(power_outage_time,
                                                                                      current_hour_min)
                    mail.send_mail(sender, receivers, "Power outage", notification, smtp_server, password)
                if google:
                    # sheet.append_row("lol")
                print("Power was out for {} minutes at {}".format(power_outage_time, current_timestring))

        elif last_power_timestring == last_internet_timestring:
            last_internet_timestamp = datetime.strptime(last_internet_timestring, timestamp_format)
            internet_downtime = int((current_timestamp - last_internet_timestamp).total_seconds() / 60)
            min_outage_time = 0
            print("Internet was down for {} to {} minutes at {}".format(min_outage_time, internet_downtime,
                                                                        current_timestring))
            notification = "Internet has been down for {} to {} minutes at {}.".format(min_outage_time,
                                                                                       internet_downtime,
                                                                                       current_hour_min)
            mail_enabled.send_mail(sender, receivers, "Internet down", notification, smtp_server, password)

        sleep(int(config["timeout"]))
