# BackEnd based on Flask = Gunicorn
  **Doc in progress**

The Framework used is NextJS which is installed with: npm install next react react-dom
For testing purpouse just run execute the project with: npm run dev

# Environment file

You must create a local environment files: 
- .env

The file must include:

FLASK_APP=server.py
FLASK_DEBUG=1
JWT_AUTH_SECRET=""
FLASK_AUTH_SECRET=""

HOSTNAME=""

# POSGRESQL
POSGRESQL_DATABASE=""

POSGRESQL_LOCAL_URL="X.X.X.X"
POSGRESQL_LOCAL_PORT="YYYY"
POSGRESQL_LOCAL_USER="user"
POSGRESQL_LOCAL_USER_PASSWORD="password"

POSGRESQL_REMOTE_URL="Z.Z.Z.Z"
POSGRESQL_REMOTE_PORT="YYYY"
POSGRESQL_REMOTE_USER="user"
POSGRESQL_REMOTE_USER_PASSWORD="password"

# MAIL
MAIL_SMTP_SERVER="smtp.provider.com"
MAIL_SMTP_PORT=X
MAIL_SENDER_EMAIL="email@provider.com"
MAIL_USERNAME="username"
MAIL_PASSWORD="password"

# Telegram
TELEGRAM_BOT_TOKEN=""

# HCAPTCHA
HCAPTCHA_SITE_KEY=""
HCAPTCHA_SECRET_KEY=""