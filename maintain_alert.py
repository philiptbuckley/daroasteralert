import os
import smtplib
import configparser
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import html2text

# --- CONFIGURATION ---
FILE_PATH = "/mnt/production/Maintenance schedule.ods"
EMAIL_SENDER = "your_alerts_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"  # Use an App Password, not your regular password
EMAIL_RECEIVER = "roaster_operator@example.com"
SMTP_SERVER = "://gmail.com"
SMTP_PORT = 587

# --- Test output to terminal ---
def test_output_to_terminal(due_tasks):
    html_table = due_tasks.to_html(index=False)
    html_body = f"<h3>Coffee Roaster Maintenance Due</h3>{html_table}"

    # Pretty print the HTML to standard terminal text
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    print(text_maker.handle(html_body))

# --- Read config data ---
def get_filename():
    # Read filename from config file
    CFG_FILE = '~/.da_config'
    SECTION = 'MAINTENANCE ALERTS'
    OPTION = 'maint_logfile'
    global __config
    __config = configparser.ConfigParser()
    fc = __config.read([os.path.expanduser(CFG_FILE)])
    if not fc:
        print(f'Config file not found {CFG_FILE}')
        return None
    
    # Section exists?
    if not __config.has_section(SECTION):
        print (f'Section [{SECTION}] missing from config file {CFG_FILE}')
        return None
    
    # Option exists?
    fname = __config.get(SECTION, OPTION,fallback=None)
    if not fname:
        print (f'Option {OPTION} missing from config file {CFG_FILE}')
        return None

    # File exists?
    if not os.path.exists(fname):
        print(f"Error: File not found at {fname}")
        return None
    
    return fname

# --- 1. PARSE SPREADSHEET ---

def check_maintenance():

    file_path = get_filename()
    if not file_path:
        return
    # Read the LibreOffice Calc sheet
    df = pd.read_excel(FILE_PATH, engine="odf")

    # Clean column names (strips whitespace)
    df.columns = df.columns.str.strip()

    # Convert 'Next Due' column to datetime
    # Replace 'Next Due' with your exact column name
    df["Next Due"] = pd.to_datetime(df["Next Due"], errors="coerce")

    # Get today's date (normalized to midnight)
    today = pd.to_datetime(datetime.today().date())

    # Filter for tasks due today or already overdue
    due_tasks = df[df["Next Due"] <= today]

    # Filter only the columns required for email
    columns_for_email = ["Task", "Last Done", "By", "Next Due", "Comments"]
    due_tasks_filtered = due_tasks[columns_for_email]

    if not due_tasks.empty:
        test_output_to_terminal(due_tasks_filtered)
        # send_email(due_tasks_filtered)
    else:
        print("No maintenance tasks due today.")


# --- 2. SEND EMAIL ---


def send_email(tasks_df):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = f"🚨 Coffee Roaster Maintenance Due - {datetime.today().strftime('%Y-%m-%d')}"

    # Convert the due tasks dataframe into a clean HTML table for the email body
    html_table = tasks_df.to_html(index=False, classes="table table-striped")

    body = f"""
    <html>
      <head>
        <style>
          table {{ border-collapse: collapse; width: 100%; font-family: sans-serif; }}
          th, td {{ text-align: left; padding: 8px; border: 1px solid #ddd; }}
          th {{ background-color: #4CAF50; color: white; }}
          tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
      </head>
      <body>
        <p>The following coffee roaster maintenance tasks require attention:</p>
        {html_table}
        <br>
        <p>Please update the spreadsheet once the tasks are completed.</p>
      </body>
    </html>
    """

    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("Alert email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


if __name__ == "__main__":
    check_maintenance()

