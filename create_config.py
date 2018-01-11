#!/usr/bin/env python
# -*- coding: utf-8 -*-

#    This script creates configuration files for conky and lua based on
#    your machines's current resources.
#    Copyright (C) 2017  popi
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see ihttp://www.gnu.org/licenses/gpl.html.

# Modified by A-A-G

from __future__ import print_function
import argparse
import time
import platform
import re
from collections import OrderedDict
import sys
from os import getcwd
import logging as log

# Defaults is blue metrics and white font
## blue     | 34cdff
## white    | efefef

# for LUA config, this should not be changed.
default_fg_color = '0x34cdff'

couleurs = {
        'yellow': 'fffd1d',
        'orange': 'ff8523',
        'red': 'ff1d2b',
        'green': '1dff22',
        'pink': 'd70751',
        'skyblue': '8fd3ff',
        'brown': 'd7bd4c',
        'blue': '165cc4',
        'iceblue': '43d2e5',
        'white': 'efefef',
        'grey': '323232',
        'black': '000000',
        'violet': 'bb07d7',
        'ASSE': '006a32'
        }

def init(rings, title, text, reload):
    """Initialisation of colors
    """
    # Keeping previous colors?
    if reload:
        with open(dest_conky, 'r') as f:
            filedata = f.read() 
            matchconky = re.findall('^ +color[01] = \'#([0-9a-f]{6})', filedata, re.M)
            print('colors were: {}'.format(matchconky))

        with open(dest_lua, 'r') as f:
            filedata = f.read() 
            matchlua = re.findall('^normal="0x([0-9a-f]{6})"', filedata, re.M)
            print('colors were: {}'.format(matchlua))
            crings = '0x'+matchlua[0]
            # for conky
            ctitle = '#'+matchconky[0]
            ctext = '#'+matchconky[1]
    else:
        # for lua
        crings = '0x'+couleurs[rings]
        # for conky
        ctitle = '#'+couleurs[title]
        ctext = '#'+couleurs[text]
 
    ctextsize = '8'

    return crings, ctitle, ctext, ctextsize

def read_conf(filename):
    """ Read file in variable and returns it
    """
    try:
        with open(filename, 'r') as f:
            filedata = f.read();
    except IOError:
        log.error("[Error] Could not open {}".format(filename))
        return 1
    return filedata

def write_conf(filedata, dest):
    """ Write new config file
    """
    try:
        with open(dest, 'w') as f:
            f.write(filedata);
    except IOError:
        log.error("[Error] Could not open {}".format(dest))
        return 1

def write_color_lua():
    """ Last function called
    """
    datain = read_conf(dest_lua)
    filedata = datain.replace(default_fg_color, crings)
    write_conf(filedata, dest_lua)

def write_conf_blank(src, dest, width, height):
    """ Reload new config file from template
    """
    filedata = read_conf(src)
    log.info('Overwriting config file {}'.format(dest))
    filedata = filedata.replace('--{{ COLOR0 }}', "  color0 = '{}',".format(ctitle))
    filedata = filedata.replace('--{{ COLOR1 }}', "  color1 = '{}',".format(ctext))
    filedata = filedata.replace('--{{ FONTTEXT }}', "  font = 'Play:normal:size={}',".format(ctextsize))
    filedata = filedata.replace('{{ WORKING_DIR }}', "{}".format(working_dir))
    filedata = filedata.replace('--{{ SIZE }}', "  minimum_width = {},\n  minimum_height = {},".format(width, height))
	
    write_conf(filedata, dest)

def cpu_number():
    """ Looks for number of CPU threads
    """
    with open('/proc/cpuinfo') as f:
        nbcpu = 0
        for line in f:
        # Ignore the blank line separating the information between
        # details about two processing units
            if line.strip():
                if line.rstrip('\n').startswith('cpu MHz'):
                    nbcpu += 1
    return nbcpu

def write_conf_lua(temp_factor, mem_factor, gpu_factor, radius, start_angle, end_angle, space, empty_rings_in_middle, alpha):
    """ Prepare lua config for CPU
    """
    cpunb = cpu_number()
    ringconf_lua = []
    additional_rings = 0
    if temp_factor:
      additional_rings = additional_rings + 1
    if mem_factor:
      additional_rings = additional_rings + 1
    if gpu_factor:
      additional_rings = additional_rings + 1
    thickness = (radius-((cpunb+empty_rings_in_middle+additional_rings)*space))/(cpunb+empty_rings_in_middle+temp_factor+mem_factor+gpu_factor)
    temp_thickness = thickness * temp_factor
    mem_thickness = thickness * mem_factor
    gpu_thickness = thickness * gpu_factor

    if gpu_factor:
        log.info('We have {} GPU thickness factor. Adding to lua config.'.format(mem_factor))
        radius = radius - 0.5 * gpu_thickness
        data = {
            'bg_alpha': alpha,
            'radius': radius,
            'name': "exec nvidia-smi -a | grep -m 1 Gpu | awk '{print $3}'",
            'thickness': gpu_thickness,
            'start_angle': start_angle,
            'end_angle': end_angle
            }
        
        new_block = """\n    {{
        name="{name}",
        arg='',
        max=100,
        bg_colour=0x3b3b3b,
        bg_alpha={bg_alpha},
        fg_colour=0x34cdff,
        fg_alpha=0.8,
        x=500, y=500,
        radius={radius},
        thickness={thickness},
        start_angle={start_angle},
        end_angle={end_angle}
    }},""".format(**data)
        
        ringconf_lua.append(new_block)
        radius = radius -0.5 * gpu_thickness - space
    
    if mem_factor:
        log.info('We have {} Memory thickness factor. Adding to lua config.'.format(mem_factor))
        radius = radius - 0.5 * mem_thickness
        data = {
            'bg_alpha': alpha,
            'radius': radius,
            'thickness': mem_thickness,
            'start_angle': start_angle,
            'end_angle': end_angle
            }
        
        new_block = """\n    {{
        name='memperc',
        arg='',
        max=100,
        bg_colour=0x3b3b3b,
        bg_alpha={bg_alpha},
        fg_colour=0x34cdff,
        fg_alpha=0.8,
        x=500, y=500,
        radius={radius},
        thickness={thickness},
        start_angle={start_angle},
        end_angle={end_angle}
    }},""".format(**data)
        
        ringconf_lua.append(new_block)
        radius = radius -0.5 * mem_thickness - space

    log.info('We have {} CPUs. Adding to lua config.'.format(cpunb))
    radius = radius - 0.5 * thickness
    for cpt in range (cpunb):
        data = {
            'arg': "cpu{}".format(cpt+1),
            'bg_alpha': alpha,
            'radius': radius,
            'thickness': thickness,
            'start_angle': start_angle,
            'end_angle': end_angle
            }

        new_block = """\n    {{
        name='cpu',
        arg='{arg}',
        max=100,
        bg_colour=0x3b3b3b,
        bg_alpha={bg_alpha},
        fg_colour=0x34cdff,
        fg_alpha=0.8,
        x=500, y=500,
        radius={radius},
        thickness={thickness},
        start_angle={start_angle},
        end_angle={end_angle}
    }},""".format(**data)

        ringconf_lua.append(new_block)
        radius -= (thickness + space)
        
    if temp_factor:
        log.info('We have {} Temperature thickness factor. Adding to lua config.'.format(temp_factor))
        radius = radius + 0.5 * thickness - 0.5 * temp_thickness
        data = {
            'bg_alpha': alpha,
            'temp_radius': radius,
            'thickness': temp_thickness,
            'start_angle': start_angle,
            'end_angle': end_angle
            }
        
        new_block = """\n    {{
        name='hwmon',
        arg='temp 1',
        max=110,
        bg_colour=0x3b3b3b,
        bg_alpha={bg_alpha},
        fg_colour=0x34cdff,
        fg_alpha=0.8,
        x=500, y=500,
        radius={temp_radius},
        thickness={thickness},
        start_angle={start_angle},
        end_angle={end_angle}
    }},""".format(**data)
        
        ringconf_lua.append(new_block)

    print('Writing generated LUA config in config file')
    filedata = read_conf(dest_lua)
    filedata = filedata.replace('--{{ GEN }}', ''.join(ringconf_lua))
    if gpu_factor>0:
      filedata = filedata.replace('--{{GPU_WATCH}}', '	gpu_watch()')
    if mem_factor>0:
      if gpu_factor>0:
        filedata = filedata.replace('--{{MEMORY_WATCH}}', '  memory_watch(2)')
      else:
        filedata = filedata.replace('--{{MEMORY_WATCH}}', '  memory_watch(1)')
    write_conf(filedata, dest_lua)

# main
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Creates/overwrites conky and lua configuration for conky-grapes adjustments to your system.')
    parser.add_argument('-ri', '--color_rings', dest='rings', metavar='COLOR_RINGS',
                        default='blue', choices=couleurs,
                        help='the textual color for the rings and titles, among: {0}'
                        .format(' '.join(couleurs.keys()))
                        )
    parser.add_argument('-ti', '--color_title', dest='title', metavar='COLOR_TITLE',
                        default='blue', choices=couleurs,
                        help='the textual color for the title display, see COLOR_RINGS \
                            for accepted values.'''
                        )
    parser.add_argument('-te', '--color_text', dest='text', metavar='COLOR_TEXT',
                        default='white', choices=couleurs,
                        help='the textual color for the text display, see COLOR_RINGS \
                            for accepted values.'
                       )
    parser.add_argument('-v', '--verbose', dest='verbose', action="store_true",
                        help='verbose mode, displays gathered info as we found it.'
                       )
    parser.add_argument('-r', '--reload', dest='reload', action="store_true",
                        help='Only refresh configuration resource-wise. Colors will stay the same as previously.'
                       )
    parser.add_argument('-t', '--temp', dest='temp', action="store", default=0.5,  type=float,
                        help='Temperature ring thickness factor. 0 for no ring (default=0.5).'
                       )
    parser.add_argument('-m', '--memory', dest='mem', action="store", default=2, type=float,
                        help='Memory ring thickness factor. 0 for no ring (default=2).'
                       )
    parser.add_argument('-w', '--width', dest='width', action="store", default=1000, type=float,
                        help='Conky width (default=1000).'
                       )
    parser.add_argument('-he', '--height', dest='height', action="store", default=1000, type=float,
                        help='Conky height (default=1000).'
                       )
    parser.add_argument('-sa', '--startAngle', dest='start_angle', action="store", default=0, type=float,
                        help='Start angle (default=0).'
                       )
    parser.add_argument('-ea', '--endAngle', dest='end_angle', action="store", default=359, type=float,
                        help='End angle (default=359).'
                       )
    parser.add_argument('-s', '--space', dest='space', action="store", default=2, type=float,
                        help='Space between two rings (default=2).'
                       )
    parser.add_argument('-em', '--middle', dest='empty_rings_in_middle', action="store", default=5, type=float,
                        help='Empty rings in the middle (default=5).'
                       )
    parser.add_argument('-a', '--alpha', dest='alpha', action="store", default=0.7, type=float,
                        help='Ring background alpha (default=0.7).'
                       )
    parser.add_argument('-wd', '--workingDir', dest='working_dir', action="store",
                        help='Working directory with template files.'
                       )
    parser.add_argument('-ng', '--nvidiaGPU', dest='gpu', action="store", default=0, type=float,
                        help='Nvidia GPU ring thickness factor (default=0 for no ring). Uses nvidia-smi command.'
                       )
    
    args = parser.parse_args()
    # Log Level
    if args.verbose:
        log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        log.info("Verbose output.")
    else:
        log.basicConfig(format="%(levelname)s: %(message)s")

    log.info('Arguments received: {}'.format(args))
    
    if args.working_dir==None:
      working_dir=getcwd()
    else:
      working_dir=args.working_dir
      
    log.info('Working directory is: {}'.format(working_dir))
    src_lua = working_dir+'/rings_tpl'
    dest_lua = working_dir+'/rings_gen.lua'
    src_conky = working_dir+'/conky_tpl'
    dest_conky = working_dir+'/conky_gen.conkyrc'

    # init file
    crings, ctitle, ctext, ctextsize = init(args.rings, args.title, args.text, args.reload)
    write_conf_blank(src_lua, dest_lua, args.width, args.height)
    write_conf_blank(src_conky, dest_conky, args.width, args.height)

    # LUA
    radius = 0.5*max(args.width, args.height)
    print("""\nCreating configuration for a conky with width={} and height={}, resulting in a radius of {}\n\n""".format(args.width, args.height, radius))
    write_conf_lua(args.temp, args.mem, args.gpu, radius, args.start_angle, args.end_angle, args.space, args.empty_rings_in_middle, args.alpha)

    write_color_lua()

    print ("""\nSuccess!\nNew config files have been created:\n- {}\n- {} \n\n\
If conky is not running, you can activate it with following command:\n 
conky -q -d -c {}conky_gen.conkyrc\n\n"""
         .format(dest_conky, dest_lua, working_dir)
         )

