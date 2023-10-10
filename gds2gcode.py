# GDSPY docs:
#   https://gdspy.readthedocs.io/en/stable/index.html

import sys # read command-line arguments
import os
import gdspy # open gds file
import argparse

script_name = os.path.basename(__file__)

argparser = argparse.ArgumentParser(description='GDSII file to GCODE converter', formatter_class=argparse.ArgumentDefaultsHelpFormatter)

argparser.add_argument("-i", "--input_gds", required=True, help="GDS file")
argparser.add_argument("-o", "--output_dir", required=False, help="Output GCODE directory (one file per layer)")

argparser.add_argument("-c", "--cell", required=False, help="Optional cell id to export. If not set the first top level cell is selected")

argparser.add_argument("-pw", "--plot_width", required=False, help="Max plot width in mm", type=float)
argparser.add_argument("-ph", "--plot_height", required=False, help="Max plot height in mm", type=float)

argparser.add_argument("-zm", "--z_movements_height", required=False, help="Z height for not drawing movements", type=float, default=1.0)
argparser.add_argument("-zd", "--z_drawing_height", required=False, help="Z height for drawing movements", type=float, default=0.0)
argparser.add_argument("-zs", "--z_safe_height", required=False, help="Z height for safe movements at start and end", type=float, default=15.0)
argparser.add_argument("-sz", "--z_speed", required=False, help="Speed of Z axis movements", type=float, default=300.0)
argparser.add_argument("-sxy", "--xy_drawing_speed", required=False, help="Speed of XY axis movements when drawing", type=float, default=1000.0)

argparser.add_argument("-cr", "--crop_rect", required=False, nargs="+", help="Crop rectangle in gds coords (x_min y_min x_max y_max ). Ex: -cr 0 0 140 200 ", type=float)

argparser.epilog = "Example: " + script_name + " -i design.gds -o somedir -c inverter -pw 260 -ph 215 -zm 2.0 -zd -0.1 -zs 15 -sz 100 -sxy 2000"
                 
#argparser.add_argument("-l", "--layer", required=False, help="Layer to export")
#argparser.add_argument("-d", "--datatype", required=False, help="Datatype to export")
args = vars(argparser.parse_args())


input_gds_filepath = args["input_gds"]
input_cell_id = args["cell"]
plot_max_width = args["plot_width"]
plot_max_height = args["plot_height"]
plot_z_movements_height = args["z_movements_height"]
plot_z_drawing_height = args["z_drawing_height"]
plot_z_safe_height = args["z_safe_height"]
plot_z_speed = args["z_speed"]
plot_xy_drawing_speed = args["xy_drawing_speed"]


if(args["output_dir"]==None):    
    #output_dir = os.path.dirname( os.path.dirname(input_gds_filepath) )
    output_dir = "."
else:
    output_dir = args["output_dir"]

    try:
        os.makedirs(output_dir, exist_ok = True)
        #print("Output directory '%s' created successfully" % output_dir)
    except OSError as error:
        print("Output directory '%s' can not be created" % output_dir)
        exit()

crop = False
crop_rect = None
if(args["crop_rect"]!=None):
    crop = True
    crop_rect = args["crop_rect"]
    if( len(crop_rect)!=4):        
        print("Crop rect parameter error. \n Should be 4 values: x_min y_min x_max y_max\nEx: -cr 0 0 140 200")
        print(crop_rect)
        exit()
    
    


print('Reading GDSII file {}...'.format(input_gds_filepath))
gdsii = gdspy.GdsLibrary()
gdsii.read_gds(input_gds_filepath, units='import')

if(input_cell_id==None):
    input_cell_id = gdsii.top_level()[0].name

if(not gdsii.cells.get(input_cell_id)):
    print("Error: %s doesn't existis in gds" % input_cell_id)
    exit()

cell = gdsii.cells[input_cell_id]
# cell.flatten()
cell_bounds = cell.get_bounding_box()
if(not crop):
    cell_size = cell_bounds[1] - cell_bounds[0]
else:
    # x0 - left
    crop_rect[0] = max(cell_bounds[0][0],crop_rect[0])
    # y0 - bottom
    crop_rect[1] = max(cell_bounds[0][1],crop_rect[1])
    # x1 - right
    crop_rect[2] = min(cell_bounds[1][0],crop_rect[2])
    # y1 - top
    crop_rect[3] = min(cell_bounds[1][1],crop_rect[3])

    cell_size = [crop_rect[2] - crop_rect[0], crop_rect[3] - crop_rect[1]]


# Set scaling
if(plot_max_width != None and plot_max_height != None):
    horizontal_ratio = plot_max_width/cell_size[0]
    vertical_ratio = plot_max_height/cell_size[1]
    scaling = min(horizontal_ratio, vertical_ratio)
else:
    if(plot_max_width != None):
        scaling = plot_max_width/cell_size[0]
    elif(plot_max_height != None):
        scaling = plot_max_height/cell_size[1]
    else:
        scaling = 1.0

print("Parsing cell %s" % cell.name)
print(f"GDS Cell size: {cell_size[0]} x {cell_size[1]}" + (" (after crop)" if crop else ""))      
print(f"Scaling: x{scaling}")
print(f"Plot Cell size: {cell_size[0]*scaling} x {cell_size[1]*scaling}")      




# POLYGONS
layers = cell.get_polygons(True)
for id, polygons in layers.items():
    
    gds_layer_id = str(id[0])
    gds_datatype_id = str(id[1])

    out_filename = input_cell_id + "__" + gds_layer_id + "__" + gds_datatype_id + ".gcode"
    outf = open(os.path.join(output_dir, out_filename), "w")


    # GCODE Header
    outf.write("G21\n") # All distances and positions are in mm
    outf.write("G90\n") # All distances and positions are Absolute values from the current origin.

    outf.write(f"G1 F{plot_z_speed}\n")
    outf.write(f"G1 Z{plot_z_safe_height}\n")


    poly_count = 0
    
    for poly in polygons:
        
        #scaled_poly = poly * scaling    
        skip_poly = False
        poly_string = ""
        

        poly_string = poly_string + ("\n")
        poly_string = poly_string + (f"(Poly #{poly_count})\n")
        poly_string = poly_string + (f"G0 X{poly[0][0]*scaling} Y{poly[0][1]*scaling}\n")
        
        poly_string = poly_string + (f"G1 F{plot_z_speed}\n")
        poly_string = poly_string + (f"G1 Z{plot_z_drawing_height}\n")

        poly_string = poly_string + (f"G1 F{plot_xy_drawing_speed}\n")
        for points in poly:
            if(crop):
                if( points[0] < crop_rect[0] or #x_min
                    points[1] < crop_rect[1] or #y_min
                    points[0] > crop_rect[2] or #x_max
                    points[1] > crop_rect[3]    #y_max
                    ):
                    skip_poly = True
                    continue                
            poly_string = poly_string + (f"\tG1 X{points[0]*scaling} Y{points[1]*scaling}\n")
        
        if(skip_poly): 
            continue

        # repeat first point to close de polygon
        poly_string = poly_string + (f"G1 X{poly[0][0]*scaling} Y{poly[0][1]*scaling}\n")
    
        poly_string = poly_string + (f"G1 F{plot_z_speed}\n")
        poly_string = poly_string + (f"G1 Z{plot_z_movements_height}\n")


        outf.write(poly_string)

        poly_count+=1


    outf.write(f"G1 F{plot_z_speed}\n")
    outf.write(f"G1 Z{plot_z_safe_height}\n")

    outf.close()

    # layerid = str(id[0]) + "/" + str(id[1])
    
    # if(not layerid in output_layers):
    #     output_layers[layerid] = create_layer(layerid)

    # for poly in polygons:
    #     output_layers[layerid]["polygons"].append(poly.tolist())
    




# print(gdsii.cells)