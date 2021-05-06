# dmfwizard

A python library to make it easier to experiment with digital microfluidics.

## What it does
<p align="center">
  <img class="align-center" src="images/electrode_board.png?raw=true" width=400 />
</p>

DMF devices use arrays of electrodes laid out on a subtrate to control small
droplets of fluids. One really cheap and easy way to fabricate these substrates
is as printed circuit boards (PCBs). [KiCad](https://www.kicad.org) is open source
software for designing PCBs, but laying out a complex pattern of electrodes in
KiCad can be cumbersome and slow, and this makes iterating and trying different
designs more difficult.

Fortunately, KiCad also uses simple file formats, and has a python scripting
interface that makes it fairly easy to programmatically control the layout of
design. The dmfwizard python package takes care of some of the gritty details
of defining the electrode layout, like creating the jagged crenellations between
electrodes that improve droplet transport, and ensuring the design meets the
required copper-to-copper clearance rules everywhere.

It is essentially a domain-specific-language for describing the board layout in
a python script, and then exporting all of the information necessary to
automatically place all of the electrodes in [pcbnew](https://docs.kicad.org/5.0/en/pcbnew/pcbnew.html).

It also helps to generate the layout information used by the [PurpleDrop driver
software](https://github.com/uwmisl/purpledrop-driver): the "board definition"
file.

## Documentation

Documentation is hosted at <https://dmfwizard.readthedocs.io>. There's an
example project in [the examples directory](examples/) of this repo, and a
[corresponding tutorial](https://dmfwizard.readthedocs.io/en/latest/tutorials/basic.html).

This project is currently tested with KiCad v5.10, and likely works with all
5.x versions of KiCad. When KiCad 6.x is released, there are likely to be some
incompatibilities that will require updates to dmfwizard.

The [kicad_component_layout](https://github.com/mcbridejc/kicad_component_layout)
plugin is used to import the component placement information into pcbnew.
