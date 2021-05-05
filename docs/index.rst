DMFWizard Documentation
=======================

DMF Wizard is a python package to make programmatic design of PCB 
electrode patterns for digital microfluidic device easier. It supports: 

- Laying out uniform grids of square electrodes, and created jagged 
  "crenellated" edges at their interface to improve drop transfer between
  neighboring electrodes while maintaining the minimum design spacing between
  all copper.
- Importing custom "peripheral" designs with one or more irregular electrode
  shapes from DXF files, which can be exported from CAD tools such as Solidworks, 
  Fusion 360, or FreeCAD.
- Exporting footprints and component placement information which can be used
  in KiCad during board layout.
- Creating silkscreen fiducial footprints

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   command
   api/index
   tutorials/index

