#!/bin/bash

# Generate database.ini
cat << EOF > ATC-Framework/src/pe_reports/data/database.ini
[postgres]
host=${DB_HOST}
database=${PE_DB_NAME}
user=${PE_DB_USERNAME}
password=${PE_DB_PASSWORD}
port=5432

[shodan]
key1=${PE_SHODAN_API_KEYS}

[hibp]
key=${HIBP_API_KEY}

[pe_api]
pe_api_key=${PE_API_KEY}
pe_api_url=https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/
cf_api_key=${CF_API_KEY}

[staging]
[cyhy_mongo]

[sixgill]
client_id=${SIXGILL_CLIENT_ID}
client_secret=${SIXGILL_CLIENT_SECRET}

[whoisxml]
key=

[intelx]
api_key=${INTELX_API_KEY}

[dnsmonitor]
[pe_db_password_key]
[blocklist]
[dehashed]
[dnstwist]

[API_Client_ID]
[API_Client_secret]
[API_WHOIS]

[xpanse]
api_key=${XPANSE_API_KEY}
auth_id=${XPANSE_AUTH_ID}


EOF

# Find the path to the pe_reports package in site-packages
pe_reports_path=$(pip show pe-reports | grep -E '^Location:' | awk '{print $2}')

# Ensure pe_reports_path ends with /pe_reports
pe_reports_path="${pe_reports_path%/pe-reports}/pe_reports"

# Copy database.ini to the module's installation directory
cp /app/ATC-Framework/src/pe_reports/data/database.ini "${pe_reports_path}/data/"

exec "$@"
