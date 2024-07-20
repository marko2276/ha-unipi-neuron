# ha-unipi-neuron
Custom Home Assistant (HA) integration for [Unipi](https://www.unipi.technology) devices. In my home assistant project, I use Neron type of products but the component should work as well with other products (Axon, Patron, Lite) where [Evok API](https://github.com/UniPiTechnology/evok) can be run. (Support for EVOK v3 is also there, where some of the API's have been changed)

The system connects to the Unipi device via WebSocket (part of a separate [python package](https://pypi.org/project/evok-ws-client/) wrapper). This bidirectional management connection enables a blazing fast user experience and although Neuron devices support directSwitch functionality (I do use it for light switches), you will most likely not see any difference between it or if you let HA do the desired action. The latency between an input signal change and an action executed by HA is very low.

I was planning (this is still on my wishlist) to integrate the component directly into the home-assistant repo but to get things available for others to use, play around and extend, I decided to just release it as a barebone repo for now.

# Installation

1. Make sure that EVOK is installed and running on your Unipi devices.

2. Configure Unipi device I/Os.

1. Simply copy the custom_components folder to your own Home Assistant /config folder.

2. Change your configuration yaml file with the desired configuration.

# Supported features
Functionality-wise, it supports the bare minimum (multiple device instances, lights, binary sensors and covers) so that my home-assistant project works.

## TODO
There are tons of things that are missing or could be added.
Part of my backlog items are support for MODBUS, 1-Wire sensors, automatic Neuron configuration, etc.

# Configuration

Example of Basic config for three Unipi Neuron devices.<br/>
the type parameter is not used for any specific purpose but one should set it to either "L203", "M203" or "S203". Other parameters should be self-explanatory.
```yaml
#Unipi neuron
unipi_neuron:
  - name: "device1"
    type: L203
    ip_address: 192.168.11.23
    reconnect_time: 30
  - name: "device2"
    type: M203
    ip_address: 192.168.11.21
    reconnect_time: 30
  - name: "device3"
    type: L203
    ip_address: 192.168.11.24
    reconnect_time: 30
```
## Light component
Two modes are supported:<br/>
"on_off" - simple on or off type of outputs.<br/>
"pwm" - PWM type dimming (available only on digital output pins).<br/>

Port names are the same as defined in Evok API.<br/>

Note: the behavior of Unipi I/O's is configured on the Unipi device itself. So if PWM mode is used by HA, then the target output pin on Unipi must be configured accordingly.

```yaml
#configuration.yaml
light:
  - platform: unipi_neuron
    device_id: "device1"
    devices:
      - name: "Light bathroom"
        device: relay
        mode: "on_off"
        port: "1_01"
      - name: "Light bedroom"
        device: relay
        mode: "on_off"
        port: "3_06"
  - platform: unipi_neuron
    device_id: "device2"
    devices:
      - name: "Light kitchen"
        device: relay
        mode: "on_off"
        port: "1_01"
      - name: "Light staircase"
        device: relay
        mode: "pwm"
        port: "1_02"
```
Note: the device entity name for relay output has changed in EVOK v3 (from "relay" to "ro") and above config example should be adjusted accordingly, if EVOK v3 is used.

## Binary sensor component
Port names are the same as defined in Evok API<br/>
```yaml
#configuration.yaml
binary_sensor:
  - platform: unipi_neuron
    device_id: "device3"
    devices:
      - name: switch_up_utility
        device: input
        port: "2_01"
      - name: switch_down_utility
        device: input
        port: "2_08"
      - name: switch_light_toilet
        device: input
        port: "2_02"
```
Note: the device entity name for digital input has changed in EVOK v3 (from "input" to "di") and above config example should be adjusted accordingly, if EVOK v3 is used.


## Cover component
Used to manage dummy cover/blinds that only support driving motor up and down ( without any ability or sensor to detect the location of the blinds or tilt)

Warning: Based on the cover supplier documentation, driving both signals up and down at the same time may damage the motor. Well in fact this happened to me once but it was not the motor that burned, it was the relay outputs on my Unipi! Anyhow I have added a couple of checks in the code to prevent such a situation but there may still be corner cases that are not fully covered - so use it with caution :). Use this software at your own risk! I do not take responsibility in any way.

port_up and port_down are output ports used to drive blinds up and down.<br/>
full_close_time and full_open_time define the time it takes for the blind to fully open (from a closed state) or fully close (from an open state) in seconds.<br/>
tilt_change_time defines the time (in seconds) that the tilt changes from fully open to fully closed state (and vice-versa) <br/>
min_reverse_dir_time minimum time between changing the direction of the motor (in seconds) - defined by the blind motor supplier.<br/>

```yaml
#configuration.yaml
cover:
  - platform: unipi_neuron
    device_id: "main_level_1"
    covers:
      cover_utility:
        device: relay
        port_up: "2_01"
        port_down: "2_08"
        full_close_time: 40
        full_open_time: 40
        tilt_change_time: 1.5
        min_reverse_dir_time: 1
        name: "Cover_utility"
        device_class: "blind"
        friendly_name: "Cover Utility"
      cover_bedroom:
        device: relay
        port_up: "2_06"
        port_down: "2_07"
        full_close_time: 40
        full_open_time: 40
        tilt_change_time: 1.5
        min_reverse_dir_time: 1
        name: "Cover_bedroom"
        device_class: "blind"
        friendly_name: "Cover Bedroom"
```
# Feedback
Your feedback, pull requests and any other contribution are welcome.
# License
MIT License
