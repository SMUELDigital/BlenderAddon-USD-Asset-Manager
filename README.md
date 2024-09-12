# BlenderAddon USD Stage Manager

*Vision* 

This addon should help to get a similar interface and pipeline to the Houdini Solaris. The goal is to get a proper import/export function and have a usd editor for adjusting the hierachy. 

*Present*

At the moment, the addon works with setup the USD Stage Structure inside Blender 4.2 LTS as you might know in SideFX Houdini. Please be aware that there are some known issues indicated with every released version.

*Help/Colab*

Please feel free to contribute your ideas/functions as well with reaching out. 
Many thanks


*Installation Blender 4.2 LTS*

1.) Download the zip file from the Github repository into your addons library. Open Blender and proceed with the normal addon installation from disc. If the name of the addon does not appear, try searching for it by name and activate it if it is not already activated by Blender.
2.) The panel is located in the Collection Properties under the Exporters tab. Assemble your scene first, for the last steps make a full copy of your scene, change the name of the scene (root empty takes the same name automatically) and press the button Create USD Layer for the USD Stage Setup. 
3.) Then go to the Exporters tab where the addon has already created the USD exporter. For the first time you will need to select a preset for your final USD export settings. After the first time, you can select it manually from the drop-down menu to save some time. In the future this should be integrated and set automatically for you.
