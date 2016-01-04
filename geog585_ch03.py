
# Trim the Philadelphia Base Layers shapefiles to the clipFeature/city_limits geometry,
# reproject the shapefile geometry from EPSG:4326 to EPSG:3857 and load resulting
# layers into PostGIS tables in the geog585_ch03 schema.
#
# The roads.shp geometry will be converted to wkbMultiLine in the process.

import ogr
import osr
import os
import glob

ogr.UseExceptions()

# PostGIS compatible geometry names.
def postgis_geom_type(type):
    return 'Geometry' if type == 0 else ogr.GeometryTypeToName(type).replace(' ', '')

src_dir = '../../Mapping/geog585/ch03/PhiladelphiaBaseLayers'
src_srid = 4326

dest_schema = 'geog585'
dest_srid = 3857

DSN = 'PG: host=localhost port=5432 dbname=postgis_scratch user=postgres password=pg'

trim_shapefile = 'clipFeature/city_limits.shp'

# SRS transform to project geometry: 4326 -> 3857
src_srs = osr.SpatialReference()
src_srs.ImportFromEPSG(src_srid)
dest_srs = osr.SpatialReference()
dest_srs.ImportFromEPSG(dest_srid)
srsTransform = osr.CoordinateTransformation(src_srs, dest_srs)

# Open a connection to PostgreSQL.
destConn = ogr.Open(DSN)
destDS = ogr.Open(DSN, 1)

# Driver for reading source shapefiles.
srcDriver = ogr.GetDriverByName('ESRI Shapefile')

# Get clipping geometry.
trimDS = srcDriver.Open(os.path.join(src_dir, trim_shapefile), 0)
trimLayer = trimDS.GetLayer()
trimFeature = trimLayer.GetFeature(0)
trimGeom = trimFeature.GetGeometryRef()

for shapefile in glob.glob(os.path.join(src_dir, '*.shp')):
    srcDS = srcDriver.Open(shapefile, 0)
    srcLayer = srcDS.GetLayer()
    srcLayer.SetSpatialFilter(trimGeom)

    layer_name = srcLayer.GetName()
    geom_type = srcLayer.GetGeomType()
    print('{0}: {1}'.format(layer_name, postgis_geom_type(geom_type)))

    # Common layer format.
    qstr = """
    DROP TABLE IF EXISTS {schema}.{layer};
    CREATE TABLE {schema}.{layer} (
      gid serial NOT NULL,
      osm_id bigint,
      name character varying(48),
      type character varying(48),
      geom geometry({geom_type}, {srid}),
      CONSTRAINT {layer}_pkey PRIMARY KEY (gid)) WITH (OIDS=FALSE);
    """.format(schema=dest_schema, layer=layer_name, geom_type=postgis_geom_type(geom_type), srid=dest_srid)

    # Special processing for specific layers.
    if layer_name == 'roads':
        qstr += """
        ALTER TABLE {schema}.{layer}
          ADD COLUMN ref character varying(48),
          ADD COLUMN oneway integer,
          ADD COLUMN bridge integer,
          ALTER COLUMN geom SET DATA TYPE geometry(MultiLineString, {srid});
        """.format(schema=dest_schema, layer=layer_name, srid=dest_srid)

    elif layer_name == 'places':
        qstr += """
        ALTER TABLE {schema}.{layer}
          ADD COLUMN population integer;
        """.format(schema=dest_schema, layer=layer_name)

    elif layer_name == 'waterways':
        qstr += """
        ALTER TABLE {schema}.{layer}
          ADD COLUMN width integer;
        """.format(schema=dest_schema, layer=layer_name)

    destDS.ExecuteSQL(qstr)
    destLayer = destDS.GetLayerByName(dest_schema + '.' + layer_name)
    destFeatureDefn = destLayer.GetLayerDefn()

    for srcFeature in srcLayer:
        destFeature = ogr.Feature(destFeatureDefn)

        for field in ['osm_id', 'name', 'type']:
            destFeature.SetField(field,
                srcFeature.GetField(srcFeature.GetFieldIndex(field)))

        geom = srcFeature.GetGeometryRef()
        geom.Transform(srsTransform)

        # Extras for specific layers
        if layer_name == 'roads':
            for field in ['ref', 'oneway', 'bridge']:
                destFeature.SetField(field, srcFeature.GetField(srcFeature.GetFieldIndex(field)))

            # Convert line strings to multi line strings.
            geom = ogr.ForceToMultiLineString(geom)

        elif layer_name == 'waterways':
            for field in ['width']:
                destFeature.SetField(field, srcFeature.GetField(srcFeature.GetFieldIndex(field)))

        elif layer_name == 'places':
            for field in ['population']:
                destFeature.SetField(field,  srcFeature.GetField(srcFeature.GetFieldIndex(field)))

        destFeature.SetGeometry(geom)
        destLayer.CreateFeature(destFeature)

        srcFeature.Destroy()
        destFeature.Destroy()

    srcDS.Destroy()

# Change roads columns 'oneway' and 'bridge' to boolean.
qstr = """
ALTER TABLE {schema}.roads
ALTER oneway TYPE boolean USING oneway::boolean,
ALTER bridge TYPE boolean USING bridge::boolean;
""".format(schema=dest_schema)
destDS.ExecuteSQL(qstr)

trimFeature.Destroy()
trimDS.Destroy()

destDS.Destroy()