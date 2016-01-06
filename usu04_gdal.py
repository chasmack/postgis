
import gdal, ogr
from gdalconst import *
import time

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
    pgFeature.SetFID(feat.GetField('id'))
    pgFeature.SetField('cover', feat.GetField('cover'))
    pgFeature.SetGeometry(feat.GetGeometryRef())

    pgLayer.CreateFeature(pgFeature)

# Done with the shapefile.
shpDriver = sitesDS = None

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

print('\nrows x cols x bands: {0:d} x {1:d} x {2:d}'.format(rows, cols, bands))

geotransform = ds.GetGeoTransform()
x0, dx, rx, y0, ry, dy = geotransform

print('\ntop-left corner (x,y):  {0:12.4f}, {1:12.4f}'.format(x0, y0))
print('pixel resolution (x,y): {0:12.4f}, {1:12.4f}'.format(dx, dy))
print('axis rotation (x,y):    {0:12.4f}, {1:12.4f}'.format(rx, ry))

# Read point coordinates (x,y) and cover from the sites geometry into a list.
qstr = """
SELECT cover, geom
FROM {schema}.{layer} AS a
ORDER BY cover, ST_Y(geom) DESC;
""".format(schema=sites_schema, layer=sites_layername)
pgLayer = pgDS.ExecuteSQL(qstr)

sites = []
for feat in pgLayer:
    coords = feat.GetGeometryRef().GetPoint_2D()
    sites.append({
        'coords': coords,
        'cover' : feat.GetField('cover'),
        'offset': get_raster_offset(coords, geotransform),
        'data' : [],
    })
pgDS.ReleaseResultSet(pgLayer)

startTime = time.time()

READ_ENTIRE_BAND = False

if READ_ENTIRE_BAND:
    print('\nreading entire band ...\n')
else:
    print('\nreading one pixel at a time ...\n')

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

for site in sites:
    x, y = site['coords']
    print('{0:.4f}, {1:.4f}:  {2:>6s} = ({3:2d}, {4:2d}, {5:2d})'.format(
            x, y, site['cover'], *site['data']))

endTime = time.time()
print('\ntime: {0:.3f} sec'.format(endTime - startTime))

# Done.
ds = None
exit(0)
