# USU OS Python Assignment 4a
#
# Print the pixel values for all three bands of aster.img at
# the points contained in sites.shp.

import gdal, ogr
from gdalconst import *
import time
import utils

ogr.UseExceptions()

aster_rasterfile = 'data/usu04/aster.img'

sites_shapefile  = 'data/usu04/sites.shp'
sites_schema = 'usu04'
sites_layername = 'sites'
sites_srid = 32612

DSN = 'PG: host=localhost dbname=postgis_scratch user=postgres password=pg'

# Open a connection to PostgreSQL.
pgDS = ogr.Open(DSN, 1)

# Open the sites shapefile.
shpDriver = ogr.GetDriverByName('ESRI Shapefile')
sitesDS = shpDriver.Open(sites_shapefile, 0)
if sitesDS is None:
    print('Can''t open shapefile ' + sites_shapefile)
    exit(1)

# Create a PostGIS table to hold the sites data.
qstr = """
    DROP TABLE IF EXISTS {schema}.{layer};
    CREATE TABLE {schema}.{layer} (
      gid serial NOT NULL,
      site_id integer,
      cover character varying(48),
      geom geometry({geomtype}, {srid}),
      CONSTRAINT {layer}_pkey PRIMARY KEY (gid))
    WITH (OIDS=FALSE);
    """.format(schema=sites_schema, layer=sites_layername, geomtype='Point', srid=sites_srid)
pgDS.ExecuteSQL(qstr)

# Copy features from the sites shapefile to the PostGIS table.
pgLayer = pgDS.GetLayerByName(sites_schema + '.' + sites_layername)
pgFeatureDefn = pgLayer.GetLayerDefn()

for feat in sitesDS.GetLayer():
    pgFeature = ogr.Feature(pgFeatureDefn)
    pgFeature.SetField('site_id', feat.GetField('id'))
    pgFeature.SetField('cover', feat.GetField('cover'))
    pgFeature.SetGeometry(feat.GetGeometryRef())

    pgLayer.CreateFeature(pgFeature)

# Done with the shapefile.
shpDriver = sitesDS = None

# Register the raster driver and open the data source.
rastDriver = gdal.GetDriverByName('HFA')
rastDriver.Register()
ds = gdal.Open(aster_rasterfile, GA_ReadOnly)
if ds is None:
    print('Can''t open raster data file ' + aster_rasterfile)
    exit(1)

cols = ds.RasterXSize
rows = ds.RasterYSize
bands = ds.RasterCount

print('\nRaster file: ' + aster_rasterfile)
print('Rows x Columns x Bands: {0:d} x {1:d} x {2:d}'.format(rows, cols, bands))

geotransform = ds.GetGeoTransform()
x0, dx, rx, y0, ry, dy = geotransform

print('\nTop-Left corner (x,y):  {0:12.4f}, {1:12.4f}'.format(x0, y0))
print('Pixel resolution (x,y): {0:12.4f}, {1:12.4f}'.format(dx, dy))
print('Axis rotation (x,y):    {0:12.4f}, {1:12.4f}'.format(rx, ry))

# Read point coordinates (x,y) and cover from the sites geometry into a list.
qstr = """

SELECT site_id, cover, geom,
  ST_AsBearing(ST_Azimuth(garden_city, geog)) AS bearing,
  ST_Distance(garden_city, geog) / 1000 AS dist_km
FROM {schema}.{layer},
  LATERAL (
    -- using geography to give true bearings
    SELECT
      ST_PointFromText('POINT(-111.393384 41.946642)', 4326)::Geography AS garden_city,
      ST_Transform(geom, 4326)::Geography AS geog
  ) AS a
ORDER BY dist_km;

""".format(schema=sites_schema, layer=sites_layername)

pgLayer = pgDS.ExecuteSQL(qstr)

sites = []
for feat in pgLayer:
    coords = feat.GetGeometryRef().GetPoint_2D()
    sites.append({
        'site_id' : feat.GetField('site_id'),
        'coords'  : coords,
        'cover'   : feat.GetField('cover'),
        'dist_km' : feat.GetField('dist_km'),
        'bearing' : feat.GetField('bearing'),
        'offset'  : utils.get_raster_offset(coords, geotransform),
        'data'    : [],
    })
pgDS.ReleaseResultSet(pgLayer)

startTime = time.time()

READ_ENTIRE_BAND = False

if READ_ENTIRE_BAND:
    print('\nReading entire band ...')
else:
    print('\nReading one pixel at a time ...')

for n in (1,2,3):

    band = ds.GetRasterBand(n)

    if (READ_ENTIRE_BAND):

        # Read entire band into an array.
        data = band.ReadAsArray(0, 0, cols, rows)
        for site in sites:
            col, row = site['offset']
            site['data'].append(data[row, col])

    else:

        # Read one pixel at a time.
        for site in sites:
            xoff, yoff = site['offset']
            data = band.ReadAsArray(xoff, yoff, 1, 1)
            site['data'].append(data[0, 0])

    band = data = None


print('\n<id>: <northing>, <easting>, <bearing> <distance>: <cover> = (<b1>, <b2>, <b3>).')
print('\nCoordinates are UTM 12N Northing, Easting (meters).')
print('Bearing and Distance are straight line from Garden City, UT.')
print()

for site in sites:

    x, y=  site['coords']
    fmt = '{0:2d}: {1:.4f}, {2:.4f}, {3:s} {4:5.2f} km:  {5:>6s} = ({6:2d}, {7:2d}, {8:2d})'

    print(fmt.format(
        site['site_id'], y, x, site['bearing'], site['dist_km'],
        site['cover'], *site['data']
    ))

endTime = time.time()
print('\ntime: {0:.3f} sec'.format(endTime - startTime))

# Done.
ds = None
exit(0)
