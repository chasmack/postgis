# USU OS Python Assignment 4b
#
# Write a script to calculate the average pixel value for the bands in aster.img.
# Read and process the data one block at a time. Do the calculation two ways:
# first including zeros in the calculation and then ignoring zeros.

import gdal
from gdalconst import *
import numpy as np
import time

gdal.UseExceptions()

rasterfile = 'data/usu04/aster.img'
# rasterfile = 'data/usu04/usgs-hoopa.tif'
# rasterfile = 'data/usu04/naip-stapp.tif'

# Register the raster driver and open the data source.
# rastDriver = gdal.GetDriverByName('HFA')
gdal.AllRegister()
ds = gdal.Open(rasterfile, GA_ReadOnly)
if ds is None:
    print('Can''t open raster data file ' + rasterfile)
    exit(1)

cols = ds.RasterXSize
rows = ds.RasterYSize
bands = ds.RasterCount

print('\nRaster file: ' + rasterfile)
print('\nRows x Columns x Bands: {0:d} x {1:d} x {2:d}'.format(rows, cols, bands))

print()
for n in range(1, bands+1):
    band = ds.GetRasterBand(n)
    xblock, yblock = band.GetBlockSize()
    datatype = gdal.GetDataTypeName(band.DataType)
    color_interp = gdal.GetColorInterpretationName(band.GetColorInterpretation())
    print('Band {0}: Block={1}x{2}  Type={3}  ColorInterp={4}'.format(
            n, xblock, yblock, datatype, color_interp))

startTime = time.time()

# Initialize arrays for the data and stats lists.
data  = [None for n in range(bands+1)]
stats = [None for n in range(bands+1)]
for n in range(1, bands+1):
    stats[n] = {'sum': 0.0, 'nonzero': 0}

# Read all bands a block at a time.
for yoff in range(0, rows, yblock):
    for xoff in range(0, cols, xblock):

        xsize = min(cols - xoff, xblock)
        ysize = min(rows - yoff, yblock)

        for n in range(1, bands+1):
            band = ds.GetRasterBand(n)
            data[n] = band.ReadAsArray(xoff, yoff, xsize, ysize)

        # One block from each band is loaded.
        for n in range(1, bands+1):
            stats[n]['sum'] += data[n].astype(np.float).sum()
            stats[n]['nonzero'] += np.greater(data[n], 0).sum()

band = data = None

pixel_count = rows * cols
fmt = 'Band {0}: Sum={1:,.0f}  Pixels={2:,d}  NonZeroPixels={3:,d}  ' \
    + 'Mean={4:.2f}  NonZeroMean={5:.2f}'

print()
for n in range(1, bands+1):
    print(fmt.format(
        n, stats[n]['sum'], pixel_count, stats[n]['nonzero'],
        stats[n]['sum'] / pixel_count,
        stats[n]['sum'] / stats[n]['nonzero']
    ))

endTime = time.time()
print('\ntime: {0:.3f} sec'.format(endTime - startTime))

# Done.
ds = None
exit(0)
