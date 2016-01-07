
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

