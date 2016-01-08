
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


-- Transform geometry with 4-parameter inverse similarity transform.
--
-- Given a0, b0, a1 & b1 for the forward transform -
--   x' = a1*x - b1*y + a0
--   y' = b1*x + a1*y + b0
--
-- In martix notation -
--   X = R*x + t
--
-- The inverse transform is -
--   x = inv(R)*(X - t) = inv(R)*X + (-1)*inv(R)*t

DROP FUNCTION IF EXISTS ST_SimilarityInverse(geometry,
  double precision, double precision, double precision, double precision);

CREATE OR REPLACE FUNCTION ST_SimilarityInverse(
  geom geometry,
  a0 double precision, b0 double precision,
  a1 double precision, b1 double precision)
RETURNS geometry AS
$$
SELECT ST_Affine(geom, inv_a1, -inv_b1, inv_b1, inv_a1, inv_a0, inv_b0)
FROM (
  SELECT 1.0/(a1^2 + b1^2) AS inv_det
) AS a,
LATERAL (
  SELECT
    -inv_det * ( a0*a1 + b0*b1) AS inv_a0,
    -inv_det * (-a0*b1 + a1*b0) AS inv_b0,
     inv_det *  a1 AS inv_a1,
     inv_det * -b1 AS inv_b1
) AS b
$$ LANGUAGE sql IMMUTABLE
;

COMMENT ON FUNCTION ST_Similarity(geometry, float, float, float, float) IS
  'args: geom, a0, b0, a1, b1 - Applies 2-d inverse similarity transform to uniformly scale, rotate and translate geometry.';

