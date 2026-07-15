PRODUCTION DASHBOARD

FILES
- app.py
- database.py
- report_utils.py
- requirements.txt
- favicon.png
- views/production_report.py
- views/upload_reports.py

HOW TO DEPLOY

1. Upload all files and folders to the GitHub repository connected to Streamlit.
2. In Streamlit Cloud open:
   App settings > Secrets
3. Add:

DATABASE_URL = "YOUR_SUPABASE_POSTGRESQL_CONNECTION_STRING"

4. Save the secret.
5. Streamlit will redeploy the app automatically.

HOW IT WORKS

- Production Report:
  Shows all historical production data saved in PostgreSQL.

- Upload Reports:
  Upload CSV or XLSX reports.
  Data is saved permanently in PostgreSQL.
  Existing date/product combinations are updated.
  Exact duplicate files are blocked.

EXPECTED REPORT COLUMNS

Date
Line
Product
Actual Units
Expected Units
Actual Run Rate (/min)
Est. Run Rate (/min)
