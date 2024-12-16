"""""
Built-Up Growth Rapid Assessment Geoprocessing Tool's Script by hilmyfar
https://www.linkedin.com/in/hilmyfarras

This script is intended to run with .atbx file as an custom geoprocessing tool in ArcGIS Pro.
I included custom colormap, but you need to set the path to absolute path in your computer. I doesnt know why but it won't work with relative path.

This script uses NDBI, MNDWI, and modified Index-Based Builtup Index (mIBI) that I personally developed after some intensive research (three weeks *cough *cough).
So yeah, the methods are not scientificly proven (yet). But based on my internal testing, it achieves 85-92% of OA on three urban agglomeration area.
Basically, this is for fun experiment and learning purpose~

Anyway, you can use it for anything as long as it's not commercial (non-profit) and credited me (attach link to my github/linkedin page). 
"""""

import arcpy
from arcpy.sa import *
import os
import uuid
import tempfile

# To make this go fast (honestly, idk if its works or not)
arcpy.env.parallelProcessingFactor = "100%"

# List to store paths of temporary rasters for cleanup
temp_raster_paths = []

def rescale_to_255(raster):
    if not arcpy.Exists(raster):
        raise ValueError(f"Raster does not exist or is invalid: {raster}")

    if hasattr(raster, 'isTemporary') and raster.isTemporary:
        temp_raster_path = os.path.join(
            arcpy.env.scratchFolder or tempfile.gettempdir(),
            f"temp_raster_{uuid.uuid4().hex}.tif"
        )
        raster.save(temp_raster_path)
        raster = arcpy.Raster(temp_raster_path)
        temp_raster_paths.append(temp_raster_path)  # Track for cleanup

    arcpy.management.CalculateStatistics(raster, skip_existing=True)

    min_val = float(arcpy.management.GetRasterProperties(raster, "MINIMUM").getOutput(0).replace(',', '.'))
    max_val = float(arcpy.management.GetRasterProperties(raster, "MAXIMUM").getOutput(0).replace(',', '.'))

    if min_val == max_val:
        raise ValueError(f"Raster has constant values ({min_val}); cannot rescale.")

    return ((raster - min_val) / (max_val - min_val)) * 255

def calculate_builtup(builtup_list, output_dir):
    total_builtup_area = []
    # Calculate total built-up area for each year
    for i, builtup in enumerate(builtup_list):
        zonal_table = os.path.join(output_dir, f"zonal_table_{i}.dbf")
        arcpy.sa.ZonalStatisticsAsTable(builtup, "Value", builtup, zonal_table, "DATA", "SUM")
        
        with arcpy.da.SearchCursor(zonal_table, ["SUM"]) as cursor:
            for row in cursor:
                total_builtup_area.append(row[0])
        arcpy.AddMessage(f"+ Total built-up area for year {i+1}: {total_builtup_area[-1]}")

    # Filter out zero values
    valid_builtup_area = [area for area in total_builtup_area if area != 0.0]

    # Calculate built-up growth rate for each valid period
    growth_rates = []
    for i in range(1, len(valid_builtup_area)):
        previous_area = valid_builtup_area[i-1]
        current_area = valid_builtup_area[i]

        if previous_area != 0:
            growth_rate = ((current_area - previous_area) / current_area) * 100
            growth_rates.append(growth_rate)
            arcpy.AddMessage(f"+ Growth rate for period {i}: {growth_rate:.2f}%")
        else:
            arcpy.AddMessage(f"Cannot calculate growth rate for period {i} due to zero division error.")
    
    return valid_builtup_area, growth_rates

def calculate_elasticity(valid_builtup_area, growth_rates):
    continue_choice = arcpy.GetParameter(3) # Input checkbox if user want to calculate builtup growth elasticity
    
    if continue_choice:  # If the checkbox is checked
        arcpy.AddMessage("|------------------ Urban Growth Elasticity To Population ------------------|")

        # Get population data as a list
        population_input = arcpy.GetParameterAsText(4) 
        population_data = list(map(int, map(str.strip, population_input.split(';'))))

        # Validate the number of population data matches rasters input (in this case valid_builtup_area)
        if len(population_data) != len(valid_builtup_area):
            arcpy.AddError("The number of population periods does not match the number of built-up area periods.")
            return

        # Calculate population growth rates
        population_growth_rates = []
        for i in range(1, len(population_data)):
            previous_population = population_data[i - 1]
            current_population = population_data[i]

            if previous_population != 0:
                population_growth_rate = ((current_population - previous_population) / previous_population) * 100
                population_growth_rates.append(population_growth_rate)
            else:
                arcpy.AddWarning(f"Cannot calculate population growth rate for period {i} due to zero division error.")
                population_growth_rates.append(0)

        # Calculate builtup growth elasticity (ratios)
        ratios = []
        for i in range(len(growth_rates)):
            if i < len(population_growth_rates) and population_growth_rates[i] != 0:
                ratio = growth_rates[i] / population_growth_rates[i]
                ratios.append(ratio)

                # Classification and message
                if ratio > 1:
                    arcpy.AddMessage(f"~ Period {i+1}: Inefficient urban expansion (Elasticity > 1)")
                    arcpy.AddMessage(f"  For every addition to the population, the built-up area increases by {ratio:.2f})")
                else:
                    arcpy.AddMessage(f"~ Period {i+1}: Efficient urban densification (Elasticity ≤ 1)")
                    arcpy.AddMessage(f"  For every addition to the population, the built-up area increases by {ratio:.2f}")
            else:
                arcpy.AddWarning(f"Cannot calculate ratio for period {i+1} due to zero population growth.")
                ratios.append(None)

        return population_data, population_growth_rates, ratios

def create_results_table(output_table, builtup_list, valid_builtup_area, growth_rates, population_data, population_growth_rates, ratios):

    if arcpy.Exists(output_table):
        arcpy.management.Delete(output_table) 
    arcpy.management.CreateTable(os.path.dirname(output_table), os.path.basename(output_table))
    arcpy.AddMessage(f"Table created: {output_table}")

    fields = [
        ("Year", "LONG"),
        ("BU_Area", "DOUBLE"),
        ("BU_Growth", "DOUBLE"),
        ("Pop", "LONG"), 
        ("Pop_Growth", "DOUBLE"), 
        ("Elasticity", "DOUBLE")  # Built-up Growth Elasticity
    ]
    for field_name, field_type in fields:
        arcpy.management.AddField(output_table, field_name, field_type)

    with arcpy.da.InsertCursor(output_table, [f[0] for f in fields]) as cursor:
        for i in range(len(builtup_list)):
            year = i
            row = [
                year + 1,  # Year
                valid_builtup_area[i] if i < len(valid_builtup_area) else 0,  # Built-up Area
                growth_rates[i-1] if i - 1 > -1 else 0,  # Built-up Growth Rate
                population_data[i] if i < len(population_data) else 0,  # Population
                population_growth_rates[i-1] if i - 1 > -1 else 0,  # Population Growth Rate
                ratios[i-1] if i - 1 > -1 else 0  # Built-up Growth Elasticity
            ]
            cursor.insertRow(row)
    
    if "Field1" in [f.name for f in arcpy.ListFields(output_table)]:
        arcpy.management.DeleteField(output_table, "Field1")

# Main script
try:
    # User input parameters
    imagery_type = arcpy.GetParameterAsText(0)
    rasters_input = arcpy.GetParameterAsText(1)
    output_dir = arcpy.GetParameterAsText(2)
    raster_files = [file.strip() for file in rasters_input.split(';')]

    arcpy.AddMessage(f"Raster files to process: {raster_files}")

    ibi_list = []
    ndbi_list = []
    mndwi_list = []
    msavi_list = []
    builtup_list = []

    # Process each rasters input
    for i, raster_file in enumerate(raster_files):
        arcpy.AddMessage(f"> Processing file: {raster_file}...")

        try:
            raster = arcpy.Raster(raster_file)
        except RuntimeError as e:
            arcpy.AddError(f"Failed to load raster {raster_file}: {e}")
            continue

        # Calculate indices
        if imagery_type == "Landsat 8":
            msavi = arcpy.sa.MSAVI(raster, 5, 4)
            ndvi = arcpy.sa.NDVI(raster, 5, 4)
            ndbi = arcpy.sa.NDVI(raster, 6, 5)
            mndwi = arcpy.sa.NDVI(raster, 3, 7)
        elif imagery_type == "Sentinel-2":
            msavi = arcpy.sa.MSAVI(raster, 8, 4)
            ndvi = arcpy.sa.NDVI(raster, 8, 4)
            ndbi = arcpy.sa.NDVI(raster, 11, 8)
            mndwi = arcpy.sa.NDVI(raster, 3, 12)

        try:
            msavi_r = rescale_to_255(msavi)
            ndvi_r = rescale_to_255(ndvi)
            ndbi_r = rescale_to_255(ndbi)
            mndwi_r = rescale_to_255(mndwi)

        except ValueError as e:
            arcpy.AddError(f"Error rescaling raster: {e}")

        ndbi_list.append(ndbi_r)
        mndwi_list.append(mndwi_r)
        msavi_list.append(msavi_r)

        ibi = (ndbi_r - (msavi_r + mndwi_r) / 2) / (ndbi_r + (msavi_r + mndwi_r) / 2)
        ibi_list.append(ibi)

        if imagery_type == "Landsat 8":
            builtup = Con(((ibi > -0.05) & (ndbi > mndwi)), 1, 0) 
        elif imagery_type == "Sentinel-2":
            builtup = Con(((ibi > 0.0) & (ndbi > mndwi)), 1, 0) 
        
        builtup_list.append(builtup)

    # Clean the built-up rasters so that builtup area won't transform into non-builtup
    arcpy.AddMessage("> Extracting and cleaning built-up raster...")
    for i in range(len(builtup_list) - 1, 0, -1):
        builtup_list[i - 1] = Con(builtup_list[i] == 0, 0, builtup_list[i - 1])

    # Reference current ArcGIS Pro project
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.listMaps()[0]

    # Save each raster in builtup_list
    arcpy.AddMessage("> Saving built-up rasters...")
    for i, builtup in enumerate(builtup_list):
        output_path = os.path.join(output_dir, f"builtup_{i+1}.tif")
        try:
            builtup.save(output_path)
            arcpy.AddMessage(f"Saved built-up year {i+1} raster to {output_path}")

            # Applying colormap to raster Built-up each year so it has good color
            colormap_file = r"D:\Project\Python Project\Script\BuiltupGrowth\colormap\twoway.clr"  # Change with absolute path to your .clr file (I included mine in colormap folder)
            if arcpy.Exists(colormap_file):
                arcpy.management.AddColormap(output_path, '' ,colormap_file)
                # arcpy.AddMessage(f"Applied colormap to raster: {output_path}")
            else:
                arcpy.AddError(f"Colormap file not found: {colormap_file}")

            layer_name = f"Built-up Year {i+1}"
            layer = arcpy.management.MakeRasterLayer(builtup, layer_name)
            added_layer = active_map.addLayer(layer.getOutput(0))[0]

        except RuntimeError as e:
            arcpy.AddError(f"Failed to save built-up raster {i + 1}: {e}")


    # Overlay built-up series
    arcpy.AddMessage("> Combining each raster to analyze Built-up Growth...")
    builtup_growth = builtup_list[0]
    for builtup in builtup_list[1:]:
        builtup_growth += builtup

    output_path2 = os.path.join(output_dir, f"builtup_growth.tif")
    builtup_growth.save(output_path2)
    arcpy.AddMessage(f"Saved built-up_growth raster to {output_path}")

    # Applying colormap to raster Built-up Growth so it has good color
    colormap_file2 = r"D:\Project\Python Project\Script\BuiltupGrowth\colormap\fourway.clr"  # Change with absolute path to your .clr file (I included mine in colormap folder)
    if arcpy.Exists(colormap_file):
        arcpy.management.AddColormap(output_path2, '' ,colormap_file2)
    else:
        arcpy.AddError(f"Colormap file not found: {colormap_file}")
                
    layer_name2 = f"Built-up Growth"
    layer2 = arcpy.management.MakeRasterLayer(builtup_growth, layer_name2)
    added_layers2 = active_map.addLayer(layer2.getOutput(0)) 
    
    # ----- Statistics -----
    arcpy.AddMessage("|----------------------- Calculating Statistics -----------------------|")

    valid_builtup_area, growth_rates = calculate_builtup(builtup_list, output_dir)
    population_data, population_growth_rates, ratios = calculate_elasticity(valid_builtup_area, growth_rates)
    
    output_table = os.path.join(output_dir, "Builtup_Growth_Statistics.dbf")
    create_results_table(output_table, builtup_list, valid_builtup_area, growth_rates, population_data, population_growth_rates, ratios)

    table = arcpy.management.MakeTableView(output_table, "Builtup_Growth_Statistics")
    active_map.addTable(table.getOutput(0))

except Exception as e:
    arcpy.AddError(f"An error occurred: {e}")

finally:
    # Cleanup temporary rasters
    for temp_path in temp_raster_paths:
        if os.path.exists(temp_path):
            try:
                arcpy.management.Delete(temp_path)
                # *
            except Exception as e:
                arcpy.AddError(f"Failed to delete temporary raster: {temp_path}: {e}")