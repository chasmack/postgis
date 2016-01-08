
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

return '{0:s}{1:0{2:d}.{3:d}f}{4:s}'.format(quadrant[0], degrees, width, ndigits, quadrant[1])

$$ LANGUAGE plpython3u IMMUTABLE
;

COMMENT ON FUNCTION ST_AsBearing(float, integer) IS
  'args: azimuth, ndigits - Return text representation of azimuth as a bearing in decimal degrees.';

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
SELECT ST_Affine(geom, ia1, -ib1, ib1, ia1, ia0, ib0)
FROM (
  SELECT 1.0/(a1^2 + b1^2) AS idet
) AS a,
LATERAL (
  SELECT
    -idet * ( a0*a1 + b0*b1) AS ia0,
    -idet * (-a0*b1 + a1*b0) AS ib0,
     idet *  a1 AS              ia1,
     idet * -b1 AS              ib1
) AS b
$$ LANGUAGE sql IMMUTABLE
;

COMMENT ON FUNCTION ST_InverseSimilarity(geometry, float, float, float, float) IS
  'args: geom, a0, b0, a1, b1 - Applies inverse transform to uniformly scale, rotate and translate 2D geometry.';

