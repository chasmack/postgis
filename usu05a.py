# USU OS Python Assignment 5a
#
# NDVI - Normalized Difference Vegetation Index

import gdal
from gdalconst import *
import numpy as np
import numpy.ma as ma
import time

gdal.UseExceptions()

SRC_RASTERFILE = 'data/usu04/aster.img'
DST_RASTERFILE = 'data/usu04/aster-ndvi.img'

DST_DATA_TYPE = np.float32
NO_DATA_VALUE = -99

# Register the raster driver and open the source data.
gdal.AllRegister()
srcDS = gdal.Open(SRC_RASTERFILE, GA_ReadOnly)
if srcDS is None:
    print('Can''t open source raster file ' + SRC_RASTERFILE)
    exit(1)

cols = srcDS.RasterXSize
rows = srcDS.RasterYSize
src_bands = srcDS.RasterCount

print('\nRaster file: ' + SRC_RASTERFILE)
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
dstDS = driver.Create(DST_RASTERFILE, cols, rows, 1, GDT_Float32)
if dstDS is None:
    print('Can''t open destination raster file ' + DST_RASTERFILE)
    exit(1)
dstBand = dstDS.GetRasterBand(1)

startTime = time.time()

# Initialize an array for the data.
data  = [None for n in range(src_bands + 1)]

valid_count = 0
ndvi_sum = 0.0

no_valid = some_valid = all_valid = 0

# Read all bands a block at a time.
for yoff in range(0, rows, yblock):
    for xoff in range(0, cols, xblock):

        xsize = min(cols - xoff, xblock)
        ysize = min(rows - yoff, yblock)
        block_size  = xsize * ysize

        # Read blocks from bands 2 & 3.
        for n in (2,3):
            srcBand = srcDS.GetRasterBand(n)
            data[n] = srcBand.ReadAsArray(xoff, yoff, xsize, ysize).astype(DST_DATA_TYPE)

        nir = data[3]
        red = data[2]

        # NDVI denominator.
        b = nir + red

        # Mask for divide by zero.
        mask = np.equal(b, 0)
        masked = np.count_nonzero(mask)
        unmasked = block_size - masked

        # Calculate ndvi = (nir - red) / (nir + red)
        if unmasked == 0:
            # No valid data in this block.
            ndvi = np.full((ysize, xsize), NO_DATA_VALUE)
            no_valid += 1

        elif masked > 0:
            # Some valid data, use a masked array.
            a = ma.array(nir-red, mask=mask, fill_value=NO_DATA_VALUE)
            ndvi = a/b
            valid_count += unmasked
            ndvi_sum += ndvi.sum()
            ndvi = ndvi.filled()
            some_valid += 1

        else:
            # All data in the block is valid.
            a = nir-red
            ndvi = a/b
            valid_count += block_size
            ndvi_sum += ndvi.sum()
            all_valid += 1

        dstBand.WriteArray(ndvi, xoff, yoff)

srcBand = data = None

# Finish up with the output raster.
dstBand.SetNoDataValue(NO_DATA_VALUE)
dstBand.FlushCache()
dstBand.GetStatistics(0, 1)

dstDS.SetGeoTransform(geotransform)
dstDS.SetProjection(projection)
gdal.SetConfigOption('HFA_USE_RRD', 'YES')
dstDS.BuildOverviews(overviewlist=[2, 4, 8, 16, 32, 64, 128])

pixel_count = rows * cols

print('\nValid blocks: NONE={0}  SOME={1}  ALL={2}'.format(no_valid, some_valid, all_valid))

print('\nValid Pixels/Total Pixels: {0:,d}/{1:,d}  ({2:.0f}%)'.format(
    valid_count, pixel_count, 100.0 * valid_count / pixel_count
))

print('\nNDVI mean: {0:.3f}'.format(ndvi_sum / valid_count))

endTime = time.time()
print('\ntime: {0:.3f} sec'.format(endTime - startTime))

# Done.
srcDS = None
exit(0)
