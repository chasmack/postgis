
import gdal, ogr
from gdalconst import *
import time

rasterfile = 'data/usu04/aster.img'
shapefile  = 'data/usu04/sites.shp'

ogrDriver = ogr.GetDriverByName('ESRI Shapefile')
ogrDS = ogrDriver.Open(shapefile, 0)
if ogrDS is None:
    print('Can''t open shapefile ' + shapefile)
    exit(1)

# Read point coordinates (x,y) from the shapefile geometry into a list.
coords = [feat.GetGeometryRef().GetPoint_2D() for feat in ogrDS.GetLayer()]
ogrDriver = ogrDS = None

# Calculate x/y pixel offset from a coordinate (x,y) and GeoTransform.
def raster_offset(coord, geoxfm):
    xoff = int((coord[0] - geoxfm[0]) / geoxfm[1])
    yoff = int((coord[1] - geoxfm[3]) / geoxfm[5])
    return xoff, yoff

# Register the raster driver and open the data source.
rastDriver = gdal.GetDriverByName('HFA')
rastDriver.Register()
ds = gdal.Open(rasterfile, GA_ReadOnly)
if ds is None:
    print('Can''t open raster data file ' + rasterfile)
    exit(1)

cols = ds.RasterXSize
rows = ds.RasterYSize
bands = ds.RasterCount

print('\nrows x cols x bands: {0:d} x {1:d} x {2:d}'.format(rows, cols, bands))

geotransform = ds.GetGeoTransform()
x0, dx, rx, y0, ry, dy = geotransform

print('\ntop-left corner (x,y):  {0:12.4f}, {1:12.4f}'.format(x0, y0))
print('pixel resolution (x,y): {0:12.4f}, {1:12.4f}'.format(dx, dy))
print('axis rotation (x,y):    {0:12.4f}, {1:12.4f}'.format(rx, ry))

# Read one pixel at a time.
print('\nread one pixel at a time ...')
startTime = time.time()

for n in (1,2,3):
    band = ds.GetRasterBand(n)
    print('\nband %d:' % n)

    for p in coords:
        xoff, yoff = raster_offset(p, geotransform)
        data = band.ReadAsArray(xoff, yoff, 1, 1)
        print('  {0:.4f}, {1:.4f} => {2}'.format(p[0], p[1], *data))

    band = None

endTime = time.time()
print('\ntime: {0:.3f} sec'.format(endTime - startTime))

# Read entire band into an array.
print('\nread entire band ...')
startTime = time.time()

for n in (1,2,3):
    band = ds.GetRasterBand(n)
    print('\nband %d:' % n)

    data = band.ReadAsArray(0, 0, cols, rows)
    for p in coords:
        col, row = raster_offset(p, geotransform)
        print('  {0:.4f}, {1:.4f} => {2}'.format(p[0], p[1], data[row, col]))

    band = None

endTime = time.time()
print('\ntime: {0:.3f} sec'.format(endTime - startTime))

ds = None
