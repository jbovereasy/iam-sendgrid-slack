import os
import json
import boto3
import datetime
from datetime import timezone

from base64 import b64decode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

iam = boto3.client("iam")
now = datetime.datetime.now(timezone.utc)
alarm = datetime.timedelta(days=0)


# Get active keys num of days
def find_active_dates():
    num_dates = []
    users = iam.list_users()
    for user in users["Users"]:
        keys = iam.list_access_keys(UserName=user["UserName"])
        for key in keys["AccessKeyMetadata"]:
            if key["Status"] == "Active":
                if (now - key['CreateDate']) > alarm:
                    get_days = -(key['CreateDate'] - now)
                    num_dates.append(get_days.days)
    return num_dates


# Get users with expired active keys
def find_active_users():
    expired_users = []
    users = iam.list_users()
    for user in users["Users"]:
        keys = iam.list_access_keys(UserName=user["UserName"])
        for key in keys["AccessKeyMetadata"]:
            if key["Status"] == "Active":
                if (now - key['CreateDate']) > alarm:
                    expired_users.append(user["UserName"])
            else:
                None
    return expired_users


# Post attachment to slack
def lambda_handler(event, context):
    results = []
    HOOK_URL = os.environ["kmsEncryptedHookUrl_test"]
    alias = iam.list_account_aliases()["AccountAliases"][0]
    username = find_active_users()
    num_expire = find_active_dates()

    for i, j in zip(username, num_expire):
        message = [
            {
                "fallback": "Required alarm attachment",
                "title": f"Alert from {alias} account",
                "text": f"Access key needs rotating for user: {i.upper()}",
                "footer": f"{j} days",
                "color": "FF0000",
            }
        ]
        results += message
    req = Request(HOOK_URL, json.dumps(
        {"attachments": results}).encode("utf-8"))

    try:
        response = urlopen(req)
        print(response)
    except HTTPError as e:
        print(f" Error {e}")
    except URLError as e:
        print(f" Error {e}")
