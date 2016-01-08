# USU OS Python Assignment 5a
#
# NDVI - Normalized Difference Vegetation Index

import gdal
from gdalconst import *
import numpy as np
import numpy.ma as ma
import time

gdal.UseExceptions()

src_rasterfile = 'data/usu04/aster.img'
dst_rasterfile = 'data/usu04/aster-ndvi.img'

# Register the raster driver and open the source data.
gdal.AllRegister()
srcDS = gdal.Open(src_rasterfile, GA_ReadOnly)
if srcDS is None:
    print('Can''t open source raster file ' + src_rasterfile)
    exit(1)

cols = srcDS.RasterXSize
rows = srcDS.RasterYSize
src_bands = srcDS.RasterCount

print('\nRaster file: ' + src_rasterfile)
print('\nRows x Columns x Bands: {0:d} x {1:d} x {2:d}'.format(rows, cols, src_bands))

projection = srcDS.GetProjection()
geotransform = srcDS.GetGeoTransform()
x0, dx, rx, y0, ry, dy = geotransform

print('\nTop-Left corner (x,y):  {0:12.4f}, {1:12.4f}'.format(x0, y0))
print('Pixel resolution (x,y): {0:12.4f}, {1:12.4f}'.format(dx, dy))
print('Axis rotation (x,y):    {0:12.4f}, {1:12.4f}'.format(rx, ry))

print()
for n in range(1, src_bands + 1):
    srcBand = srcDS.GetRasterBand(n)
    xblock, yblock = srcBand.GetBlockSize()
    datatype = gdal.GetDataTypeName(srcBand.DataType)
    color_interp = gdal.GetColorInterpretationName(srcBand.GetColorInterpretation())
    print('Band {0}: Block={1}x{2}  Type={3}  ColorInterp={4}'.format(
            n, xblock, yblock, datatype, color_interp))

# Open the output raster file.
driver = srcDS.GetDriver()
dstDS = driver.Create(dst_rasterfile, cols, rows, 1, GDT_Float32)
if dstDS is None:
    print('Can''t open destination raster file ' + dst_rasterfile)
    exit(1)
dstBand = dstDS.GetRasterBand(1)

startTime = time.time()

# Initialize an array for the data.
data  = [None for n in range(src_bands + 1)]

nonzeros = 0
ndvi_sum = 0.0

# Read all bands a block at a time.
for yoff in range(0, rows, yblock):
    for xoff in range(0, cols, xblock):

        xsize = min(cols - xoff, xblock)
        ysize = min(rows - yoff, yblock)

        for n in range(1, src_bands + 1):
            srcBand = srcDS.GetRasterBand(n)
            data[n] = srcBand.ReadAsArray(xoff, yoff, xsize, ysize)

        # One block from each band is loaded.

        # mask = np.greater(data[2]+data[3], 0)

        # nir = data[3].astype(np.float32)
        # red = data[2].astype(np.float32)

        a = (data[3]-data[2]).astype(np.float32)
        b = ma.masked_equal(data[3]+data[2], 0).astype(np.float32)

        ndvi = a/b
        dstBand.WriteArray(ndvi, xoff, yoff)

        # nir = data[3][mask].astype(np.float32)
        # red = data[2][mask].astype(np.float32)

        # nonzeros += mask.sum()
        # ndvi_sum += ((nir-red) / (nir+red)).sum()

srcBand = data = None

# Finish up with the output raster.
dstBand.SetNoDataValue(-99)
dstBand.FlushCache()
dstBand.GetStatistics(0, 1)

dstDS.SetGeoTransform(geotransform)
dstDS.SetProjection(projection)
gdal.SetConfigOption('HFA_USE_RRD', 'YES')
dstDS.BuildOverviews(overviewlist=[2, 4, 8, 16, 32, 64, 128])

pixels = rows * cols

print('\nNonZeros/Pixels: {0:d}/{1:d}  ({2:.0f}%)'.format(
    nonzeros, pixels, 100.0 * nonzeros / pixels
))

# print('\nNDIV mean: {0:.2f}'.format(ndvi_sum / nonzeros))

endTime = time.time()
print('\ntime: {0:.3f} sec'.format(endTime - startTime))

# Done.
srcDS = None
exit(0)
