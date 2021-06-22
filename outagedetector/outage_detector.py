from datetime import datetime
import json
import os
from pathlib import Path
import socket
import traceback

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


# if power is on, script will run even if internet is down, therefore we only take into account the power timestamp
# from the last run in determining the periodicity of the script runs
def extract_run_periodicity(scheduled_now, last_scheduled, current_time, last_power_time, last_period):
    if scheduled_now == "scheduled" and last_scheduled == "scheduled":
        return int((current_time - last_power_time).total_seconds() / 60)
    else:
        return last_period


def check_power_and_internet():
    just_booted = True

    config_path = os.path.join(os.path.expanduser("~"), ".config/outagedetector")
    tmp_path = os.path.realpath("/tmp/")
    timestamp_format = "%d-%m-%Y %H-%M-%S"
    hour_minute_format = "%H:%M"

    link_working = check_link()
    tcp_working = check_tcp()

    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds']
    creds = ServiceAccountCredentials.from_json_keyfile_name(os.path.join(config_path, "client_secret.json"), scope)
    client = gspread.authorize(creds)

    # Find a workbook by name and open the first sheet
    # Make sure you use the right name here.
    sheet = client.open("Monitoraggio uptime").sheet1

    sheet.append_row("lol")

    try:
        with open(os.path.join(config_path, "config.json")) as json_file:
            config = json.load(json_file)
            sender = config["mail_sender"]
            receivers = config["mail_receivers"]
            smtp_server = config["mail_smtp_server"]
            password = keyring.get_password("Mail-OutageDetector", sender)
            if password is None:
                print("Mail password not found, try running initial configuration again!")
                exit(1)

    except FileNotFoundError:
        print(os.path.join(config_path, "config.json") + " does not exist!")
        exit(1)
    except KeyError:
        print("Configuration error:")
        traceback.print_exc()
        exit(1)

    if not send_notification:
        try:
            with open(os.path.join(config_path, "config.json")) as json_file:
                config = json.load(json_file)
                sender = config["sender"]
                receivers = config["receivers"]
                smtp_server = config["smtp_server"]
                password = keyring.get_password("Mail-OutageDetector", sender)
                if password is None:
                    print("Mail password not found, try running initial configuration again!")
                    exit(1)

        except FileNotFoundError:
            print("Mail will not be sent, there is no config file in the folder.")
        except KeyError:
            print("Config.json file doesn't have all fields (sender, receivers, smtp_server")


    current_timestamp = datetime.now()
    current_timestring = datetime.strftime(current_timestamp, timestamp_format)
    current_hour_min = datetime.strftime(current_timestamp, hour_minute_format)

    try:
        with open(os.path.join(config_path, "last_timestamp.txt")) as file:
            read_string = file.read()
    except FileNotFoundError:
        read_string = ""

    file_data = read_string.split(",")

    try:
        last_power_timestring = file_data[0]
        last_internet_timestring = file_data[1]
        last_argument = file_data[2]
        last_periodicity = int(file_data[3])
    except IndexError:
        last_power_timestring = current_timestring
        last_internet_timestring = current_timestring
        last_argument = "N/A"
        last_periodicity = 0

    last_power_timestamp = datetime.strptime(last_power_timestring, timestamp_format)

    periodicity = extract_run_periodicity(run,
                                          last_argument,
                                          current_timestamp,
                                          last_power_timestamp,
                                          last_periodicity)

    with open(os.path.join(config_path, "last_timestamp.txt"), 'w+') as file:
        if link_working:
            file.write("{},{},{},{}".format(current_timestring, current_timestring, run, periodicity))
        else:
            file.write("{},{},{},{}".format(current_timestring, last_internet_timestring, run, periodicity))

    if link_working:
        if just_booted:
            power_outage_time = int((current_timestamp - last_power_timestamp).total_seconds() / 60)
            if periodicity > 0:
                min_outage_time = max(range(0, power_outage_time + 1, periodicity))
            else:
                min_outage_time = 0
            notification = "Power was out for {} to {} minutes at {}.".format(min_outage_time, power_outage_time,
                                                                              current_hour_min)
            print("Power was out for {} to {} minutes at {}".format(min_outage_time, power_outage_time,
                                                                    current_timestring))
            if not send_notification:
                mail.send_mail(sender, receivers, "Power outage", notification, smtp_server, password)

        if not last_power_timestring == last_internet_timestring:
            last_internet_timestamp = datetime.strptime(last_internet_timestring, timestamp_format)
            internet_downtime = int((current_timestamp - last_internet_timestamp).total_seconds() / 60)
            if periodicity > 0:
                min_outage_time = max(range(0, internet_downtime + 1, periodicity))
            else:
                min_outage_time = 0
            print("Internet was down for {} to {} minutes at {}".format(min_outage_time, internet_downtime,
                                                                        current_timestring))
            notification = "Internet has been down for {} to {} minutes at {}.".format(min_outage_time,
                                                                                       internet_downtime,
                                                                                       current_hour_min)
            mail.send_mail(sender, receivers, "Internet down", notification, smtp_server, password)

    print("Script has run at {}. Internet connected: {}. Just booted: {}.".format(current_timestring,
                                                                                  link_working,
                                                                                  just_booted))


def google():
