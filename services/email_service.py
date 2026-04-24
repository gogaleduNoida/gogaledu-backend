import requests
from flask import render_template
from config import Config

def send_email(to_email, subject, template, attachments=None, **kwargs):
    html_content = render_template(template, **kwargs)

    files = []
    if attachments:
        for file_path in attachments:
            files.append(("attachment", open(file_path, "rb")))

    response = requests.post(
        f"https://api.mailgun.net/v3/{Config.MAILGUN_DOMAIN}/messages",
        auth=("api", Config.MAILGUN_API_KEY),
        data={
           "from": Config.FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content
        },
        files=files
    )

    return response
