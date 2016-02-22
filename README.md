# SerialPlot

A serial data plotting and analysis tool.

## Config
Configuration is done using a python config script which can be edited from the app. The config
script calls the `config` function to setup. The following parameters are supported by the `config`
function.
+ `plotLabels` - The label from the data streams that will be plotted. This is should be an array of
                 strings or tuples. if tuple, it is interpreted as a (label, color) pair. eg: `("encoder", "#00FFFF")`
+ `serialPort` - The serial port from which to read data.
+ `serialBaudRate` - The baudrate for the serial communication
+ `serialTimeout` - Serial readline timeout
+ `parseLine` - A function that parses the raw line from the input stream. The function that accepts a raw line
                and returns a tuple of (time, label, value). Return None for all other cases.
+ `processLine`- A function that pre-processes the tuple from the data stream. The function that accepts a time, label, value
                 and returns a tuple of (time, label, value).

## Screenshot
![Screenshot](./screenshot.PNG?raw=true "Screenshot")
