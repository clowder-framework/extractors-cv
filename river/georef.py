#!/usr/bin/env python
import ogr
import osr
import gdal
import subprocess
import sys
import tempfile
import os, os.path
import shutil

def getExtent(gt,cols,rows):
	''' Return list of corner coordinates from a geotransform

		@type gt:   C{tuple/list}
		@param gt: geotransform
		@type cols:   C{int}
		@param cols: number of columns in the dataset
		@type rows:   C{int}
		@param rows: number of rows in the dataset
		@rtype:    C{[float,...,float]}
		@return:   coordinates of each corner
	'''
	ext=[]
	xarr=[0,cols]
	yarr=[0,rows]

	for px in xarr:
		for py in yarr:
			x=gt[0]+(px*gt[1])+(py*gt[2])
			y=gt[3]+(px*gt[4])+(py*gt[5])
			ext.append([x,y])
		yarr.reverse()
	#ext: ul, ll, lr, ur
	#extStr: ulx uly lrx lry
	extStr = [str(ext[0][0]),str(ext[0][1]),str(ext[2][0]), str(ext[2][1])]
	return extStr

def getProjectionStr(wktProj):
	srs = osr.SpatialReference()
	srs.ImportFromWkt(wktProj)
	if srs.IsLocal() == 1:  # this is a local definition
		return srs.ExportToProj()
	if srs.IsGeographic() == 1:  # this is a geographic srs
		cstype = 'GEOGCS'
	else:  # this is a projected srs
		cstype = 'PROJCS'
		an = srs.GetAuthorityName(cstype)
		ac = srs.GetAuthorityCode(cstype)
	if an is not None and ac is not None:  # return the EPSG code
		return '%s:%s' % (an, ac)
	else:
		srs.AutoIdentifyEPSG()
		try:
			ac = srs.GetAuthorityCode(None)
			return 'EPSG:'+ac
		except:
			return None	

	

def getOriginalGeoRef(inraster):
	ds = gdal.Open(inraster)
	gt = ds.GetGeoTransform()
	cols = ds.RasterXSize
	rows = ds.RasterYSize
	#ext: ul, ll, lr, ur
	ext = getExtent(gt, cols, rows)
	prj = getProjectionStr(ds.GetProjection())
	return [ext, prj]

def convert(extractedJpg, outTif, ext, prj):
	cmd = 'gdal_translate'
	o  = subprocess.check_output([cmd, '-a_ullr',ext[0], ext[1], ext[2], ext[3],'-a_srs', prj, extractedJpg, outTif])
	#o  = subprocess.check_output(['/usr/bin/gdal_translate', '-a_ullr', ext, '-a_srs', prj, extractedJpg, outTif])
	print o
	return

def getGeoRef(original_tif, generated_img, output_tif):
	ext, prj  = getOriginalGeoRef(original_tif)
	print ext, prj
	convert(generated_img, output_tif, ext, prj)
	return

if __name__ == '__main__':
	# georef.py original.tif extracted.jpg output.tif
	# getGeoRef(sys.argv[1], sys.argv[2], sys.argv[3])

	ofilepath="./TerEx_demo_1820s_str/39-44.tif"
	# ofilepath="./TerEx_demo_1820s_str/39-45.tif"
	# ofilepath="./TerEx_demo_1820s_str/39-71.tif"
	# ofilepath="./TerEx_demo_1820s_str/39-72.tif"
	gfilepath="./39-44-t.tif"
	target="./39-44-output.tif"
	getGeoRef(ofilepath, gfilepath, target)

