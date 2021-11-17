#!/usr/bin/env python
# -*- coding: utf-8 -*-

####################################################################################################
####################################################################################################
#Este script realiza las siguientes funciones:
#1. Descargar datos MODIS de reflectancia de las bandas 1 a 7 (Producto MOD09A1)
#2. Reproyectar los datos a EPSG:4326
#3. Generar Mosaicos de las bandas RED y MIR para Argentina, Uruguay y Paraguay
#4. Calcular NDWI
#############################################01-04-2019#############################################
####################################################################################################

from datetime import datetime, timedelta
from funciones import descarga, mosaico, filldata, recorte, subirtiff
import os
import glob
import sys

tiles = ["h11v11","h11v12","h12v10","h12v11","h12v12","h12v13","h13v11","h13v12","h13v13","h13v14","h14v14"]

url = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/" #Dirección de descarga de los datos
prods = ["MOD09A1"] #Producto requeridos
#appkey = "51B6A2FE-4FC6-11E9-84A2-8E39E106C194" #Clave de autenticación al servidor de descarga
appkey = "ai5lLnJ1YmlvOmFuSjFZbWx2UUdOdmJtRmxMbWR2ZGk1aGNnPT06MTYyODI1MjU2MTpiYTI4ZmMyZDMyNjc0Y2MzYjc0NmFkODUzMWJjOWI1YmNkMmNhMTA5"

path = "/mnt/datos/Repositorio/sancor/" #Directorio principal de procesamiento
path_descarga = path+"datos/crudos/" #Directorio para descarga de información
path_proc = path+"procesamiento/" #Directorio para almacenar datos temporales de procesamiento
path_xml = path+"datos/xml/" #Directorio con archivos xml para reproyección de las imágenes
path_pymodis = "/home/asolarte/ProyectoCalidadAgua/pyModis-2.0.9/scripts/" #Directorio de pyModis para reproyectar imágenes
path_mrt = "/home/asolarte/ProyectoCalidadAgua/MRT/" #Directorio MODIS REPROJECTION TOOL - MRT
path_indices = "/mnt/datos/Repositorio/sancor/indices/" #Directorio donde se almacenan los índices calculados
shp = path+"datos/mascara/mask.shp" #Archivo shapefile con máscara de zona de interés
red_nodata = -28672
mir_nodata = -28672
#factor_red = 0.0001 #Factor de escala para el producto MOD11A2
#factor_mir = 0.0001 #Factor de escala para el producto MOD11A2
resx,resy = 0.005086568914507,0.005086568914507 #Resolución para remuestreo de datos de temperatura

#Estilos
estilo_ndwi = "ndwi"

#Workspace
ws_ndwi = "ndwi"

#Datos Conexión
user = "xxx" #Usuario
passw = "xxx" #Contraseña
ipgeo = "xx.xx.xx.xx" #IP del servidor
port = "8080" #Puerto


#Crear rutas para procesamiento de datos
if not os.path.exists(path_proc+"red_temp/"):os.mkdir(path_proc+"red_temp/")
if not os.path.exists(path_proc+"mir_temp/"):os.mkdir(path_proc+"mir_temp/")
if not os.path.exists(path_proc+"mosaicos/"):os.mkdir(path_proc+"mosaicos/")
if not os.path.exists(path_proc+"recortes/"):os.mkdir(path_proc+"recortes/")
#Crear rutas para almacenamiento de información
if not os.path.exists(path_indices+"ndwi/"):os.mkdir(path_indices+"ndwi/")

fecha = sys.argv[1] #Fecha de procesamiento

#Descargar datos
descarga(url,appkey,tiles,prods,fecha,path_descarga,path_xml) 

#Reproyectar capas de vegetación y temperatura superficial
lista_ndwi = glob.glob("%s/%s/%s/%s/*%s*.hdf"%(path_descarga,prods[0],fecha[0:4],fecha[4:7],fecha))

#Reproyectar capas de vegetación y temperatura superficial
for w in lista_ndwi:
	#RED
	salida_red = path_proc+"red_temp/"+os.path.basename(w)[:-4]+".tif"
	os.system(path_pymodis+'modis_convert.py -s "( 1 0 0 0 0 0 0 0 0 0 0 0)" -o '+salida_red+'  -m "'+path_mrt+'" '+w)
	#MIR
	salida_mir = path_proc+"mir_temp/"+os.path.basename(w)[:-4]+".tif"
	os.system(path_pymodis+'modis_convert.py -s "( 0 0 0 0 0 1 0 0 0 0 0 0)" -o '+salida_mir+'  -m "'+path_mrt+'" '+w)
	
#Realizar el Mosaico de las imágenes
mosaico(glob.glob(path_proc+"red_temp/*"+fecha+".*.tif"),path_proc+"mosaicos/mosaico_"+fecha+"_red.tif",red_nodata,resx,resy)
mosaico(glob.glob(path_proc+"mir_temp/*"+fecha+".*.tif"),path_proc+"mosaicos/mosaico_"+fecha+"_mir.tif",mir_nodata,resx,resy)

#Interpolación de líneas faltantes
red_fill = path_proc+"mosaicos/mosaico_"+fecha+"_red_fill.tif"
mir_fill = path_proc+"mosaicos/mosaico_"+fecha+"_mir_fill.tif"

filldata(path_proc+"mosaicos/mosaico_"+fecha+"_red.tif",red_fill)
filldata(path_proc+"mosaicos/mosaico_"+fecha+"_mir.tif",mir_fill)

#Recorte de zona de interés
red_rec500 = path_proc+"recortes/red_"+fecha+"_500m.tif"
mir_rec500 = path_proc+"recortes/mir_"+fecha+"_500m.tif"

recorte(shp,resx,resy,red_fill,red_rec500,red_nodata)
recorte(shp,resx,resy,mir_fill,mir_rec500,mir_nodata)

#NDWI
salida_ndwi = path_indices+"ndwi/ndwi_%s_500m.tif"%fecha
os.system('gdal_calc.py -A %s -B %s --outfile=%s --calc="(A-B)*1.0/(A+B)" --NoDataValue %d --type="Float32" --overwrite'%(red_rec500,mir_rec500,salida_ndwi,red_nodata))

#Subir datos al GeoServer
subirtiff(salida_ndwi, estilo_ndwi, ws_ndwi, user, passw, ipgeo, port)

#Borrar archivos temporales
os.system("rm "+path_proc+"red_temp/*")
os.system("rm "+path_proc+"mir_temp/*")
os.system("rm "+path_proc+"mosaicos/*")
os.system("rm "+path_proc+"recortes/*")
