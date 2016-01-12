
-- Format an azimuth in radians as a bearing in decimal degrees.

DROP FUNCTION IF EXISTS ST_AsBearing(float, integer);

CREATE OR REPLACE FUNCTION ST_AsBearing(
  param_azimuth float,
  param_ndigits integer DEFAULT 0)
RETURNS text AS
$$
import math

# ST_Azimuth return NULL when given tow identical points
azimuth = param_azimuth if param_azimuth is not None else 0.0
ndigits = param_ndigits if param_ndigits is not None else 0

quadrant = ('NE','SE','SW','NW')[int((azimuth // (math.pi/2.0)) % 4)]
degrees = math.degrees(math.asin(abs(math.sin(azimuth))))
width = ndigits + (2 if ndigits == 0 else 3)
bearing = '{0:s}{1:0{2:d}.{3:d}f}{4:s}'.format(quadrant[0], degrees, width, ndigits, quadrant[1])

return bearing

$$ LANGUAGE plpython3u IMMUTABLE
;

COMMENT ON FUNCTION ST_AsBearing(float, integer) IS
  'args: azimuth, ndigits - Return text representation of azimuth as a bearing in decimal degrees.';

SELECT azimuth::numeric(5,2),
  ST_AsBearing(radians(azimuth)) AS bearing,
  ST_AsBearing(radians(azimuth), 2) AS bearing_2
FROM (
  VALUES
    (-0.01),(0.0),(0.01),
    (45.0),
    (89.99),(90.0),(90.01),
    (135.0),
    (179.99),(180.0),(180.01),
    (225.0),
    (269.99),(270.0),(270.01),
    (315.0),
    (359.99),(360.0),(360.01)
) AS v (azimuth);

-- Transform geometry with 4-parameter similarity transform.
--
-- Given a0, b0, a1 & b1 for the forward transform -
--   x' = a1*x - b1*y + a0
--   y' = b1*x + a1*y + b0
--
-- In matrix notation -
--   X = R*x + t
--
-- The rotate/scale (r,k) matrix R -
--   k = sqrt(a1^2 + b1^2)
--   r = acos(a1/k) = asin(b1/k)
--
-- The inverse transform is -
--   x = inv(R)*(X - t) = inv(R)*X + (-1)*inv(R)*t

DROP FUNCTION IF EXISTS ST_Similarity(geometry,  float, float, float, float);

CREATE OR REPLACE FUNCTION ST_Similarity(
  geom geometry, a0 float, b0 float, a1 float, b1 float)
RETURNS geometry AS
$$
SELECT ST_Affine(geom, a1, -b1, b1, a1, a0, b0)
$$ LANGUAGE sql IMMUTABLE
;

COMMENT ON FUNCTION ST_Similarity(geometry, float, float, float, float) IS
  'args: geom, a0, b0, a1, b1 - Applies transform to uniformly scale, rotate and translate 2D geometry.';


DROP FUNCTION IF EXISTS ST_InverseSimilarity(geometry,  float, float, float, float);

CREATE OR REPLACE FUNCTION ST_InverseSimilarity(
  geom geometry, a0 float, b0 float, a1 float, b1 float)
RETURNS geometry AS
$$
WITH a AS (
    SELECT 1.0/(a1^2 + b1^2) AS idet
  ), b AS (
    SELECT
      -idet * ( a0*a1 + b0*b1) AS ia0,
      -idet * (-a0*b1 + a1*b0) AS ib0,
       idet *  a1 AS              ia1,
       idet * -b1 AS              ib1
    FROM a
  )
SELECT ST_Affine(geom, ia1, -ib1, ib1, ia1, ia0, ib0)
FROM b
$$ LANGUAGE sql IMMUTABLE;

COMMENT ON FUNCTION ST_InverseSimilarity(geometry, float, float, float, float) IS
  'args: geom, a0, b0, a1, b1 - Applies inverse transform to uniformly scale, rotate and translate 2D geometry.';

WITH a AS (
    SELECT
      radians(-1.5) AS rotate,
      0.95 AS scale
  ), b AS (
    SELECT
      ST_Transform(ST_PointFromText('POINT(-124.0 40.0)', 4326), 2225) AS geom,
      6000000.0 AS a0,
      2000000.0 AS b0,
      scale * cos(rotate) AS a1,
      scale * sin(rotate) AS b1
    FROM a
)
SELECT
  ST_AsEWKT(geom) AS geom1,
  ST_AsEWKT(
    ST_InverseSimilarity(
      ST_Similarity(geom, a0, b0, a1, b1), a0, b0, a1, b1)) AS geom2
FROM b


