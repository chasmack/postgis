# PSU Geography 897d project 4
#
# In GEOG 483 the first project had you finding the best locations for "Jen and Barry"
# to open an ice cream business. We're going to revisit that scenario for this project.
# Your task is to import the project shapefiles into a PostGIS schema and then write a
# series of SQL statements that automate the site selection process. If you need a new
# copy of the data you can download and unzip the Project 4 Data file. Here's a reminder
# of Jen and Barry's original selection criteria:
#
#  Greater than 500 farms for milk production
#  A labor pool of at least 25,000 individuals between the ages of 18 and 64 years
#  A low crime index (less than or equal to 0.02)
#  A population of less than 150 individuals per square mile
#  Located near a university or college
#  At least one recreation area within 10 miles
#  Interstate within 20 miles
#
# Because the interstate and recreation area criteria are a bit difficult to evaluate,
# I'm only going to require you to handle the other (county- and city-level) criteria.
# Given these requirements you should end up with 9 candidate cities. You can attempt
# to incorporate the interstate and recreation area criteria for extra credit. If you
# do so correctly you will end up with 4 candidate cities.

import psycopg2
import psycopg2.extras

DSN = 'dbname=postgis_scratch user=postgres host=localhost password=pg'
DSN_Z400 = 'dbname=postgis_scratch user=postgres host=z400 password=pg707'

with psycopg2.connect(DSN) as conn, psycopg2.connect(DSN_Z400) as rconn:
    with conn.cursor() as curs:
        qstr = """
        SELECT ci.name AS city, co.name AS county,
            co.no_farms87::integer AS farms,
            co.age_18_64::integer AS labor_pool,
            ci.crime_inde::numeric(6,4) AS crime_index,
            co.pop_sqmile::numeric(6,2) AS pop_density,
            ci.university > 0 AS university,
            miles_to_recreation, miles_to_interstate
        FROM (
          SELECT intco.gid AS county_gid, intci.gid AS city_gid,
            min (
              ST_Distance(ST_Transform(intci.geom, 2272), ST_Transform(rec.geom, 2272)) / 5280
            )::numeric(6,2) AS miles_to_recreation,
            min (
              ST_Distance(ST_Transform(intci.geom, 2272), ST_Transform(ist.geom, 2272)) / 5280
            )::numeric(6,2) AS miles_to_interstate
          FROM geog897d.v_jb_candidate_counties AS intco
            INNER JOIN geog897d.cities AS intci ON ST_Contains(intco.geom, intci.geom),
            geog897d.rec_areas AS rec,
            geog897d.interstates AS ist
          GROUP BY county_gid, city_gid
        ) AS a
          INNER JOIN geog897d.cities AS ci ON ci.gid = city_gid
          INNER JOIN geog897d.counties AS co on co.gid = county_gid
        WHERE ci.crime_inde <= 0.02
            AND ci.university > 0
            -- AND miles_to_recreation <= 10
            -- AND miles_to_interstate <= 20
        ORDER BY miles_to_interstate
        """

        curs.execute(qstr)
        rows = curs.fetchall()

        for rec in rows:
            city, county, farms, labor_pool, crime_index = rec[0:5]
            pop_density, university, miles_to_recreation, miles_to_interstate = rec[5:9]
            
            print('{0:6.2f}: {1}'.format(miles_to_interstate, city))
            
        # Query roster data from local database.
        qstr = """
        SELECT first_name, last_name, postal_code
        FROM geog897d.roster
        """
        curs.execute(qstr)
        students = curs.fetchall()
        
        print()
        print('SELECT: ' + str(curs.rowcount) + ' rows returned.')
        
        # Close local cursor and send roster data to remote database.
        curs.close()

    with rconn.cursor() as rcurs:

        qstr = """
        DROP SCHEMA IF EXISTS sample CASCADE;
        
        CREATE SCHEMA sample
          AUTHORIZATION postgres;
          
        CREATE TABLE sample.roster
        (
          gid serial NOT NULL,
          first_name character varying(50),
          last_name character varying(50),
          postal_code character varying(6),
          CONSTRAINT roster_pkey PRIMARY KEY (gid)
        )
        WITH (
          OIDS=FALSE
        );
        
        ALTER TABLE sample.roster
          OWNER TO postgres;

        """
        rcurs.execute(qstr)
        
        qstr = """
        INSERT INTO sample.roster (first_name, last_name, postal_code)
        VALUES (%s, %s, %s)
        """
        rcurs.executemany(qstr, students)
        print('INSERT: ' + str(rcurs.rowcount) + ' rows effected.')
        
        # Done with remote database.
        rcurs.close()
        
    # Use dictionary names for columns.
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

        # Charlie Mack - 93436
        # Michael Mack - 93421

        qstr = """
        SELECT first_name AS first, last_name AS last, postal_code AS zip
        FROM geog897d.roster WHERE postal_code LIKE '93%'
        """
        curs.execute(qstr)
        rows = curs.fetchall()
        students = rows
        
        print()
        print('SELECT: ' + str(curs.rowcount) + ' rows returned.')
        for rec in rows:
            print(rec['first'] + ' ' + rec['last'] + ' - ' + rec['zip'])

        qstr = """
        DELETE FROM geog897d.roster WHERE postal_code LIKE '93%'
        """
        curs.execute(qstr)
        
        print()
        print('DELETE: ' + str(curs.rowcount) + ' rows effected.') 
        
        qstr = """
        INSERT INTO geog897d.roster (first_name, last_name, postal_code)
        VALUES (%s, %s, %s)
        """
        curs.executemany(qstr, students)

        print('INSERT: ' + str(curs.rowcount) + ' rows effected.') 

