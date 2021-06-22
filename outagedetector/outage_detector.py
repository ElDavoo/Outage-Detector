from datetime import datetime
import json
import os
import socket
import traceback
from time import sleep

import keyring

from outagedetector import send_mail as mail

import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds


def check_link():
    try:
        sock = socket.create_connection(
            ("www.google.com", 80))  # if connection to google fails, we assume internet is down
        sock.close()
        return True
    except OSError:
        pass
    return False


def check_tcp():
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

    link_working = check_link()
    tcp_working = check_tcp()

    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds']
    try:
        with open(os.path.join(config_path, "config.json")) as json_file:
            config = json.load(json_file)
            google = config["google"]
            mail_enabled = config["mail"]
            timeout = config["timeout"]
            # ???
            if mail_enabled:
                sender = config["mail_sender"]
                receivers = config["mail_receivers"]
                smtp_server = config["mail_smtp_server"]
                password = keyring.get_password("Mail-OutageDetector", sender)
                if password is None:
                    print("Mail password not found, try running initial configuration again!")
                    exit(1)
            if google:
                creds = ServiceAccountCredentials.from_json_keyfile_name(
                    os.path.join(config_path, "client_secret.json"), scope)
                client = gspread.authorize(creds)
                sheet = client.open_by_key(config["google_doc"])

    except FileNotFoundError:
        print(os.path.join(config_path, "config.json") + " does not exist!")
        exit(1)
    except KeyError:
        print("Configuration error:")
        traceback.print_exc()
        exit(1)

    while True:

        # we get the current time.
        current_timestamp = datetime.now()
        current_timestring = datetime.strftime(current_timestamp, timestamp_format)
        current_hour_min = datetime.strftime(current_timestamp, hour_minute_format)

        # we get the ast written timestamp.
        try:
            with open(os.path.join(tmp_path, "last_timestamp.txt")) as file:
                read_string = file.read()
        except FileNotFoundError:
            read_string = ""

        file_data = read_string.split(",")

        try:
            last_power_timestring = file_data[0]
            last_internet_timestring = file_data[1]
        except IndexError:
            last_power_timestring = current_timestring
            last_internet_timestring = current_timestring

        last_power_timestamp = datetime.strptime(last_power_timestring, timestamp_format)

        with open(os.path.join(tmp_path, "last_timestamp.txt"), 'w+') as file:
            if link_working:
                file.write("{},{}".format(current_timestring, current_timestring))
            else:
                file.write("{},{}".format(current_timestring, last_internet_timestring))

        if link_working:
            if just_booted:
                power_outage_time = int((current_timestamp - last_power_timestamp).total_seconds() / 60)
                min_outage_time = 0
                if mail_enabled:
                    notification = "Power was out for {} to {} minutes at {}.".format(min_outage_time,
                                                                                      power_outage_time,
                                                                                      current_hour_min)
                    mail.send_mail(sender, receivers, "Power outage", notification, smtp_server, password)
                if google:
                    sheet.append_row("lol")
                print("Power was out for {} to {} minutes at {}".format(min_outage_time, power_outage_time,
                                                                        current_timestring))

            if not last_power_timestring == last_internet_timestring:
                last_internet_timestamp = datetime.strptime(last_internet_timestring, timestamp_format)
                internet_downtime = int((current_timestamp - last_internet_timestamp).total_seconds() / 60)
                min_outage_time = 0
                print("Internet was down for {} to {} minutes at {}".format(min_outage_time, internet_downtime,
                                                                            current_timestring))
                notification = "Internet has been down for {} to {} minutes at {}.".format(min_outage_time,
                                                                                           internet_downtime,
                                                                                           current_hour_min)
                mail_enabled.send_mail(sender, receivers, "Internet down", notification, smtp_server, password)

        sleep(config["timeout"])
