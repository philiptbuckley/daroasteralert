import os
import smtplib
import configparser
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import html2text
from pathlib import Path

# --- CONFIGURATION ---
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

# --- Config file class ---
class CfgReader(dict):

    CFG_FILE = '~/.da_config'
    SECTION = 'MAINTENANCE ALERTS'
    OPTION_FNAME = 'filename'
    OPTION_SENDER = 'sender'
    OPTION_RECEIVER = 'receiver'

    def __init__(self):

        self.config = configparser.ConfigParser()
        
        # Read filename from config file
        path = Path(self.CFG_FILE).expanduser()
        if not path.exists():
            raise FileNotFoundError(f'Config file not found {self.CFG_FILE}')
        self.config.read([os.path.expanduser(self.CFG_FILE)])
        
        # Section exists?
        if not self.config.has_section(self.SECTION):
            raise ValueError (f'Section [{self.SECTION}] missing from config file {self.CFG_FILE}')
        
        # Get maintenance file name
        self[self.OPTION_FNAME] = self.config.get(self.SECTION, self.OPTION_FNAME, fallback=None)
        if not self[self.OPTION_FNAME]:
            raise ValueError (f"{self.OPTION_FNAME} keyword missing from {self.SECTION} section of config file {self.CFG_FILE}'")
        
        if not os.path.exists(self[self.OPTION_FNAME]):
            raise FileNotFoundError(f'Roaster maintenance schedule file {self[self.OPTION_FNAME]} not found')
        
    def get_fname(self) -> str:
        return self[self.OPTION_FNAME]
        
# --- 1. PARSE SPREADSHEET ---

def check_maintenance(maintfile: str):

    # Read the LibreOffice Calc sheet
    df = pd.read_excel(maintfile, engine="odf")

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

    try:
        # Read the maintenance section of the config file
        cfg = CfgReader()

        check_maintenance(cfg.get_fname())

    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}")
        raise SystemExit(1)

