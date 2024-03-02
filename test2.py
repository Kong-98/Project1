import email
import imaplib
import os
import requests
from requests.auth import HTTPBasicAuth
import json

user = 'jashwanthreddy862@gmail.com'
password = 'yqudvpnwsqwfycak'
imap_url = 'imap.gmail.com'

jira_user = "akonganapati@gmail.com"
jira_api_token = "ATATT3xFfGF0B3rQHymGMJEKNlNwMNb989EC36enInCyaZwq5XFNkA-zgehuo2zK88UVL1DEfCDQ2c8C5lBUS0GlLDZmXmjvso7tPlXxWGkdmGR9xdclEPpDDCKyIue0R0NmWWY8sJQqUtt4KxseETvltARYDAbnchmUHr0dvozy-3yVD5OBGjw=41C7084F"
jira_url = "https://ajay-1998.atlassian.net/rest/api/3/issue/"
jira_url_post = "https://ajay-1998.atlassian.net/browse"
project_id = "10003"
issue_type_id = "10000"

slack_webhook_url = 'https://hooks.slack.com/services/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'

attachment_path = r'D:\pythontest'  # Specify the path to save attachments


def get_body(msg):
    if msg.is_multipart():
        return get_body(msg.get_payload(0))
    else:
        return msg.get_payload(None, True)


def send_message_to_slack(text, webhook_url):
    slack_data = {'text': text}
    response = requests.post(webhook_url, data=json.dumps(slack_data),
                             headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        raise ValueError(
            f"Request to slack returned an error {response.status_code}, the response is:\n{response.text}")


def save_attachment(attachment):
    # Generate a unique filename for the attachment
    filename = f"attachment_{hash(attachment)}.dat"
    with open(os.path.join(attachment_path, filename), 'wb') as f:
        f.write(attachment)
    return filename


def create_jira_issue_with_attachment(email_subject, email_body, attachments):
    headers = {"Content-Type": "application/json"}
    issue_data = {
        "fields": {
            "project": {"id": project_id},
            "summary": email_subject,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "text": email_body,
                                "type": "text"
                            }
                        ]
                    }
                ]
            },
            "issuetype": {"id": issue_type_id}
        }
    }

    response = requests.post(jira_url, headers=headers, auth=HTTPBasicAuth(jira_user, jira_api_token),
                             data=json.dumps(issue_data))
    if response.status_code == 201:
        issue_key = response.json()['key']
        print(f"JIRA issue created: {issue_key}")
        for attachment in attachments:
            upload_attachment_to_jira(issue_key, attachment, jira_user, jira_api_token)
        # Notify Slack about the created JIRA issue
        send_message_to_slack(f"New JIRA issue created: {jira_url_post}/{issue_key}", slack_webhook_url)
    else:
        print(f"Failed to create JIRA issue: {response.status_code}, {response.text}")


def upload_attachment_to_jira(issue_key, attachment_path, jira_user, jira_api_token):
    headers = {
        "X-Atlassian-Token": "nocheck",
    }
    files = {'file': open(attachment_path, 'rb')}
    upload_url = f"{jira_url}{issue_key}/attachments"

    response = requests.post(upload_url, files=files, auth=HTTPBasicAuth(jira_user, jira_api_token), headers=headers)
    if response.status_code == 200:
        print(f"Attachment uploaded to JIRA issue '{issue_key}'")
    else:
        print(f"Failed to upload attachment to JIRA issue '{issue_key}': {response.status_code}, {response.text}")


if not os.path.exists(attachment_path):
    os.makedirs(attachment_path)

con = imaplib.IMAP4_SSL(imap_url)
con.login(user, password)
con.select('INBOX')

result, data = con.search(None, 'UNSEEN')
msgs = data[0].split()

for num in msgs:
    typ, data = con.fetch(num, '(RFC822)')
    for response_part in data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            email_subject = msg['subject']
            email_body = get_body(msg).decode('utf-8')
            attachments = []
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                attachment = part.get_payload(decode=True)
                filename = save_attachment(attachment)
                attachments.append(os.path.join(attachment_path, filename))
            create_jira_issue_with_attachment(email_subject, email_body, attachments)

con.close()
con.logout()
