#############################################
#################### BAM ####################
######## Batch Apply Model textures #########
#############################################
#       advanced brute force edition
#                for Blender
#
# * Takes fbx, glb, etc. and outputs gltf
# * Works with normal maps, metallic, etc.
# * gradually descends from sane to insane
#   when associating model to image files
# 
# Copyright:    2023 @Ballerburg9005 
# License:      GPL-3 or later
# https://github.com/ballerburg9005/BAM
#############################################
#################### BAM ####################
#############################################

### Instructions
# 1. open an empty file in Blender
# 2. paste this script in "Scripting"
# 3. edit the input and output dir
# 4. execute script
# 5. profit
# (Debug output in system console, not Blender console)

import bpy
import os
import glob
import re
import logging
import shutil
from bpy import context
from pathlib import Path

######## Edit these ##########

# Warning: input_dir must contain subfolders, and each subfolder must contain the models and the textures without any more subfolders
# Example: mydir/trees: tree1.glb tree1.png ... - mydir/bushes: bush1.fbx bush1.jpg bush2.fbx bush2.jpg ...

input_dir = "/mnt/2/retro_nature_pack"
output_dir = "/home/l0rd/godotverse/models/retro_nature_pack"

##############################


def do_import(input_model, input_textures, input_path, output_file):

    extension = os.path.splitext(input_model)[1].lower()
    if extension in ['.glb', '.gltf']:    
        bpy.ops.import_scene.gltf(filepath=input_model)
    elif extension in ['.fbx']:
        bpy.ops.import_scene.fbx(filepath=input_model)
    elif extension in ['.obj']:
        bpy.ops.import_scene.obj(filepath=input_model)
    

    for object in set(o for o in context.scene.objects if o.type == 'MESH'):
        material = bpy.data.materials.new(name="master_material")
        material.use_nodes = True
        
        nodes = material.node_tree.nodes
        nodes.clear()
  
        node_principled = nodes.new(type='ShaderNodeBsdfPrincipled') # Add the Principled Shader node
        node_principled.location = 000,0
        node_output = nodes.new(type='ShaderNodeOutputMaterial')    # Add the Output node
        node_output.location = 300,0
        
        links = material.node_tree.links # Link all nodes
        links.new(node_principled.outputs["BSDF"], node_output.inputs["Surface"])
        
        shift = 0
        for i in ["Base Color", "Metallic", "Transmission", "Emission", "Normal", "Roughness"]:
            if i == "Base Color" or i in input_textures.keys():
                shift += 1
                node_tex = nodes.new('ShaderNodeTexImage') 
                node_tex.location = -shift*300,0
                
                if i != "Normal":
                    links.new(node_tex.outputs["Color"], node_principled.inputs[i])
                else:
                    normal_map = material.node_tree.nodes.new('ShaderNodeNormalMap') 
                    links.new(node_tex.outputs["Color"], normal_map.inputs['Color'])
                    links.new(normal_map.outputs["Normal"], node_principled.inputs[i])
            
                node_tex.image = bpy.data.images.load(bpy.path.relpath(os.path.join(input_path, input_textures[i])), check_existing=True)

        # Place copy of master material in first material slot
        if object.data.materials:
            object.data.materials[0] = material
        else:
            object.data.materials.append(material)
            
    print("exporting model "+str(input_textures["Base Color"]))
    bpy.ops.export_scene.gltf(
        check_existing=False, export_format='GLTF_SEPARATE',
        filepath=output_file)


def clear_blender_data():
    for obj in bpy.context.scene.objects:
        if obj.type in ['MESH', 'CAMERA', 'LIGHT', 'EMPTY']:
            obj.select_set(True)
        else:
            print(obj.type)
            obj.select_set(False)    
    bpy.ops.object.delete()
    for material in bpy.data.materials:
        # material.user_clear()
        bpy.data.materials.remove(material)
    for mesh in bpy.data.meshes:
        mesh.user_clear()
        bpy.data.meshes.remove(mesh)






failures_con = []
failures_tex = []
successes = []

realfile = bpy.data.filepath

synonyms = {
            "Normal": ['normal', 'normals'], 
            "Roughness": ['roughness'], 
            "Metallic": ['metallic', 'metal'], 
            "Emission": ['emission', 'emissive'], 
            "Transmission": ['transmission', 'transmit']
            }

supported_extensions = ['.gltf', '.glb', '.fbx', '.obj']
supported_image_formats = ['png', 'tga', 'jpg', 'jpeg']

for folder in os.listdir(input_dir):
    
    mydir = os.path.join(input_dir, folder)

    for file in os.listdir(mydir):
        if os.path.splitext(file)[1].lower() not in supported_extensions:
            continue
        
        name = os.path.splitext(file)[0]
        
        # try to find all matching textures
        textures = []
        for z in range(0,10): # each number more desperate attempts
            # tree_bush_big_corner -> tree_bush_big ... tree_bush ... 
            if z > 2:
                name = "_".join(name.split("_")[:z-4])
            # long_long_tree -> long_tree .. tree
            if z > 6:
                name = "_".join(name.split("_")[z-7:])
            if name == '':
                break
            # tree01_ -> tree1
            zeropad = [name]
            sploded = list(re.findall(r'([^0-9]*)([0-9]+)*(_.*|$)', name)[0])
            if sploded[1].isdigit():
                sploded[1] = str(int(sploded[1])) if z < 1 else ''
            if "".join(sploded) != name:
                zeropad += ["".join(sploded)]
            for f in os.listdir(mydir):
                # tree01 -> tree01_summer, tree01_winter
                for n in zeropad:
                    desperation_move = '(_[^_]*)*' if z < 2 else '(_.*)*'
                    found_file = next(iter(next(iter(re.findall(r'('+n+desperation_move+'\.('+"|".join(supported_image_formats)+'))$',f)), [None])), None)
                    if None != found_file:
                        if None == next(iter(re.findall(r'_([^_]*)('+str("|".join([x for n in synonyms.values() for x in n]))+').*\.[A-z0-9]+$',found_file, re.IGNORECASE)), None):
                            textures += [{"Base Color": found_file}]
            if len(textures) > 0:
                break

        # check if there is just one image or model file, so we can take whatever there is
        model_files = []
        basecolor_files = []
        for f in os.listdir(mydir):
            if os.path.splitext(f)[-1].lower() in supported_extensions:
                model_files += [f]
            if os.path.splitext(f)[-1].lower()[1:] in supported_image_formats:
                if None == next(iter(re.findall(r'_([^_]*)('+str("|".join([x for n in synonyms.values() for x in n]))+').*\.[A-z0-9]+$',f, re.IGNORECASE)), None):
                    basecolor_files += [f]

        if len(basecolor_files) == 1 or (len(model_files) == 1 and len(basecolor_files) > 0):
            textures += [{"Base Color": basecolor_files[0]}]
            
          
        # find normal textures and such
        for idx, texture_pack in enumerate(textures):
            for f in os.listdir(mydir):
                for key in synonyms:
                    for synonym in synonyms[key]:
                        # matches anything like _normal-asdf_null.png
                        fnm  = [os.path.splitext(texture_pack["Base Color"])[0]]
                        fn   = fnm[0].split("_")[:-1]
                        if len(fn) > 0:
                            fnm += fn
                        for x in fnm:
                            found_texture = next(iter(re.findall(r''+x+"_[^_]*"+synonym+".*\.[A-z0-9]+$",f, re.IGNORECASE)), None)
                            if None != found_texture:
                                textures[idx][key] = found_texture
                                break
                        if None != found_texture:
                            break
        
        try: Path(os.path.join(output_dir, folder)).mkdir(parents=True) 
        except: pass

        try:
            for texture_pack in textures: 
                
                print("Converting "+file+" ("+str(texture_pack)+")")
                # save .blend file in same directory to get correct relative paths
                bpy.context.preferences.filepaths.save_version = 0
                bpy.ops.wm.save_as_mainfile(filepath=os.path.join(mydir, texture_pack["Base Color"]+".blend"))
            
                clear_blender_data()
                
                for key in texture_pack:
                    shutil.copy(os.path.join(mydir, texture_pack[key]), os.path.join(output_dir, folder))
                do_import(
                    input_model     =     os.path.join(mydir, file),
                    input_textures  =     texture_pack,
                    input_path      =     mydir,
                    output_file     =     os.path.join(os.path.join(output_dir, folder), texture_pack["Base Color"]),
                )
                
                # save again for amusement
                bpy.ops.wm.save_as_mainfile(filepath=os.path.join(mydir, texture_pack["Base Color"]+".blend"))
                
            if len(textures) == 0:
                failures_tex += [os.path.join(mydir, file)]
            else:
                successes += [os.path.join(mydir, texture_pack["Base Color"]+" {"+file+")")]
        except Exception as e:
            print("ERROR: ",e)
            failures_con += [os.path.join(mydir, texture_pack["Base Color"]+" {"+file+")")]
            
    bpy.ops.wm.save_as_mainfile(filepath=realfile)

    print("\n\nSuccessfully converted: \n"+"\n".join(successes))
if len(failures_con)+len(failures_tex) > 0:
    print("\nFailed to convert: \n"+"\n".join(failures_con))
    print("\nSkipped due to missing texture file: \n"+"\n".join(failures_tex))
