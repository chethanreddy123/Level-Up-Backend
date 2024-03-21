import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

async def send_email(sender_email, sender_password, to_email, cc_emails, subject, message):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject

    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)

    msg.attach(MIMEText(message, 'plain'))

    async with aiosmtplib.SMTP('smtp.gmail.com', 587) as server:
        await server.starttls()
        await server.login(sender_email, sender_password)

        recipients = [to_email]
        if cc_emails:
            recipients.extend(cc_emails)

        text = msg.as_string()
        await server.sendmail(sender_email, recipients, text)
