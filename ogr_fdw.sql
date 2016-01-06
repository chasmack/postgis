CREATE SERVER fuel_server
  FOREIGN DATA WRAPPER ogr_fdw
  OPTIONS (
    datasource 'c:/temp/fuel.shp',
    format 'ESRI Shapefile' );

CREATE FOREIGN TABLE geog585.ft_fuel (
  fid integer,
  geom geometry,
  osm_id bigint,
  timestamp varchar,
  name varchar,
  type varchar )
  SERVER fuel_server
  OPTIONS ( layer 'fuel' );

DROP FOREIGN TABLE geog585.ft_fuel;

DROP SERVER fuel_server;