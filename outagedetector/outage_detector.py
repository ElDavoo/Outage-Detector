import json
import os
import platform  # For getting the operating system name
import socket
import subprocess  # For executing a shell command
import traceback
from datetime import datetime
from time import sleep

import keyring

from outagedetector.google_sheets import GSheet
from outagedetector.notifications import Notifications
from outagedetector.send_mail import Mail


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
        # Option for the number of packets as a function of
        param = '-n' if platform.system().lower() == 'windows' else '-c'

        # Building the command. Ex: "ping -c 1 google.com"
        command = ['ping', param, '1', 'google.com']

        return subprocess.call(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL) == 0
    except OSError:
        pass
    return False


def init():
    config_path = os.path.join(os.path.expanduser("~"), ".config/outagedetector")

    try:
        with open(os.path.join(config_path, "config.json")) as json_file:
            config = json.load(json_file)
            google = config["google"]
            mail_enabled = config["mail"]
            mail = None
            sheet = None
            if mail_enabled:
                port = config["mail_port"]
                sender = config["mail_sender"]
                receivers = config["mail_receivers"]
                smtp_server = config["mail_smtp_server"]
                password = config["mail_password"]
                if password is None:
                    print("Mail password not found, try running initial configuration again!")
                    exit(1)
                mail = Mail(sender, receivers, smtp_server, password, port)

            if google:
                config_file = os.path.join(config_path, "client_secret.json")
                google_doc = config["google_doc"]
                sheet = GSheet(config_file, google_doc)
            notification = Notifications(mail, sheet)

            timeout = int(config["timeout"])
    except FileNotFoundError:
        print(os.path.join(config_path, "config.json") + " does not exist!")
        exit(1)
    except KeyError:
        print("Configuration error:")
        traceback.print_exc()
        exit(1)
    print("Started up.")
    loop(notification, timeout)


def loop(notification, timeout):
    timestamp_format = "%d-%m-%Y %H-%M-%S"
    hour_minute_format = "%H:%M"
    tmp_path = os.path.realpath("/tmp/")
    just_booted = True
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
        logline = "{},{},{}".format(value1, value2, value3)

        # write to logfile
        with open(os.path.join(tmp_path, "last_timestamp.txt"), 'w+') as file:
            file.write(logline)

        if just_booted:
            # We assume power is gone
            power_outage_time = int(
                (current_timestamp - datetime.strptime(last_power_timestring, timestamp_format)).total_seconds() / 60)
            min_outage_time = 0
            if power_outage_time > min_outage_time:
                body = "Power was out for {} minutes until {}.".format(power_outage_time, current_hour_min)
                post = "{},{},{}".format("POWER", power_outage_time, current_timestring)
                notification.send("Power outage", body)
                notification.send(None, post)
                print(body)
            just_booted = False
        else:
            if last_tcp_timestring != current_timestring:
                # TCP has been down or is down
                last_tcp_timestamp = datetime.strptime(last_tcp_timestring, timestamp_format)
                tcp_downtime = int((current_timestamp - last_tcp_timestamp).total_seconds() / 60)
                min_outage_time = 0
                if tcp_downtime > min_outage_time and check_tcp():
                    body = "TCP was out for {} minutes until {}.".format(tcp_downtime, current_hour_min)
                    post = "{},{},{}".format("TCP", tcp_downtime, current_timestring)
                    notification.send("TCP outage", body)
                    notification.send(None, post)
                    print(body)
            if last_icmp_timestring != current_timestring:
                # ICMP has been down or is down
                last_icmp_timestamp = datetime.strptime(last_icmp_timestring, timestamp_format)
                icmp_downtime = int((current_timestamp - last_icmp_timestamp).total_seconds() / 60)
                min_outage_time = 0
                if icmp_downtime > min_outage_time and check_icmp():
                    body = "ICMP was out for {} minutes until {}.".format(icmp_downtime, current_hour_min)
                    post = "{},{},{}".format("TCP", icmp_downtime, current_timestring)
                    notification.send("ICMP outage", body)
                    notification.send(None, post)
                    print(body)

        sleep(timeout)
