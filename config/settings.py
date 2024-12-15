import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://localhost:5432/business_chatbot"))

    QBO_CLIENT_ID: str = field(default_factory=lambda: os.getenv("QBO_CLIENT_ID", ""))
    QBO_CLIENT_SECRET: str = field(default_factory=lambda: os.getenv("QBO_CLIENT_SECRET", ""))
    QBO_REDIRECT_URI: str = field(default_factory=lambda: os.getenv("QBO_REDIRECT_URI", "http://localhost:8080/callback"))
    QBO_REALM_ID: str = field(default_factory=lambda: os.getenv("QBO_REALM_ID", ""))
    QBO_ENVIRONMENT: str = field(default_factory=lambda: os.getenv("QBO_ENVIRONMENT", "sandbox"))

    OPENAI_API_KEY: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    OPENAI_MODEL: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4"))

    GOOGLE_SHEETS_CREDS_FILE: str = field(default_factory=lambda: os.getenv("GOOGLE_SHEETS_CREDS_FILE", "config/google_service_account.json"))
    GOOGLE_SHEETS_SPREADSHEET_ID: str = field(default_factory=lambda: os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", ""))

    SMTP_HOST: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.gmail.com"))
    SMTP_PORT: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    SMTP_USER: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    SMTP_PASSWORD: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    REPORT_RECIPIENT: str = field(default_factory=lambda: os.getenv("REPORT_RECIPIENT", ""))

    EZRENTOUT_API_KEY: str = field(default_factory=lambda: os.getenv("EZRENTOUT_API_KEY", ""))
    EZRENTOUT_BASE_URL: str = field(default_factory=lambda: os.getenv("EZRENTOUT_BASE_URL", "https://app.ezrentout.com/api/v1"))
    PICTAMAIL_API_KEY: str = field(default_factory=lambda: os.getenv("PICTAMAIL_API_KEY", ""))
    PICTAMAIL_BASE_URL: str = field(default_factory=lambda: os.getenv("PICTAMAIL_BASE_URL", ""))
    MYTAXPREPOFFICE_API_KEY: str = field(default_factory=lambda: os.getenv("MYTAXPREPOFFICE_API_KEY", ""))
    MYTAXPREPOFFICE_BASE_URL: str = field(default_factory=lambda: os.getenv("MYTAXPREPOFFICE_BASE_URL", ""))
    USPS_USERID: str = field(default_factory=lambda: os.getenv("USPS_USERID", ""))

    NIGHTLY_SYNC_HOUR: int = field(default_factory=lambda: int(os.getenv("NIGHTLY_SYNC_HOUR", "2")))
    NIGHTLY_SYNC_MINUTE: int = field(default_factory=lambda: int(os.getenv("NIGHTLY_SYNC_MINUTE", "0")))


settings = Settings()
