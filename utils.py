
import gdal

# Calculate x/y pixel offset from a coordinate (x,y) and GeoTransform.
def get_raster_offset(coord, geoxfm):
    xoff = int((coord[0] - geoxfm[0]) / geoxfm[1])
    yoff = int((coord[1] - geoxfm[3]) / geoxfm[5])
    return xoff, yoff

# Calculate x/y pixel coordinate from an offset (x,y) and GeoTransform.
def get_raster_coord(offset, geoxfm):
    x = offset[0] * geoxfm[1] + geoxfm[0]
    y = offset[1] * geoxfm[5] + geoxfm[3]
    return x, y

