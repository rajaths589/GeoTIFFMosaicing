from osgeo import gdal
import time
import sys

def findOverlapArea(image_easy1,image_easy2):
	"""returns overlao, if there is, else returns None"""
	overlap = None
	overlap_ulx = max( image_easy1.ulx, image_easy2.ulx )
	overlap_uly = min( image_easy1.uly, image_easy2.uly )	
	overlap_lrx = min( image_easy1.lrx, image_easy2.lrx )
	overlap_lry = max( image_easy1.lry, image_easy2.lry )
	if (overlap_ulx>overlap_lrx):
		print "The Input Images do not overlap."
		return None
	if (overlap_uly<overlap_lry):
		print "The Input Images do not overlap."
		return None
	return [overlap_ulx,overlap_uly,overlap_lrx,overlap_lry]

def isNorthUp(image):
	"""checks if the image is north facing,
		checks if the affine transformation matrix is diagonal.
	"""
	gTransform = image.GetGeoTransform()
	if gTransform[2]==0 and gTransform[4]==0:
		return True
	else:
		return False

class ImageEasyAccess:
	
	def __init__(self, image):	
		self.image = image
		self.ulx = (image.GetGeoTransform())[0]
		self.uly = (image.GetGeoTransform())[3]
		self.xsize = (image.GetGeoTransform())[1]
		self.ysize = (image.GetGeoTransform())[5]
		self.extentX = image.RasterXSize
		self.extentY = image.RasterYSize
		self.bandCount = image.RasterCount
		self.bandType = image.GetRasterBand(1).DataType
		self.projection = image.GetProjection()
		self.lrx = (self.getLRCoord())[0]
		self.lry = (self.getLRCoord())[1]
	
	def printdetails(self):
		print "UL:",(self.ulx,self.uly)
		print "LR:",(self.lrx,self.lry)
		print "extent:",(self.extentX,self.extentY)
		print "Pixel:",(self.xsize,self.ysize)

	def getLatLong(self,x,y):
		if (x>=0 and x<=self.extentX) and (y>=0 and y<=self.extentY):
			lat = self.ulx + x*self.xsize
			lng = self.uly + y*self.ysize
			return (lat,lng)
		else:
			return None

	def getLRCoord(self):
		lrx = self.ulx + self.extentX*self.xsize
		lry = self.uly + self.extentY*self.ysize
		return (lrx,lry)

	def getXOffYOff(self,lat,lng):
		XOff = int((lat-self.ulx)/self.xsize + 0.5) # XOff is the offset from origin
		YOff = int((lng-self.uly)/self.ysize + 0.5) 
		return (XOff,YOff)

	def getXYoffFromAB(self,a,b,x,y):
		ab = self.getXOffYOff(a,b)
		xy = self.getXOffYOff(x,y)
		return (xy[0]-ab[0],xy[1]-ab[1])

	def destroyImage(self):
		self.image = None	

def main( argv=None ):	
	start = time.time()
	#Register GDAL drivers	
	gdal.AllRegister()
	#print "GDAL Drivers Registered for opening Images."
	#print ""
	
	#Obtain name of the file from command line arguments
	argv = sys.argv
	name1 = argv[1]
	name2 = argv[2]	
	if name1 is None or name2 is None:
		print "Please provide Input Images"
		return 0	
	#print "Name1:\t",name1
	#print "Name2:\t",name2
	#print ""		
	image1 = gdal.Open( name1 )
	image2 = gdal.Open( name2 )
	if image1 is None or image2 is None:
		print "Unable to open Input Images"
		return 0

	if not (isNorthUp(image1) and isNorthUp(image2)):
		print "Images are not registered. Register images before mosaicing."
		return 0

	image_easy1 = ImageEasyAccess(image1)
	image_easy2 = ImageEasyAccess(image2)
	#print "ImageEasyAccess objects are created.\n"
	name3 = argv[3]
	if name3 is None:
		print "Output file name not given. Using Default name."
		name3 = "output.tif"
	#print "Name3:",name3
	#print ""
	
	#Create the output file.
	create_options = []
	create_options.append("COMPRESS=DEFLATE")
	create_options.append("PREDICTOR=2")
	create_options.append("ZLEVEL=9")
	Driver = gdal.GetDriverByName('GTiff')
	if Driver==None:
		print "Driver is None."	
	output_ulx = min(image_easy1.ulx,image_easy2.ulx)
	output_uly = max(image_easy1.uly,image_easy2.uly)
	#print "OutputUL:",output_ulx,",",output_uly
	lr1 = image_easy1.getLRCoord()
	lr2 = image_easy2.getLRCoord()
	output_lrx = max(lr1[0],lr2[0])
	output_lry = min(lr1[1],lr2[1])
	#print "OutputLR:",output_lrx,",",output_lry
	#if not ((image_easy1.xsize==image_easy2.xsize) and (image_easy1.ysize==image_easy2.ysize)):
	#	print "Incompatible Images to merge. Images have different pixel sizes."
	#	return 0
	output_pwidth = image_easy1.xsize
	output_pheight = image_easy1.ysize	
	if not image_easy1.bandType == image_easy2.bandType:
		print "Incompatible Images to merge. Images have different band types."
		return 0	
	output_bandtype = image_easy1.bandType
	if not image_easy1.projection == image_easy2.projection:
		print "Incompatible Images to merge. Images have different projections."
		return 0	
	output_projection = image_easy1.projection
	if not image_easy1.bandCount==image_easy2.bandCount:
		print "Incompatible Images to merge. Images have unequal band counts."
		return 0
	output_bandCount = image_easy1.bandCount
	gdal.PushErrorHandler( 'CPLQuietErrorHandler' )
	output = gdal.Open(name3,gdal.GA_Update)
	gdal.PopErrorHandler()
	if output==None:
		output_geotransform = [output_ulx,output_pwidth,0,output_uly,0,output_pheight]
		output_xsize = int((output_lrx-output_ulx)/output_pwidth + 0.5)
		output_ysize = int((output_lry-output_uly)/output_pheight + 0.5)
	else:
		print "The output file already exists. Please try with a different file name"
		return 0
	output = Driver.Create( name3, output_xsize, output_ysize, output_bandCount, output_bandtype, create_options ) #create_options not yet defined.
	if output is None:
		print "New image creation failed."
		return 0
	output.SetGeoTransform( output_geotransform )
	output.SetProjection( output_projection )
	outputImage = ImageEasyAccess(output)
	#print "Image1:"
	#image_easy1.printdetails()
	#print "Image2:"
	#image_easy2.printdetails()
	#print "Output:"
	#outputImage.printdetails()	
	#Merge the images
	#find overlap area
	overlap = findOverlapArea(image_easy1,image_easy2)	
	if overlap is None:
		return 0		
	
	#Find the image on top.
	if image_easy1.uly>=image_easy2.uly:
		above = image_easy1
		below = image_easy2
	else:
		above = image_easy2
		below = image_easy1
	#Using WriteRaster incorrectly.
	if above.ulx < below.ulx:
		copyarea = [above.ulx,above.uly,overlap[0],above.lry]
		copy_area( copyarea, above, outputImage, output_bandtype )
		#coordOff = above.getXOffYOff(overlap[2],above.lry)		
		#sourceBand = above.image.GetRasterBand(1)
		#targetBand = outputImage.image.GetRasterBand(1)		
		#data = sourceBand.ReadRaster(0,0,coordOff[0],coordOff[1],coordOff[0],coordOff[1],output_bandtype)
		#targetBand.WriteRaster(0,0,coordOff[0],coordOff[1],data,coordOff[0],coordOff[1],output_bandtype)
		copyarea = [overlap[0],above.uly,above.lrx,overlap[1]]
		copy_area( copyarea, above, outputImage, output_bandtype )
		#coordOff = above.getXOffYOff(overlap[0],above.uly)
		#coordSize = above.getXYoffFromAB(overlap[0],above.uly,above.lrx,above.uly)
		#data = sourceBand.ReadRaster(coordOff[0],coordOff[1],coordSize[0],coordSize[1],coordSize[0],coordSize[1],output_bandtype)
		#targetBand.WriteRaster(coordOff[0],coordOff[1],coordSize[0],coordSize[1],data,coordSize[0],coordSize[1],output_bandtype)
		#sourceBand = below.image.GetRasterBand(1)
		copyarea = [overlap[0],above.lry,above.lrx,below.lry]
		copy_area( copyarea, below, outputImage, output_bandtype )
		#coordOff = below.getXOffYOff(overlap[0],above.lry)
		#coordSize = below.getXYoffFromAB(overlap[0],above.lry,overlap[2],below.lry)
		#targetCoordOff = outputImage.getXoffYoff(below.ulx,overlap[3])	
		#data = sourceBand.ReadRaster(coordOff[0],coordOff[1],coordSize[0],coordSize[1],coordSize[0],coordSize[1],output_bandtype)
		#targetBand.WriteRaster(targetCoordOff[0],targetCoordOff[1],coordSize[0],coordSize[1],data,coordSize[0],coordSize[1],output_bandtype)
		copyarea = [overlap[2],below.uly,below.lrx,below.lry]
		copy_area( copyarea, below, outputImage, output_bandtype )
		#coordOff = below.getXOffYOff(overlap[2],below.uly)
		#coordSize = below.getXYoffFromAB(overlap[2],below.uly,below.lrx,below.lry)
		#targetCoordOff = outputImage.getXOffYOfpgrepf(overlap[2],below.uly)	
		#data = sourceBand.ReadRaster(coordOff[0],coordOff[1],coordSize[0],coordSize[1],coordSize[0],coordSize[1],output_bandtype)
		#targetBand.WriteRaster(targetCoordOff[0],targetCoordOff[1],coordSize[0],coordSize[1],data,coordSize[0],coordSize[1],output_bandtype)
		copyarea = overlap
		sourceBand1 = above.image.GetRasterBand(1)
		sourceBand2 = below.image.GetRasterBand(1)
		coordOff1 = above.getXOffYOff(overlap[0],overlap[1])
		coordOff2 = below.getXOffYOff(overlap[0],overlap[1])
		targetCoordSize = outputImage.getXYoffFromAB(overlap[0],overlap[1],overlap[2],overlap[3])
		coordSize1 = above.getXYoffFromAB(overlap[0],overlap[1],overlap[2],overlap[3])
		coordSize2 = below.getXYoffFromAB(overlap[0],overlap[1],overlap[2],overlap[3])
		import numpy as np
		data1 = sourceBand1.ReadAsArray(coordOff1[0],coordOff1[1],coordSize1[0],coordSize1[1],targetCoordSize[0],targetCoordSize[1]).astype(np.float)
		data2 = sourceBand2.ReadAsArray(coordOff2[0],coordOff2[1],coordSize2[0],coordSize2[1],targetCoordSize[0],targetCoordSize[1]).astype(np.float)		
		#data = np.ones((targetCoordSize[1],targetCoordSize[0]))
		#print len(data),len(data[0]), len(data1), len(data1[0]), len(data2), len(data2[0])
		#print type(data1)
		#print type(data2)
		#print type(data)
		#print data1.shape
		#print data2.shape
		#print data.shape

		#for x in range(targetCoordSize[1]):
		#	for y in range(targetCoordSize[0]):
		#		#data[x][y] = np.max((data1[x][y],data2[x][y]))
		#		if(data1[x][y]==0):
		zeroCheck = np.equal(0,data2)
		data = np.choose(zeroCheck,(data2,data1))
		data1 = None
		data2 = None		
		dataNpy = np.array(data)
		targetCoordOff = outputImage.getXOffYOff(overlap[0],overlap[1])	
		targetBand = outputImage.image.GetRasterBand(1)	
		targetBand.WriteArray(data,targetCoordOff[0],targetCoordOff[1])		
		data = None
		dataNpy = None
		targetBand = None
	
	image_easy1.destroyImage()
	image_easy2.destroyImage()
	above.destroyImage()
	below.destroyImage()
	outputImage.destroyImage()
	end = time.time()
	print 'The script took ' + str(end - start) + ' seconds.'

def copy_area( area, sourceImage, targetImage, dtype ):
	sourceBand = sourceImage.image.GetRasterBand( 1 )
	targetBand = targetImage.image.GetRasterBand( 1 )
	sourceCoordOff = sourceImage.getXOffYOff( area[0], area[1] )
	sourceCoordSize = sourceImage.getXYoffFromAB( area[0], area[1], area[2], area[3] )
	for x in sourceCoordSize:
		if x <= 0:
			return

	targetCoordOff = targetImage.getXOffYOff( area[0], area[1] )
	targetCoordSize = targetImage.getXYoffFromAB( area[0],area[1], area[2], area[3] )
	#print "Area:",area
	#print "sourceCoordOff:",sourceCoordOff
	#print "sourceCoordSize:",sourceCoordSize
	#print "targetCoordOff:",targetCoordOff
	#print "targetCoordSize:",targetCoordSize
	#print 
	data = sourceBand.ReadRaster( sourceCoordOff[0], sourceCoordOff[1], sourceCoordSize[0], sourceCoordSize[1], targetCoordSize[0], targetCoordSize[1], dtype )
	targetBand.WriteRaster( targetCoordOff[0], targetCoordOff[1], targetCoordSize[0], targetCoordSize[1], data, targetCoordSize[0], targetCoordSize[1], dtype )	
	
if __name__ == '__main__':	
	debug = True
	sys.exit(main())