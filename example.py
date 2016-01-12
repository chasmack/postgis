
import psycopg2
import string
import random
import time

DSN = 'dbname=postgis_scratch user=postgres host=localhost password=pg'

schema = 'example'
codes_table = 'codes'
used_table = 'used'

CHARS = string.digits + string.ascii_uppercase

def next_code(code):
    d = 1
    next = ''
    for n in (2,1,0):
        d, m = divmod(CHARS.index(code[n]) + d, 36)
        next = CHARS[m] + next
    return None if d == 1 else next

with psycopg2.connect(DSN) as conn,  conn.cursor() as curs:

    qstr = """

    DROP TABLE IF EXISTS {schema}.{codes_table};
    CREATE TABLE {schema}.{codes_table}
    (
      gid serial NOT NULL,
      code character(3),
      CONSTRAINT {codes_table}_pkey PRIMARY KEY (gid)
    )
    WITH (OIDS=FALSE);

    DROP TABLE IF EXISTS {schema}.{used_table};
    CREATE TABLE {schema}.{used_table}
    (
      gid serial NOT NULL,
      code character(3),
      CONSTRAINT {used_table}_pkey PRIMARY KEY (gid)
    )
    WITH (OIDS=FALSE);

    """.format(schema=schema, codes_table=codes_table, used_table=used_table)
    curs.execute(qstr)

    qstr = """
    INSERT INTO {schema}.{codes_table} (code) VALUES
    """.format(schema=schema, codes_table=codes_table)

    startTime = time.time()

    for c in [c2+c1 for c2 in CHARS for c1 in CHARS]:

        codes = ",".join(["('{0}')".format(c+c0) for c0 in CHARS])

        curs.execute(
            'INSERT INTO {schema}.{codes_table} (code) VALUES {codes}'.format(
                schema=schema, codes_table=codes_table,  codes=codes
            )
        )

    endTime = time.time()
    print('\ntime: {0:.3f} sec'.format(endTime - startTime))

    maxgid = 36**3 - 1

    qstr = """
    INSERT INTO {schema}.{used_table} (code)
      SELECT code FROM {schema}.{codes_table};
    DELETE FROM {schema}.{used_table} WHERE gid IN ({gid_list});
    """.format(
        schema=schema, codes_table=codes_table, used_table=used_table,
        gid_list=','.join([str(random.randint(0, maxgid)) for a in range(5)])
    )
    curs.execute(qstr)

    qstr = """
    SELECT code
    FROM {schema}.{codes_table} c
    LEFT JOIN {schema}.{used_table} u USING (code)
    WHERE u.code IS NULL;

    """.format(schema=schema, codes_table=codes_table, used_table=used_table)
    curs.execute(qstr)
    n = curs.rowcount
    print('missing codes: {0}'.format(
        'none found.' if n == 0 else str(n)
    ))
    rows = curs.fetchall()
    for rec in rows:
        print('  {0}'.format(rec[0]))


    qstr = """
    DROP FUNCTION IF EXISTS example.next_code(char(3));

    CREATE OR REPLACE FUNCTION example.next_code(code char(3))
    RETURNS char(3) AS
    $$
    CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    d = 1
    next = ''
    for n in (2,1,0):
        d, m = divmod(CHARS.index(code[n]) + d, 36)
        next = CHARS[m] + next

    return None if d == 1 else next
    $$ LANGUAGE plpython3u IMMUTABLE;
    """.format(schema=schema, codes_table=codes_table, used_table=used_table)
    curs.execute(qstr)

    # Cleanup.
    qstr = """
    DROP TABLE IF EXISTS {schema}.{codes_table};
    DROP TABLE IF EXISTS {schema}.{used_table};
    DROP FUNCTION IF EXISTS {schema}.next_code(char(3));
    """.format(schema=schema, codes_table=codes_table, used_table=used_table)
    curs.execute(qstr)

conn.close()
