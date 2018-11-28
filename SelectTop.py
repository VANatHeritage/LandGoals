# ----------------------------------------------------------------------------------------
# SelectTop.py
# Version:  ArcGIS 10.3.1 / Python 2.7.8
# Creation Date: 2018-11-28
# Last Edit: 2018-11-28
# Creator(s):  Kirsten R. Hazler

# Summary:
# Functions for selecting top areas to meet Governor's land goal.


# Usage Tips:
# 

# Dependencies:

# Syntax:  
# 
# ----------------------------------------------------------------------------------------

# Import modules
import Helper
from Helper import *
from arcpy.sa import *

def SelectTopAgr(in_FarmAgrVal, in_ConsLands, out_Polys, out_Scratch = "in_memory"):
   '''Goal: Select top 500,000 acres of unprotected farm fields, based on Agricultural Model scores, considering only those at least 20 acres in size.
   Parameters:
   - in_FarmAgrVal = raster with agricultural values for farmed lands only
   - in_ConsLands = conserved lands that should be removed from consideration
   - out_Polys = output polygons representing selected top unprotected agricultural fields
   - out_Scratch = geodatabase to store intermediate products
   '''
   
   arcpy.CheckOutExtension("Spatial")

   # Recast string to raster, if necessary
   if isinstance(in_FarmAgrVal, str):
      in_FarmAgrVal = Raster(in_FarmAgrVal)
      
   # Environment settings
   arcpy.env.snapRaster = in_FarmAgrVal
   arcpy.env.cellSize = in_FarmAgrVal
   arcpy.env.extent = "MAXOF"
   cellSize = arcpy.env.cellSize
   
   # Subset Agricultural Model to get high-scored farmland only
   printMsg('Subsetting farmlands with highest scores...')
   farmRast = Con((in_FarmAgrVal > 80), 1)
   farmRast.save(out_Scratch + os.sep + 'farmRast')
   
   # Eliminate areas already protected
   printMsg('Converting protected lands to raster...')
   arcpy.AddField_management (in_ConsLands, "RASTVAL", "SHORT")
   arcpy.CalculateField_management(in_ConsLands, "RASTVAL", "1", "PYTHON_9.3")
   elimRast = out_Scratch + os.sep + 'elimRast'
   arcpy.PolygonToRaster_conversion (in_ConsLands, "RASTVAL", elimRast, "MAXIMUM_COMBINED_AREA", "RASTVAL", cellSize)
   printMsg('Eliminating protected areas from eligible farmland...')
   vulnFarmRast = Con((IsNull(elimRast)==1),farmRast)
      
   # Region group the remaining farmland
   printMsg('Region grouping remaining farmland...')
   regionRast = RegionGroup (vulnFarmRast, "FOUR")
   regionRast.save(out_Scratch + os.sep + 'regionRast')
   
   # Get size of each region
   printMsg('Calculating region sizes...')
   regionSize = ZonalGeometry (regionRast, "VALUE", "AREA")
   regionSize.save(out_Scratch + os.sep + 'regionSize')
   
   # Eliminate regions < 20 acres. Area is assumed in square meters. 
   # 20 acres = 80937.1 square meters; 1 square meter = 0.000247105 acres
   printMsg('Eliminating regions under size threshold...')
   regionSubset = Con((regionSize >= 80937.1), regionRast)
   regionSubset.save(out_Scratch + os.sep + 'regionSubset')
   
   # Convert remaining regions to polygons
   printMsg('Converting remaining regions to polygons...')
   regionPolys = out_Scratch + os.sep + 'regionPolys'
   arcpy.RasterToPolygon_conversion (regionSubset, regionPolys, "NO_SIMPLIFY")
   
   # Get average Agricultural Model Score for polygons
   printMsg('Calculating zonal means for agricultural value...')
   zonalTab = out_Scratch + os.sep + 'zonalTab'
   ZonalStatisticsAsTable (regionSubset, "VALUE", in_FarmAgrVal, zonalTab, "DATA", "MEAN")
   arcpy.JoinField_management (regionPolys, "gridcode", zonalTab, "Value", "MEAN")

   # Sort polygons by score (descending)
   printMsg('Sorting polygons by agricultural score...')
   sortedPolys = out_Scratch + os.sep + 'sortedPolys'
   arcpy.Sort_management (regionPolys, sortedPolys, [["MEAN", "DESCENDING"]])
   
   # Add fields for acreage, cumulative acreage, and selection
   printMsg('Adding and calculating fields...')
   arcpy.AddField_management (sortedPolys, "ACRES", "DOUBLE")
   arcpy.AddField_management (sortedPolys, "CUM_ACRES", "DOUBLE")
   arcpy.AddField_management (sortedPolys, "SELECTION", "SHORT")
   
   # Calculate Fields
   printMsg('Calculating ACRES field...')
   expression = "!Shape_Area!*0.000247105"
   arcpy.CalculateField_management(sortedPolys, "ACRES", expression, "PYTHON_9.3")
   
   printMsg('Calculating CUM_ACRES field...')
   expression = "accumulate(!ACRES!)"
   code_block = '''cumVal = 0 \ndef accumulate(Val):
      global cumVal
      cumVal += Val
      return cumVal'''
   arcpy.CalculateField_management(sortedPolys, "CUM_ACRES", expression, "PYTHON_9.3", code_block)
   
   printMsg('Calculating SELECTION field...')
   expression = "select(!CUM_ACRES!)"
   code_block = '''def select(Val):
      if Val <= 500000:
         s = 1
      else:
         s = 0
      return s'''
   arcpy.CalculateField_management(sortedPolys, "SELECTION", expression, "PYTHON_9.3", code_block)
   
   # Save out the selected polygons
   printMsg('Saving out top agricultural polygons...')
   qry = "SELECTION = 1"
   arcpy.Select_analysis (sortedPolys, out_Polys, qry)

   arcpy.CheckInExtension("Spatial")
   
   printMsg('Done.')
   return out_Polys
   
# Use the main function below to run functions directly from Python IDE or command line with hard-coded variables
def main():
   # Set up parameters
   in_FarmAgrVal = r'H:\Backups\DCR_Work_DellD\ConsVision_AgrMod\AgrMod2018_Revision\TIF\AgrValue_Farmed.tif'
   in_ConsLands = r'I:\SWAPSPACE\K_Hazler\From_David\lands_all_single.shp'
   out_Polys = r'C:\Users\xch43889\Documents\ArcGIS\Default.gdb\TopAgr'
   out_Scratch = r'C:\Users\xch43889\Documents\ArcGIS\scratch.gdb'
   
   # Set up function(s) to run
   SelectTopAgr(in_FarmAgrVal, in_ConsLands, out_Polys, out_Scratch)
   
if __name__ == '__main__':
   main()