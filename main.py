#!/usr/bin/env python3
import os
import json
import datetime
import time
import boto3
import sendgrid
from datetime import timezone

session = boto3.Session(profile_name="default")
alias = session.client("iam").list_account_aliases()["AccountAliases"][0]
iam = session.client("iam", region_name="us-west-2")
ses = session.client("ses", region_name="us-west-2")

alarm = datetime.timedelta(days=0)  # 90
now = datetime.datetime.now(timezone.utc)

email = 'john.baltazar@warnerbros.com' # notify this user when tags are missing

# Get users with expired active keys
def find_active_users():
    username = []
    user_expire = []
    user_email = []
    users = iam.list_users()

    for user in users["Users"]:
        keys = iam.list_access_keys(UserName=user["UserName"])
        tags = iam.list_user_tags(UserName=user["UserName"])
        for key in keys["AccessKeyMetadata"]:
            # Check if access key is active
            if key["Status"] == "Active":
                if (now - key['CreateDate']) > alarm:
                    # print(user['UserName'], tags['Tags'])
                    get_days = now - key['CreateDate']
                    user_expire.append(get_days.days)
                    username.append(user["UserName"])
                    # Checks if there is no tag, append to an email
                    if len(tags["Tags"]) == 0:
                        user_email.append(email)
                    # Checks if there are tags, but email tag is missing, append to an email
                    elif not any(v['Key'] == 'Email' or v['Key'] == 'email' for v in tags['Tags']):
                        user_email.append(email)
                    else:
                        for tag in tags["Tags"]:
                            # Check if email tag exists, append value
                            if tag['Key'].lower() == 'email':
                                user_email.append(tag['Value'])
    for i, j, k in zip(username, user_expire, user_email):
        print(i, j, k)
    print('\n')
    return username, user_expire, user_email


# Send using Sendgrid
def send_sendgrid():
    username, num_expire, user_email = find_active_users()
    # Alert - 1 week - 83, 2 days - 88, 1 day - 89
    alert_sched = 50  # 83

    # Alarm - 91 day
    alarm_sched = 59  # 91

    sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API'))
    # no_reply_email = <sendgrid no-reply email>

    for i, j, k in zip(username, num_expire, user_email):
        # if j == alert_sched or j == alert_sched + 5 or j == alert_sched + 6:
        if j == alert_sched or j == alert_sched + 5:
            # print(
            #     k, f"TEST Email: {alias} - {i} IAM access key needs rotating in {alarm_sched - j} days")
            data = {
                "personalizations": [
                    {
                        "to": [
                            {
                                "email": k
                            }
                        ],
                        "subject": f"TEST Email: {alias} - {i} IAM access key needs rotating in {alarm_sched - j} days"
                    }
                ],
                "from": {
                    "email": no_reply_email
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": f"Hello {i}, this is a just test. Please rotate your key in {alarm_sched - j} days."
                    }
                ]
            }
            response = sg.client.mail.send.post(request_body=data)
            print(response.status_code)
            print(response.body)
            print(response.headers)

            data = {
                "personalizations": [
                    {
                        "to": [
                            {
                                "email": k
                            }
                        ],
                        "subject": f"Alert: {alias} - {i} IAM access key needs rotating in {alarm_sched - j} days"
                    }
                ],
                "from": {
                    "email": no_reply_email
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": f"Hello {i}, as a part of compliance, your IAM access key needs to be rotated in {alarm_sched - j} days. Please rotate as soon as possible."
                    }
                ]
            }
            response = sg.client.mail.send.post(request_body=data)
            print(response.status_code)
            print(response.body)
            print(response.headers)
        elif j >= alarm_sched and j < 200:
            data = {
                "personalizations": [
                    {
                        "to": [
                            {
                                "email": k
                            }
                        ],
                        "subject": f"Alarm: {alias} - {i} IAM key exceeded 59 days."
                    }
                ],
                "from": {
                    "email": no_reply_email
                },
                "content": [
                    {
                        "type": "text/plain",
                        "value": f"Hello {i}, your IAM access key exceeded more than 59 days. No further notification will be sent. Please act on this today."
                    }
                ]
            }
            response = sg.client.mail.send.post(request_body=data)
            print(response.status_code)
            print(response.body)
            print(response.headers)
            # print(k, f"Alarm: {alias} - {i} IAM key exceeded 59 days")
        else:
            # print(i, j, k, " - do nothing")
            pass


# Post email using SES - NOT USING AWS SES
def send_email_notification():
    # username, num_expire, user_email = find_active_users()
    # username = 'jbaltazar'
    # num_expire = 17
    # user_email = 'john.baltazar@warnerbros.com'

    for i, j, k in zip(username, num_expire, user_email):
        if j == alert_sched:
            email_alert_body = f'''Dear {i}, this is an automatic reminder to please rotate your AWS Access Keys in {j} days.'''
            ses.send_email(
                Source=email,
                Destination={
                    'ToAddresses': [email]
                },
                Message={
                    'Subject': {
                        'Data': 'Test email from SES',
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': email_alert_body,
                            'Charset': 'UTF-8'
                        }
                    }
                })

            print(email_alert_body)
        else:
            print(i, j, k)


# Post message to Slack
def post_to_slack():
    username, num_expire, user_email = find_active_users()

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
        req = r.post(
            os.environ.get('HOOK_URL'),
            data=json.dumps({"attachments": message}),
            headers={"Content-Type": "application/json"},
        )
    try:
        print(f"{req} - {req.text}")
    except TypeError as err:
        print(err)


def main():
    start_time = time.time()
    # find_active_users()
    send_sendgrid()
    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
    main()
