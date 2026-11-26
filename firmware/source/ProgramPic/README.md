# ProgramPic
Arduino sketch for programming pic controllers.

## Overview
If you would search the internet you will find quite some DIY pic programmers.
However, those designs often either require a true serial or parallel port
instead of an easily available USB port or are designed around a pre-programmed
controller assuming access to a programmer.

A compelling alternative would be the use of an Arduino as in the ArdPicProg.
Load the Arduino sketch, the host program and add a prototype shield with a very
limited number of additional components to build your pic programmer.
This programmer features also a ICD connector and an RJ-11 jack (ICD2) interface.
The complete project including hard- and software is open source and is released
under the GNU General Public License Version 3.
You can build your own ArdPicProg by using the available kit or especially designed PCB.

The complete construction and use of the ArdPicProg is described
in more detail [there](https://makerprojekte.de/en/arduino-pic-programmer/).

## Firmware wiring profile used by this application

The sketch compiled and uploaded by this repository uses a project-specific
Arduino pin map (including the active-low VPP-switch control):

| Arduino Nano pin | Sketch define | Connection |
| --- | --- | --- |
| A1 | `PIN_MCLR` | Low-voltage control input of external MCLR/VPP switch; HIGH=reset/VPP off, LOW=select external ~13 V VPP |
| D2 | `PIN_VDD` | Switched +5 V to PIC target VDD |
| D4 | `PIN_CLOCK` | PIC RB6/PGC clock (PIC16F84A pin 12) |
| D7 | `PIN_DATA` | Bidirectional PIC RB7/PGD data (PIC16F84A pin 13) |
| A5 | `PIN_ACTIVITY` | LED anode through resistor; LED cathode to GND |
| GND | — | Common Arduino/PIC/VPP/VDD ground; PIC16F84A VSS is pin 5 |

For the PIC16F84A, connect target VDD to pin 14 and add 100 nF between pins
14 and 5 close to the PIC. **Never connect the external VPP rail directly to A1
or any Arduino GPIO**; A1 must only drive the low-voltage input of a suitable
VPP switching circuit. This map differs from the original upstream sketch
wiring, so upstream hardware pictures must not be used as the wiring authority
for this application build.
