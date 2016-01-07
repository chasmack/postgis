
import math

def brg(param_azimuth=None, param_ndigits=None):


    # ST_Azimuth return NULL when given tow identical points
    azimuth = param_azimuth if param_azimuth is not None else 0.0
    ndigits = param_ndigits if param_ndigits is not None else 0

    quadrant = ('NE','SE','SW','NW')[int((azimuth // (math.pi/2.0)) % 4)]
    degrees = math.degrees(math.asin(abs(math.sin(azimuth))))
    width = ndigits + (2 if ndigits == 0 else 3)

    bearing = '{0:s}{1:0{2:d}.{3:d}f}{4:s}'.format(
            quadrant[0], degrees, width, ndigits, quadrant[1])

    return bearing

for azi in (0,1,45,89,90,91,135,179,180,185,225,265,270,275,315,355,360,365,-355):

    print('{0:.0f} => {1:s}'.format(azi, brg(math.radians(azi))))