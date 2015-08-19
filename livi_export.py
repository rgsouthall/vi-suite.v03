# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy, os, math, subprocess, datetime, bmesh, shutil
from math import sin, cos, tan, pi
from subprocess import PIPE, Popen, STDOUT
from .vi_func import retsky, retobj, retmesh, clearscene, solarPosition, mtx2vals, retobjs, selobj, selmesh, vertarea, radpoints, clearanim, radmesh

def radgexport(export_op, node, **kwargs):
    scene = bpy.context.scene  
    scene['liparams']['cp'] = node.cpoint
    export = 'geoexport' if export_op.nodeid.split('@')[0] == 'LiVi Geometry' else 'genexport'
    if bpy.context.active_object and not bpy.context.active_object.layers[scene.active_layer]:
        export_op.report({'INFO'}, "Active geometry is not on the active layer. You may need to lock layers.")
    radfiles = []
    geogennode = node.inputs['Generative in'].links[0].from_node if node.inputs['Generative in'].links else 0
    geooblist, caloblist, lightlist = retobjs('livig'), retobjs('livic'), retobjs('livil') 
    
    if not kwargs:
        mableobs = set(geooblist + caloblist)
        scene['liparams']['livig'], scene['liparams']['livic'], scene['liparams']['livil'] = [o.name for o in geooblist], [o.name for o in caloblist], [o.name for o in lightlist]
        if geogennode:            
            for o in mableobs: 
                seldict = {'ALL': True, 'Selected': (False, True)[o.select], 'Not Selected': (True, False)[o.select]}
                o.manip = seldict[geogennode.oselmenu]
            for o in mableobs:
                if geogennode.geomenu == 'Mesh':
                    selobj(scene, o)
                    if o.vertex_groups.get('genfaces'):
                        selmesh('rd')
                    else:                        
                        o.vertex_groups.new('genfaces')
                        o.vertex_groups.active = o.vertex_groups['genfaces']
                        mseldict = {'Not Selected': 'INVERT', 'All': 'SELECT', 'Selected': 'PASS'}
                        selmesh(mseldict[geogennode.mselmenu])
                    o['vgi'] = o.vertex_groups['genfaces'].index
            scene['liparams']['livim'] = [o.name for o in mableobs if o.manip]
            clearanim(scene, [bpy.data.objects[on] for on in scene['liparams']['livim']])
    
    if export == 'geoexport':
        clearscene(scene, export_op)
        scene['liparams']['fs'] = scene.frame_start if node.animmenu != 'Static' else 0
    else:
        (scene['liparams']['fs'], scene['liparams']['gfe'], node['frames']['Material'], node['frames']['Geometry'], node['frames']['Lights']) = [kwargs['genframe']] * 5 if kwargs.get('genframe') else (0, 0, 0, 0, 0)
    scene['liparams']['cfe'] = 0
       
    
    for frame in range(scene['liparams']['fs'], scene['liparams']['gfe'] + 1): 
        if export == 'geoexport':
            scene.frame_set(frame)
        
        if frame in range(node['frames']['Material'] + 1):
            mradfile, matnames = "# Materials \n\n", []
            for o in [bpy.data.objects[on] for on in scene['liparams']['livig']]: 
                mradfile +=  ''.join([m.radmat(scene) for m in o.data.materials if m.name not in matnames])
                for mat in [m for m in o.data.materials if m.name not in matnames]:
                    matnames.append(mat.name)

            bpy.ops.object.select_all(action='DESELECT')            
            tempmatfilename = scene['viparams']['filebase']+".tempmat"
            with open(tempmatfilename, "w") as tempmatfile:
                tempmatfile.write(mradfile)
                
        # Geometry export routine
        
        if frame in range(scene['liparams']['fs'], max(node['frames']['Geometry'], node['frames']['Material']) + 1):
            rti, rtpoints = 1, ''
            gframe = scene.frame_current if node['frames']['Geometry'] > 0 else 0
            mframe = scene.frame_current if node['frames']['Material'] > 0 else 0
            gradfile = "# Geometry \n\n"
            radmesh(scene, set(geooblist + caloblist), export_op) 
            for o in set(geooblist + caloblist):                
                bm = bmesh.new()
                bm.from_mesh(o.data)
                bm.transform(o.matrix_world)
                bm.normal_update()
                if o.name in scene['liparams']['livig']:
                    if not kwargs.get('mo') or (kwargs.get('mo') and o in kwargs['mo']):
                        if not o.get('merr'):                                               
                            if node.animmenu in ('Geometry', 'Material'):# or export_op.nodeid.split('@')[0] == 'LiVi Simulation':
                                bpy.ops.export_scene.obj(filepath=retobj(o.name, gframe, node, scene), check_existing=True, filter_glob="*.obj;*.mtl", use_selection=True, use_animation=False, use_mesh_modifiers=True, use_edges=False, use_normals=o.data.polygons[0].use_smooth, use_uvs=True, use_materials=True, use_triangles=True, use_nurbs=True, use_vertex_groups=False, use_blen_objects=True, group_by_object=False, group_by_material=False, keep_vertex_order=True, global_scale=1.0, axis_forward='Y', axis_up='Z', path_mode='AUTO')
                                objcmd = "obj2mesh -w -a {} {} {}".format(tempmatfilename, retobj(o.name, gframe, node, scene), retmesh(o.name, max(gframe, mframe), node, scene)) 
                            elif export_op.nodeid.split('@')[0] == 'LiVi Simulation':
                                bpy.ops.export_scene.obj(filepath=retobj(o.name, scene.frame_start, node, scene), check_existing=True, filter_glob="*.obj;*.mtl", use_selection=True, use_animation=False, use_mesh_modifiers=True, use_edges=False, use_normals=o.data.polygons[0].use_smooth, use_uvs=True, use_materials=True, use_triangles=True, use_nurbs=True, use_vertex_groups=False, use_blen_objects=True, group_by_object=False, group_by_material=False, keep_vertex_order=True, global_scale=1.0, axis_forward='Y', axis_up='Z', path_mode='AUTO')
                                objcmd = "obj2mesh -w -a {} {} {}".format(tempmatfilename, retobj(o.name, scene.frame_start, node, scene), retmesh(o.name, scene.frame_start, node, scene))
                            else:
                                if frame == scene['liparams']['fs']:                                           
                                    bpy.ops.export_scene.obj(filepath=retobj(o.name, scene.frame_current, node, scene), check_existing=True, filter_glob="*.obj;*.mtl", use_selection=True, use_animation=False, use_mesh_modifiers=True, use_edges=False, use_normals=o.data.polygons[0].use_smooth, use_uvs=True, use_materials=True, use_triangles=True, use_nurbs=True, use_vertex_groups=False, use_blen_objects=True, group_by_object=False, group_by_material=False, keep_vertex_order=True, global_scale=1.0, axis_forward='Y', axis_up='Z', path_mode='AUTO')
                                    objcmd = "obj2mesh -w -a {} {} {}".format(tempmatfilename, retobj(o.name, scene.frame_current, node, scene), retmesh(o.name, scene.frame_current, node, scene))
                                else:
                                    objcmd = ''
                            
                            objrun = Popen(objcmd.split(), stdout = PIPE, stderr=STDOUT)                        
                            for line in objrun.stdout:
                                if 'non-triangle' in line.decode():
                                    export_op.report({'INFO'}, o.name+" has an incompatible mesh. Doing a simplified export")
                                    o['merr'] = 1
                                    break
    
                            o.select = False                            
                            gradfile += "void mesh id \n1 "+retmesh(o.name, max(gframe, mframe), node, scene)+"\n0\n0\n\n"
        
                        elif o.get('merr'):
                            genframe = gframe + 1 if not kwargs else kwargs['genframe']  
                            if o.data.shape_keys and o.data.shape_keys.key_blocks[0] and o.data.shape_keys.key_blocks[genframe]:
                                skv0, skv1 = o.data.shape_keys.key_blocks[0].value, o.data.shape_keys.key_blocks[genframe].value
                                sk0, sk1 = bm.verts.layers.shape.keys()[0], bm.verts.layers.shape.keys()[genframe]
                                skl0, skl1 = bm.verts.layers.shape[sk0], bm.verts.layers.shape[sk1]
                                gradfile += radpoints(o, [face for face in bm.faces if o.data.materials and face.material_index < len(o.data.materials)], (skv0, skv1, skl0, skl1))            
                            else:
                                gradfile += radpoints(o, [face for face in bm.faces if o.data.materials and face.material_index < len(o.data.materials)], 0)

                            del o['merr']
                            
                # rtrace export routine
                
                if o.name in scene['liparams']['livic']:
                    o['cpoint'] = int(node.cpoint)
                    o.rtpoints(bm, node)
                            
    # Lights export routine
        if frame in range(scene['liparams']['fs'], node['frames']['Lights'] + 1):
            lradfile = "# Lights \n\n" 
            for o in lightlist:
                if frame in range(node['frames']['Lights'] + 1):
                    iesname = os.path.splitext(os.path.basename(o.ies_name))[0]
                    if os.path.isfile(o.ies_name):
                        iescmd = "ies2rad -t default -m {0} -c {1[0]:.3f} {1[1]:.3f} {1[2]:.3f} -p {2} -d{3} -o {4}-{5} {6}".format(o.ies_strength, o.ies_colour, scene['viparams']['newdir'], o.ies_unit, iesname, frame, o.ies_name)
                        subprocess.call(iescmd.split())
                        if o.type == 'LAMP':
                            if o.parent:
                                o = o.parent
                            lradfile += "!xform -rx {0[0]} -ry {0[1]} -rz {0[2]} -t {1[0]} {1[1]} {1[2]} {2}.rad\n\n".format([(180/pi)*o.rotation_euler[i] for i in range(3)], o.location, os.path.join(scene['viparams']['newdir'], iesname+"-{}".format(frame)))
                        elif o.type == 'MESH':
                            for face in o.data.polygons:
                                lradfile += "!xform -rx {0[0]:.3f} -ry {0[1]:.3f} -rz {0[2]:.3f} -t {1[0]:.3f} {1[1]:.3f} {1[2]:.3f} {2}{3}".format([(180/pi)*o.rotation_euler[i] for i in range(3)], o.matrix_world * face.center, os.path.join(scene['viparams']['newdir'], iesname+"-{}.rad".format(frame)), ('\n', '\n\n')[face == o.data.polygons[-1]])
                    elif iesname:
                        export_op.report({'ERROR'}, 'The IES file associated with {} cannot be found'.format(o.name))
            
            sradfile = "# Sky \n\n"
        radfiles.append(mradfile+gradfile+lradfile+sradfile)
    node['reslen'] = rti - 1
    node['radfiles'] = radfiles
    
    with open(scene['viparams']['filebase']+".rtrace", "w") as rtrace:
        rtrace.write(rtpoints)
    node['rtpoints'] = rtpoints
    
    scene['liparams']['fe'] = max(scene['liparams']['cfe'], scene['liparams']['gfe'])
    simnode = node.outputs['Geometry out'].links[0].to_node if node.outputs['Geometry out'].links else 0
    connode = simnode.connodes() if simnode else 0

    for frame in range(scene['liparams']['fs'], scene['liparams']['fe'] + 1):
        createradfile(scene, frame, export_op, connode, node)
        if kwargs:
            createoconv(scene, frame, export_op)

#def radcompexport(scene, export_op, node): 
#    skyfileslist = []
#    with open("{}-{}.sky".format(scene['viparams']['filebase'], 0), 'a') as skyfilea:
#        skyexport(node, skyfilea)
#    with open("{}-{}.sky".format(scene['viparams']['filebase'], 0), 'r') as skyfiler:
#        skyfileslist.append(skyfiler.read())
#    if node.hdr == True:
#        hdrexport(scene, 0, node)
#    node['skyfiles'] = skyfileslist
#    scene['viparams']['visimcontext'] = 'LiVi Compliance'

    
def radcbdmexport(scene, export_op, node, locnode, geonode):
    scene = bpy.context.scene
#    locnode = node.inputs['Location in'].links[0].from_node
    node['Animation'] = 'Static' if geonode.animmenu == 'Static' else 'Animated'
    if not node.fromnode:            
        node['source'] = node.sourcemenu if int(node.analysismenu) > 1 else node.sourcemenu2
        if node['source'] == '0':
            os.chdir(scene['viparams']['newdir'])
            pcombfiles = ''.join(["ps{}.hdr ".format(i) for i in range(146)])
            epwbase = os.path.splitext(os.path.basename(locnode.weather))
            if epwbase[1] in (".epw", ".EPW"):
                with open(locnode.weather, "r") as epwfile:
                    epwlines = epwfile.readlines()
                    epwyear = epwlines[8].split(",")[0]
                    subprocess.call(("epw2wea", locnode.weather, "{}.wea".format(os.path.join(scene['viparams']['newdir'], epwbase[0]))))
                    if node.startmonth != 1 or node.endmonth != 12:
                        with open("{}.wea".format(os.path.join(scene['viparams']['newdir'], epwbase[0])), 'r') as weafile:
                            wealines = weafile.readlines()
                            weaheader = [line for line in wealines[:6]]
                            wearange = [line for line in wealines[6:] if int(line.split()[0]) in range (node.startmonth, node.endmonth + 1)]
                        with open("{}.wea".format(os.path.join(scene['viparams']['newdir'], epwbase[0])), 'w') as weafile:  
                            [weafile.write(line) for line in weaheader + wearange] 
                    gdmcmd = ("gendaymtx -m 1 {} {}".format(('', '-O1')[node.analysismenu in ('1', '3')], "{0}.wea".format(os.path.join(scene['viparams']['newdir'], epwbase[0]))))
                    with open(os.path.join(scene['viparams']['newdir'], epwbase[0]+".mtx"), "w") as mtxfile:
                        Popen(gdmcmd.split(), stdout = mtxfile, stderr=STDOUT).wait()
                    mtxfile = open(os.path.join(scene['viparams']['newdir'], "{}.mtx".format(epwbase[0])), "r")
            else:
                export_op.report({'ERROR'}, "Not a valid EPW file")
                return
        
        elif node['source'] == '1' and int(node.analysismenu) > 1:
            mtxfile = open(node.mtxname, "r")

        if node['source'] == '0':
            if node.inputs['Location in'].is_linked:
                mtxlines = mtxfile.readlines()
                vecvals, vals = mtx2vals(mtxlines, datetime.datetime(int(epwyear), node.startmonth, 1).weekday(), node)
                mtxfile.close()
                node['vecvals'] = vecvals
                node['whitesky'] = "void glow sky_glow \n0 \n0 \n4 1 1 1 0 \nsky_glow source sky \n0 \n0 \n4 0 0 1 180 \nvoid glow ground_glow \n0 \n0 \n4 1 1 1 0 \nground_glow source ground \n0 \n0 \n4 0 0 -1 180\n\n"
                oconvcmd = "oconv -w - > {0}-whitesky.oct".format(scene['viparams']['filebase'])
                Popen(oconvcmd.split(), stdin = PIPE).communicate(input = node['whitesky'].encode('utf-8'))
                if int(node.analysismenu) < 2 or node.hdr:
                    vwcmd = "vwrays -ff -x 600 -y 600 -vta -vp 0 0 0 -vd 0 1 0 -vu 0 0 1 -vh 360 -vv 360 -vo 0 -va 0 -vs 0 -vl 0 | rcontrib -bn 146 -fo -ab 0 -ad 1 -n {} -ffc -x 600 -y 600 -ld- -V+ -f tregenza.cal -b tbin -o p%d.hdr -m sky_glow {}-whitesky.oct".format(scene['viparams']['nproc'], scene['viparams']['filename'])
                    subprocess.call(vwcmd.split())
                    [subprocess.call("pcomb -s {0} p{1}.hdr > ps{1}.hdr".format(vals[j], j).split()) for j in range(146)]
                    subprocess.call("pcomb -h {} > {}".format(pcombfiles, os.path.join(scene['viparams']['newdir'], epwbase[0]+".hdr")).split())
                    [os.remove(os.path.join(scene['viparams']['newdir'], 'p{}.hdr'.format(i))) for i in range (146)]
                    [os.remove(os.path.join(scene['viparams']['newdir'], 'ps{}.hdr'.format(i))) for i in range (146)]
                    node.hdrname = os.path.join(scene['viparams']['newdir'], epwbase[0]+".hdr")                    
                if node.hdr:
                    Popen("oconv -w - > {}.oct".format(os.path.join(scene['viparams']['newdir'], epwbase[0])).split(), stdin = PIPE, stdout=PIPE, stderr=STDOUT).communicate(input = hdrsky(os.path.join(scene['viparams']['newdir'], epwbase[0]+".hdr").encode('utf-8')))
                    subprocess.call('cnt 750 1500 | rcalc -f "'+os.path.join(scene.vipath, 'Radfiles', 'lib', 'latlong.cal')+'" -e "XD=1500;YD=750;inXD=0.000666;inYD=0.001333" | rtrace -af pan.af -n {} -x 1500 -y 750 -fac "{}{}{}.oct" > '.format(scene['viparams']['nproc'], os.path.join(scene['viparams']['newdir'], epwbase[0])) + '"'+os.path.join(scene['viparams']['newdir'], epwbase[0]+'p.hdr')+'"', shell=True)
            else:
                export_op.report({'ERROR'}, "No location node connected")
                return
        if node.hdrname and os.path.isfile(node.hdrname) and node.hdrname not in bpy.data.images:
            bpy.data.images.load(node.hdrname)
        
        if int(node.analysismenu) < 2:
            node['skyfiles'] = [hdrsky(node.hdrname)] 
    scene['viparams']['visimcontext'] = 'LiVi CBDM'
    
def sunexport(scene, node, locnode, frame): 
    if locnode:
        simtime = node.starttime + frame*datetime.timedelta(seconds = 3600*node.interval)
        solalt, solazi, beta, phi = solarPosition(simtime.timetuple()[7], simtime.hour + (simtime.minute)*0.016666, scene.latitude, scene.longitude)
        gsrun = Popen("gensky -ang {} {} {} -t {}".format(solalt, solazi, node['skytypeparams'], node.turb).split(), stdout = PIPE)
        return gsrun.stdout.read().decode()
    else:
        gsrun = Popen("gensky -ang {} {} {}".format(45, 0, node['skytypeparams']).split(), stdout = PIPE)
        return gsrun.stdout.read().decode()
        
def hdrexport(scene, f, frame, node, skytext):    
    with open('{}-{}sky.oct'.format(scene['viparams']['filebase'], frame), 'w') as skyoct:
        Popen('oconv -w -'.split(), stdin = PIPE, stdout = skyoct).communicate(input = skytext.encode('utf-8'))
    subprocess.call("rpict -vta -vp 0 0 0 -vd 0 1 0 -vu 0 0 1 -vh 360 -vv 360 -x 1500 -y 1500 {}-{}sky.oct > {}".format(scene['viparams']['filebase'], frame, os.path.join(scene['viparams']['newdir'], str(frame)+".hdr")), shell = True)
    subprocess.call('cnt 750 1500 | rcalc -f {} -e "XD=1500;YD=750;inXD=0.000666;inYD=0.001333" | rtrace -af pan.af -n {} -x 1500 -y 750 -fac {}-{}sky.oct > {}'.format(os.path.join(scene.vipath, 'Radfiles', 'lib', 'latlong.cal'), scene['viparams']['nproc'], scene['viparams']['filebase'], frame, os.path.join(scene['viparams']['newdir'], str(frame)+'p.hdr')), shell = True)
    if '{}p.hdr'.format(frame) not in bpy.data.images:
        bpy.data.images.load(os.path.join(scene['viparams']['newdir'], "{}p.hdr".format(frame)))
    else:
        bpy.data.images['{}p.hdr'.format(frame)].reload()

def skyexport(node):
    skytext = "4 .8 .8 1 0\n\n" if node['skynum'] < 3 else "4 1 1 1 0\n\n"
    return "\nskyfunc glow skyglow\n0\n0\n" + skytext + "skyglow source sky\n0\n0\n4 0 0 1  180\n\n"

def hdrsky(skyfile):
    return("# Sky material\nvoid colorpict hdr_env\n7 red green blue {} angmap.cal sb_u sb_v\n0\n0\n\nhdr_env glow env_glow\n0\n0\n4 1 1 1 0\n\nenv_glow bubble sky\n0\n0\n4 0 0 0 5000\n\n".format(skyfile))

def createradfile(scene, frame, export_op, connode, geonode):    
    if not connode or not connode.get('skyfiles'):
        radtext = geonode['radfiles'][0] if scene['liparams']['gfe'] == 0 else geonode['radfiles'][frame]
    elif not geonode:
        skyframe = frame if scene['liparams']['cfe'] > 0 else 0
        radtext = connode['skyfiles'][skyframe]
    elif geonode and connode: 
        geoframe = frame if scene['liparams']['gfe'] > 0 and not geonode.inputs['Generative in'].links else 0
        skyframe = frame if scene['liparams']['cfe'] > 0 and not geonode.inputs['Generative in'].links else 0
        radtext = geonode['radfiles'][geoframe] + connode['skyfiles'][skyframe]# if len(geonode['radfiles']) == 1 else geonode['radfiles'][geoframe] + connode['skyfiles'][0]
    
    with open("{}-{}.rad".format(scene['viparams']['filebase'], frame), 'w') as radfile:
        radfile.write(radtext)
   
    if not bpy.data.texts.get('Radiance input-{}'.format(frame)):
        bpy.data.texts.new('Radiance input-{}'.format(frame))
        
    bpy.data.texts['Radiance input-{}'.format(frame)].clear()
    bpy.data.texts['Radiance input-{}'.format(frame)].write(radtext)    

def createoconv(scene, frame, export_op, **kwargs):
    fbase = "{0}-{1}".format(scene['viparams']['filebase'], frame)
    with open("{}.oct".format(fbase), "w") as octfile:
        subprocess.call(("oconv", "{}.rad".format(fbase)), stdout = octfile)
    export_op.report({'INFO'},"Export is finished")

def cyfc1(self):
    scene = bpy.context.scene
    if 'LiVi' in scene['viparams']['resnode'] or 'Shadow' in scene['viparams']['resnode']:
        for material in [m for m in bpy.data.materials if m.use_nodes and m.mattype in ('1', '2')]:
            try:
                if any([node.bl_label == 'Attribute' for node in material.node_tree.nodes]):
                    material.node_tree.nodes["Attribute"].attribute_name = str(scene.frame_current)
            except Exception as e:
                print(e, 'Something wrong with changing the material attribute name')

    if scene['viparams']['resnode'] == 'VI Sun Path':
        spoblist = {ob.get('VIType'):ob for ob in scene.objects if ob.get('VIType') in ('Sun', 'SPathMesh')}
        beta, phi = solarPosition(scene.solday, scene.solhour, scene['latitude'], scene['longitude'])[2:]
        if bpy.data.worlds.get('World'):
            if bpy.data.worlds["World"].use_nodes == False:
                bpy.data.worlds["World"].use_nodes = True
            nt = bpy.data.worlds[0].node_tree
            if nt and nt.nodes.get('Sky Texture'):
                bpy.data.worlds['World'].node_tree.nodes['Sky Texture'].sun_direction = -sin(phi), -cos(phi), sin(beta)
        
        for ob in scene.objects:
            if ob.get('VIType') == 'Sun':
                ob.rotation_euler = pi * 0.5 - beta, 0, -phi
                if ob.data.node_tree:
                    for blnode in [blnode for blnode in ob.data.node_tree.nodes if blnode.bl_label == 'Blackbody']:
                        blnode.inputs[0].default_value = 2500 + 3000*sin(beta)**0.5
                    for emnode in [emnode for emnode in ob.data.node_tree.nodes if emnode.bl_label == 'Emission']:
                        emnode.inputs[1].default_value = 10 * sin(beta)
            
            elif ob.get('VIType') == 'SPathMesh':
                ob.scale = 3 * [scene.soldistance/100]
            
            elif ob.get('VIType') == 'SkyMesh':
                ont = ob.data.materials['SkyMesh'].node_tree
                if ont and ont.nodes.get('Sky Texture'):
                    ont.nodes['Sky Texture'].sun_direction = sin(phi), -cos(phi), sin(beta)
            
            elif ob.get('VIType') == 'SunMesh':                
                ob.scale = 3*[scene.soldistance/100]
                ob.location.z = spoblist['Sun'].location.z = spoblist['SPathMesh'].location.z + scene.soldistance * sin(beta)
                ob.location.x = spoblist['Sun'].location.x = spoblist['SPathMesh'].location.x -(scene.soldistance**2 - (spoblist['Sun'].location.z-spoblist['SPathMesh'].location.z)**2)**0.5  * sin(phi)
                ob.location.y = spoblist['Sun'].location.y = spoblist['SPathMesh'].location.y -(scene.soldistance**2 - (spoblist['Sun'].location.z-spoblist['SPathMesh'].location.z)**2)**0.5 * cos(phi)
                if ob.data.materials[0].node_tree:
                    for smblnode in [smblnode for smblnode in ob.data.materials[0].node_tree.nodes if ob.data.materials and smblnode.bl_label == 'Blackbody']:
                        smblnode.inputs[0].default_value = 2500 + 3000*sin(beta)**0.5
    else:
        return