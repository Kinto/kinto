import pytest
import psycopg2

def test_microsecond_precision():
    # Connect to PostgreSQL database
    conn = psycopg2.connect(dbname="your_db", user="your_user", password="your_password", host="localhost", port="5432")
    cursor = conn.cursor()

    # Insert test records
    cursor.execute("""
        INSERT INTO objects (id, parent_id, resource_name, last_modified, data, deleted)
        VALUES
        ('1', '/buckets/test', 'resource1', '2025-04-12 16:21:28.123456', '{}'::JSONB, false),
        ('2', '/buckets/test', 'resource1', '2025-04-12 16:21:28.123457', '{}'::JSONB, false);
    """)
    
    # Query the records
    cursor.execute("""
        SELECT id, last_modified, as_epoch_micro(last_modified)
        FROM objects
        WHERE parent_id = '/buckets/test' AND resource_name = 'resource1'
        ORDER BY last_modified DESC;
    """)
    
    # Fetch all rows
    rows = cursor.fetchall()
    
    # Test that the microsecond precision is correctly applied
    assert len(rows) == 2
    assert rows[0][2] != rows[1][2]  # Ensure the epoch microseconds are different
    
    # Close the cursor and connection
    cursor.close()
    conn.close()

# Run the test
pytest.main()
