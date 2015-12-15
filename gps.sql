
--
-- lpt_read - read local pnezd points file
--

DROP FUNCTION IF EXISTS gps.lpt_read(text);

CREATE OR REPLACE FUNCTION gps.lpt_read(
  IN filename text,
  
  OUT lpt_name text,
  OUT lpt_x text,
  OUT lpt_y text,
  OUT lpt_z text,
  OUT lpt_desc text
  
) RETURNS SETOF record AS
$$
  with open(filename) as f:
    for line in f:
      p, n, e, z, d = line.strip().split(',', 4)
      result = {}
      result['lpt_name'] = p
      result['lpt_x'] = e
      result['lpt_y'] = n
      result['lpt_z'] = z
      result['lpt_desc'] = d

      yield result

$$ LANGUAGE plpython3u
;

--
-- gpx_read - read gpx waypoints
--

DROP FUNCTION IF EXISTS gps.gpx_read(text);

CREATE OR REPLACE FUNCTION gps.gpx_read(
  IN filename text,
  
  OUT wpt_lon text,
  OUT wpt_lat text,
  OUT wpt_ele text,
  OUT wpt_name text,
  OUT wpt_cmt text,
  OUT wpt_desc text,
  OUT wpt_time text,
  OUT wpt_symbol text,
  OUT wpt_samples text
  
) RETURNS SETOF record AS
$$
  import xml.etree.ElementTree as etree

  ns = {
    'gpx': 'http://www.topografix.com/GPX/1/1',
    'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
    'wpt1': 'http://www.garmin.com/xmlschemas/WaypointExtension/v1',
    'ctx': 'http://www.garmin.com/xmlschemas/CreationTimeExtension/v1'
  }

  etree.register_namespace('', 'http://www.topografix.com/GPX/1/1')
  etree.register_namespace('gpxx', 'http://www.garmin.com/xmlschemas/GpxExtensions/v3')
  etree.register_namespace('wpt1', 'http://www.garmin.com/xmlschemas/WaypointExtension/v1')
  etree.register_namespace('ctx', 'http://www.garmin.com/xmlschemas/CreationTimeExtension/v1')

  gpx = etree.parse(filename).getroot()
  for e in gpx.findall('gpx:wpt', ns):
    result = {}
    result['wpt_lat'] = e.get('lat')
    result['wpt_lon'] = e.get('lon')
    result['wpt_ele'] = e.findtext('gpx:ele', namespaces=ns)
    result['wpt_name'] = e.findtext('gpx:name', namespaces=ns)
    result['wpt_cmt'] = e.findtext('gpx:cmt', namespaces=ns)
    result['wpt_desc'] = e.findtext('gpx:desc', namespaces=ns)
    result['wpt_time'] = e.findtext('gpx:time', namespaces=ns)
    result['wpt_symbol'] = e.findtext('gpx:sym', namespaces=ns)
    result['wpt_samples'] = e.findtext('.//wpt1:Samples', default='0', namespaces=ns)
    
    yield result

$$ LANGUAGE plpython3u
;

--
-- gpx_write - write waypoints to a gpx file.
--

DROP FUNCTION IF EXISTS gps.gpx_write(text, text);

CREATE OR REPLACE FUNCTION gps.gpx_write(
  IN tablename text,
  IN filename text,
  OUT result text
) RETURNS text AS
$$
  import xml.etree.ElementTree as etree
  import xml.dom.minidom as minidom
  from datetime import datetime, timedelta
  import pytz

  ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
  etree.register_namespace('', 'http://www.topografix.com/GPX/1/1')

  gpx_attrib = {
    'creator': 'Python pyloc', 'version': '1.1',
    'xsi:schemaLocation': 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd',
    'xmlns': 'http://www.topografix.com/GPX/1/1',
    'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance'
  }

  # Get the ISO 8601 date-time string.
  time = datetime.now(pytz.utc)
  time -= timedelta(microseconds=time.microsecond)    # get rid of the microseconds
  time = time.isoformat()

  gpx = etree.Element('gpx', attrib=gpx_attrib)
  meta = etree.SubElement(gpx, 'metadata')
  link = etree.SubElement(meta, 'link', attrib={'href': 'http://www.asis.com/users/chas.mack'})
  etree.SubElement(link, 'text').text = 'Charles Mack'
  etree.SubElement(meta, 'time').text = time

  q = """
    SELECT name, ST_X(pt) AS lon, ST_Y(pt) AS lat, description
    FROM
      %s AS wpt,
      LATERAL
      ST_Transform(wpt.geom, 4326) AS pt;
  """ % tablename

  npts = 0;
  for row in plpy.cursor(q):
    npts += 1
    coords = {'lat': '%.8f' % row['lat'], 'lon': '%.8f' % row['lon']}
    wpt = etree.SubElement(gpx, 'wpt', attrib=coords)
    etree.SubElement(wpt, 'ele').text = '{0:.4f}'.format(0.0)
    etree.SubElement(wpt, 'time').text = time
    etree.SubElement(wpt, 'name').text = row['name']
    etree.SubElement(wpt, 'cmt').text = row['description']
    etree.SubElement(wpt, 'desc').text = row['description']
    etree.SubElement(wpt, 'sym').text = 'Waypoint'

  # Reparse the etree gpx with minidom and write pretty xml.
  dom = minidom.parseString(etree.tostring(gpx, encoding='utf-8'))
  with open(filename, 'w') as f:
    dom.writexml(f, addindent='  ', newl='\n', encoding='utf-8')
  
  return filename + ': ' + str(npts) + ' waypoints.'

$$ LANGUAGE plpython3u
;

--
-- lpt_transform - four-parameter rigid transform for local points
--

DROP FUNCTION IF EXISTS gps.lpt_transform(float, float, float ARRAY[4]);

CREATE OR REPLACE FUNCTION gps.lpt_transform(
  IN x float,
  IN y float,
  IN params float ARRAY[4],
  
  OUT xf_x float,
  OUT xf_y float
) RETURNS record AS
$$

  a0, b0, a1, b1 = params
  return (a0 + a1*x - b1*y, b0 + b1*x + a1*y)

$$ LANGUAGE plpython3u
;

--
-- lpt_transform_inv - inverse four-parameter rigid transform for local points.
--

DROP FUNCTION IF EXISTS gps.lpt_transform_inv(float, float, float ARRAY[4]);

CREATE OR REPLACE FUNCTION gps.lpt_transform_inv(
  IN x float,
  IN y float,
  IN params float ARRAY[4],
  
  OUT xi_x float,
  OUT xi_y float
) RETURNS record AS
$$

  a0, b0, a1, b1 = params
  k2 = a1**2 + b1**2
  a2 = a1/k2
  b2 = -b1/k2
  return (a2*(x-a0) - b2*(y-b0), b2*(x-a0) + a2*(y-b0))

$$ LANGUAGE plpython3u
;

--
-- Read a gpx waypoints file.
--

DROP TABLE IF EXISTS gps.stapp_wpt;

SELECT wpt_name AS name, wpt_lon AS lon, wpt_lat AS lat,
  upper(wpt_desc) AS description
INTO gps.stapp_wpt
FROM gps.gpx_read('c:/temp/gps/data/stapp_wpt.gpx') AS wpt
;

--
-- Add primary key and geometry columns to the waypoints table and populate
-- the geometry column with point coordinates transformed to EPSG:26941.
--

ALTER TABLE gps.stapp_wpt ADD COLUMN gid serial;
UPDATE gps.stapp_wpt SET gid = DEFAULT;
ALTER TABLE gps.stapp_wpt ADD PRIMARY KEY (gid);

SELECT * FROM gps.stapp_wpt ORDER BY gid;

ALTER TABLE gps.stapp_wpt ADD COLUMN geom geometry;
UPDATE gps.stapp_wpt
SET geom = ST_Transform(ST_PointFromText('POINT(' || lon || ' ' || lat || ')', 4326), 26941)
;

SELECT gid, name, ST_AsEWKT(geom) as geom FROM gps.stapp_wpt ORDER BY gid;

--
-- Read a local pnezd points file.
--

DROP TABLE IF EXISTS gps.stapp_lpt;

SELECT lpt_name AS name, lpt_x AS x, lpt_y AS y, lpt_z AS z,
  upper(lpt_desc) AS description
INTO gps.stapp_lpt
FROM gps.lpt_read('c:/temp/gps/data/stapp_pts.txt') AS lpt
;

SELECT * FROM gps.stapp_lpt;

--
-- Add primary key and geometry columns to the local points table and populate
-- the geometry column with local point coordinates transformed to EPSG:26941.
--

ALTER TABLE gps.stapp_lpt ADD COLUMN gid serial;
UPDATE gps.stapp_lpt SET gid = DEFAULT;
ALTER TABLE gps.stapp_lpt ADD PRIMARY KEY (gid);

ALTER TABLE gps.stapp_lpt ADD COLUMN geom geometry(POINT, 26941);
UPDATE gps.stapp_lpt AS lpt SET geom = pnt
  FROM
    gps.stapp_lpt AS a,
    LATERAL
    gps.lpt_transform(a.x::float, a.y::float,
      '{1848247.9513, 642758.3238, 0.3047285467, -0.0066275507}') AS b,
    LATERAL
    ST_SetSRID(ST_MakePoint((b).xf_x, (b).xf_y), 26941) as pnt
  WHERE lpt.gid = a.gid
;

SELECT gid, name, ST_AsEWKT(geom) as geom FROM gps.stapp_lpt ORDER BY gid;

--
-- Write transformed local coordinates to a gpx file.
--

SELECT gps.gpx_write('gps.stapp_lpt', 'c:/temp/gps/stapp_lpt.gpx');

--
-- Forward transform from local to EPSG:26941 (nad83 ca01 meters).
--

SELECT name, (lpt).xf_x AS x, (lpt).xf_y AS y
FROM (
  SELECT name, gps.lpt_transform(x::float, y::float,
    '{1848247.9513, 642758.3238, 0.3047285467, -0.0066275507}') AS lpt
  FROM gps.stapp_lpt
) AS a
;

--
-- Forward transform using a LATERAL join.
--

SELECT name, (lpt).xf_x AS x, (lpt).xf_y AS y
FROM
  gps.stapp_lpt AS a,
  LATERAL
  gps.lpt_transform(a.x::float, a.y::float,
    '{1848247.9513, 642758.3238, 0.3047285467, -0.0066275507}') AS lpt
;

--
-- Forward transform of local coordinates to EPSG:4326 lon/lat.
--

SELECT name, x, y, z, description,
  ST_AsEWKT(ST_Transform(ST_SetSRID(ST_MakePoint((lpt).xf_x, (lpt).xf_y), 26941), 4326))
FROM
  gps.stapp_lpt AS a,
  LATERAL
  gps.lpt_transform(a.x::float, a.y::float,
    '{1848247.9513, 642758.3238, 0.3047285467, -0.0066275507}') AS lpt
;

--
-- Inverse transform from EPSG:26941 to local coordinates (us-ft).
--

SELECT name, (lpt).xi_x AS x, (lpt).xi_y AS y
FROM
  gps.stapp_wpt AS a,
  LATERAL
  gps.lpt_transform_inv(ST_X(a.geom), ST_Y(a.geom),
    '{1848247.9513, 642758.3238, 0.3047285467, -0.0066275507}') AS lpt
;
