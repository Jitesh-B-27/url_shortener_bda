# AWS URL Shortener

A small Flask application for shortening URLs, counting redirects, and exporting URL data to Amazon S3. It is designed for EC2 behind Nginx and Gunicorn, with RDS MySQL for persistence and an EC2 IAM role for S3 access.

## Architecture

~~~text
Browser -> Nginx :80 -> Gunicorn 127.0.0.1:8000 -> Flask
                                                      |-> RDS MySQL
                                                      -> Amazon S3
~~~

The repository contains no AWS keys or database credentials. Environment variables provide all deployment-specific values.

## Features

- Create HTTP and HTTPS short URLs
- Redirect and track click counts
- Display all URLs in a dashboard
- Export all rows to a timestamped CSV object under **exports/** in S3
- Process health check at **GET /health**

## Prerequisites

- Python 3.10 or newer
- MySQL 8 locally or an accessible RDS MySQL instance
- An S3 bucket and AWS credentials for local export testing
- On EC2: Ubuntu, Nginx, and an attached IAM role

## Environment variables

Copy **.env.example** to **.env** for local development.

| Variable | Purpose | Example |
|---|---|---|
| SECRET_KEY | Flask session-signing key | A long random value |
| DB_HOST | MySQL endpoint without a protocol | RDS endpoint |
| DB_PORT | MySQL port | 3306 |
| DB_NAME | Existing database name | urlshortener |
| DB_USER | Application database user | app_user |
| DB_PASSWORD | Application database password | Secret value |
| AWS_REGION | S3 bucket region | ap-south-1 |
| S3_BUCKET_NAME | Existing bucket name | project-url-exports |
| BASE_URL | Public address used for short links | http://EC2_PUBLIC_IP |

The **.env** file is ignored by Git. Never commit it. Generate a production secret with:

~~~bash
python3 -c "import secrets; print(secrets.token_hex(32))"
~~~

## Local setup

~~~bash
python -m venv .venv
~~~

Linux or macOS:

~~~bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
~~~

Windows PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
~~~

Create a local database and restricted user. Substitute a strong password:

~~~sql
CREATE DATABASE urlshortener CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'app_user'@'%' IDENTIFIED BY 'replace-me';
GRANT SELECT, INSERT, UPDATE, CREATE, INDEX ON urlshortener.* TO 'app_user'@'%';
FLUSH PRIVILEGES;
~~~

Fill in **.env**, then initialize and run:

~~~bash
python scripts/init_db.py
python run.py
~~~

Open **http://localhost:5000**. On Linux, a production-like local command is:

~~~bash
gunicorn --workers 2 --bind 127.0.0.1:8000 run:app
~~~

Gunicorn does not run natively on Windows; use Flask there.

## Tests

Tests use an isolated in-memory SQLite database and mock S3, so no AWS resources are contacted:

~~~bash
pytest -q
~~~

Also perform a final integration test against MySQL before deployment.

## AWS requirements

### RDS MySQL

- Use a private RDS MySQL instance.
- Its DB subnet group should contain private subnets in at least two Availability Zones.
- Create the database and application user before running **scripts/init_db.py**.
- Keep RDS values in the EC2 environment file only.
- Allow TCP 3306 only from the EC2 security group.
- Do not make RDS public or allow 0.0.0.0/0 on port 3306.

### S3 and IAM

Create a private bucket in the configured region. Attach an IAM role to EC2 that permits uploads only to this project's export prefix:

~~~json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::your-project-bucket/exports/*"
  }]
}
~~~

Do not create AWS keys for the application. boto3 automatically uses temporary credentials from the EC2 instance role.

### Security groups

EC2 inbound:

- TCP 80 from 0.0.0.0/0
- TCP 22 from the administrator's public IP only
- Optionally TCP 443 when HTTPS is configured

Never expose ports 5000 or 8000 publicly.

RDS inbound:

- TCP 3306 from the EC2 security group only

## EC2 deployment

These commands assume Ubuntu. Replace the repository URL and adjust the service username/path if the AMI differs.

~~~bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx git
sudo git clone https://github.com/<username>/<repository>.git /opt/url_shortener_bda
sudo chown -R ubuntu:www-data /opt/url_shortener_bda
cd /opt/url_shortener_bda
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
~~~

Create **/etc/url-shortener.env** with plain KEY=value lines based on **.env.example**, then protect it:

~~~bash
sudo nano /etc/url-shortener.env
sudo chown root:root /etc/url-shortener.env
sudo chmod 600 /etc/url-shortener.env
~~~

Load it once to initialize the database:

~~~bash
set -a
source /etc/url-shortener.env
set +a
python scripts/init_db.py
~~~

Test Gunicorn, then verify the health endpoint from a second shell:

~~~bash
gunicorn --workers 2 --bind 127.0.0.1:8000 run:app
curl http://127.0.0.1:8000/health
~~~

Stop the test process and install the service and reverse proxy:

~~~bash
sudo cp deployment/url-shortener.service /etc/systemd/system/url-shortener.service
sudo cp deployment/nginx.conf /etc/nginx/sites-available/url-shortener
sudo ln -s /etc/nginx/sites-available/url-shortener /etc/nginx/sites-enabled/url-shortener
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable --now url-shortener
sudo systemctl restart nginx
~~~

If the EC2 user is not **ubuntu**, edit User, Group, ownership, and paths in the service template first.

## Verification

~~~bash
curl http://127.0.0.1:8000/health
curl http://EC2_PUBLIC_IP/health
sudo systemctl status url-shortener
sudo journalctl -u url-shortener -n 100 --no-pager
~~~

Then create a short URL, follow it, confirm the click count increases, export the CSV, and confirm the displayed S3 object key exists.

## Troubleshooting

- **Incomplete database configuration:** confirm every DB variable exists, then restart the service.
- **Database connection failure:** check the endpoint, user/database creation, port 3306, and EC2-to-RDS security-group rule.
- **S3 export failure:** check bucket name, region, IAM role attachment, and PutObject permission for the export prefix.
- **502 Bad Gateway:** inspect the service status and journal; confirm Gunicorn binds to 127.0.0.1:8000.
- **Nginx error:** run **sudo nginx -t** and check for another enabled site using port 80.

Technical exceptions go to the service journal. Browser messages intentionally omit database and AWS details.

## GitHub handoff

Before the first push, confirm **.env** is absent from Git status:

~~~bash
git init
git add .
git status
git commit -m "Build AWS-ready URL shortener application"
git branch -M main
git remote add origin https://github.com/<username>/<repository>.git
git push -u origin main
git tag -a v1.0.0 -m "Initial deployable URL shortener"
git push origin v1.0.0
~~~

The AWS teammate can deploy the reviewed **v1.0.0** tag rather than an unfinished branch.
