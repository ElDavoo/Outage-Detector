import json
import os
import socket
import traceback
from smtplib import SMTPAuthenticationError

import gspread

from outagedetector.send_mail import Mail


def curate_input(shown_message, expected_values):
    result = input(shown_message)
    if result in expected_values:
        return result.lower()
    else:
        return curate_input("You need to input one of the following: {}. Try again! ".format(expected_values),
                            expected_values)


def initialize():
    config_path = os.path.join(os.path.expanduser("~"), ".config/outagedetector")
    if not os.path.exists(config_path):
        os.makedirs(config_path)
    if os.path.exists(os.path.join(config_path, "config.json")):
        result = curate_input("Configuration file already exists. Would you like to reconfigure the script? (y/n) ",
                              ("y", "n"))
        if result != "y":
            print("Alright, script should be ready to run. If you run into issues, run the initialization process "
                  "again")
            exit(1)

    json_data = {"mail": False, "google": False}
    print("We are going to walk you through setting up this script!")
    configure_email = curate_input("Do you want email? (y/n) ",
                                   ("y", "n"))
    if configure_email == "y":
        json_data["mail"] = True
        mail_working = False
        failed_attempts = 0
        while not mail_working:
            sender_mail_address = None
            while sender_mail_address is None:
                sender_mail_address = Mail.check_mails(input("Please input the mail address you want to send the "
                                                             "notification mail from: "))
            json_data["mail_sender"] = sender_mail_address

            json_data["mail_password"] = input("Type in your password: ")

            receiver_mail_addresses = None
            while receiver_mail_addresses is None:
                receiver_mail_addresses = Mail.check_mails(input("Please input the mail addresses "
                                                                 "(separated by a comma) to which you want to send "
                                                                 "the notification: "))
            json_data["mail_receivers"] = receiver_mail_addresses

            if "gmail" in json_data["mail_sender"]:
                json_data["mail_smtp_server"] = "smtp.gmail.com"
                json_data["mail_port"] = 465
            elif "yahoo" in json_data["mail_sender"]:
                json_data["mail_smtp_server"] = "smtp.mail.yahoo.com"
                json_data["mail_port"] = 465
            else:
                json_data["mail_smtp_server"] = input("Please enter the SMTP server of your mail provider "
                                                      "(you can look it up online): ")
                port_number = ""
                while not port_number.isdigit():
                    port_number = input("Type in the port number of the SMTP server: ")
                json_data["mail_port"] = port_number
            try:
                mail = Mail(json_data["mail_sender"], json_data["mail_receivers"], json_data["mail_smtp_server"],
                            json_data["mail_password"],
                            json_data["mail_port"])
                mail.send_mail("Testing mail notification", "Mail sent successfully!")
                mail_working = True
                print("Mail has been successfully sent, check your mailbox!")
            except SMTPAuthenticationError as e:
                failed_attempts += 1
                if failed_attempts >= 3:
                    print("Too many failed attempts, exiting script, try again later!")
                    exit(1)
                if "BadCredentials" in str(e):
                    print(e)
                    print("Wrong user/password or less secure apps are turned off")
                elif "InvalidSecondFactor" in str(e):
                    print(e)
                    print("Two factor authentication is not supported! Turn it off and try again!")
            except socket.gaierror:
                print("No internet connection, try again later!")
                exit(1)
    configure_google = curate_input("Do you want Google Sheets? (y/n)",
                                    ("y", "n"))
    if configure_google == "y":
        json_data["google"] = True
        print("Follow this outdated guide.")
        print(
            "https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html")
        input("Now, Put client_secret.json into " + config_path + "and press enter.")
        client = gspread.service_account(os.path.join(config_path, "client_secret.json"))

        google_working = False
        while not google_working:
            try:
                doc_name = input("Insert the name of the google sheet: ")
                sheet = client.open(doc_name)
                json_data["google_doc"] = sheet.id
                google_working = True
            except gspread.SpreadsheetNotFound:
                print("Not found, try again")
                traceback.print_exc()
    timeout = input("how many seconds should i wait between checks? ")
    json_data["timeout"] = timeout
    with open(os.path.join(config_path, 'config.json'), 'w+') as json_file:
        json.dump(json_data, json_file)

    print("Config saved.")


if __name__ == '__main__':
    initialize()
