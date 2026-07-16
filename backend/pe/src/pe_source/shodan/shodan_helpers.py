# Third-Party Libraries
import pandas as pd
import psycopg2
from psycopg2 import OperationalError
import psycopg2.extras as extras

CONN_PARAMS_DIC = config()

def connect():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(**CONN_PARAMS_DIC)
    except OperationalError as err:
        show_psycopg2_exception(err)
        conn = None
    return conn

def insert_shodan_top_cves(top_cves):
    """Take dataframe of top 10 Shodan CVEs and insert into the top_cves_shodan table."""
    # Build query
    cve_list = top_cves.to_dict(orient="records")
    insert_vals = ""
    for record in cve_list:
        cve_id = record.get("cve_id")
        epss = record.get("epss")
        nvd = record.get("nvd_base_score").replace("'", "''")
        date = record.get("date")
        summary = record.get("summary").replace("'", "''")
        data_source_uid = record.get("data_source_uid")
        insert_vals += f"('{cve_id}', '{epss}', '{nvd}', '{date}', '{summary}', '{data_source_uid}'),\n"
    insert_vals = insert_vals[:-2]
    sql = f"""
    INSERT INTO top_cves_shodan(cve_id, epss_score, nvd_base_score, collection_date, summary, data_source_uid)
    VALUES
    {insert_vals}
    ON CONFLICT (cve_id, collection_date)
    DO UPDATE SET
    epss_score = EXCLUDED.epss_score,
    nvd_base_score = EXCLUDED.nvd_base_score,
    summary = EXCLUDED.summary,
    data_source_uid = EXCLUDED.data_source_uid
    """
    # Execute query
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

def query_all_shodan_cves(start_date, end_date):
    """Retrieve a list of all distinct CVEs across all stakeholders for the specified report period."""
    # Build query
    sql = f"""
    SELECT DISTINCT cve
    FROM
        (
            SELECT
                o.organizations_uid,
                o.cyhy_db_name,
                sv.timestamp,
                sv.type,
                UNNEST(sv.potential_vulns) as cve
            FROM
                shodan_vulns sv JOIN
                organizations o ON
                sv.organizations_uid = o.organizations_uid
            WHERE
                o.report_on = True AND
                sv.timestamp BETWEEN '{start_date}' AND '{end_date}' AND
                sv.type != 'Insecure Protocol'
        ) q1
    ORDER BY
        cve DESC
    """
    # Execute query
    conn = connect()
    df = pd.read_sql(sql, conn)
    conn.close()
    # Return result
    return df