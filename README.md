# ha-unipi-neuron
Custom Home Assistant (HA) integration for [Unipi](https://www.unipi.technology) devices. In my home assistant project I use neron type of products, but the component should work as well on other products (Axon, Patron, Lite) where [Evok API](https://github.com/UniPiTechnology/evok) can be run.

The system connect to the Unipi device via websocket (part of a separate [python package](https://pypi.org/project/evok-ws-client/) wrapper). This bidirectional management connection enable a blazingly fast user experience and although Neuron devices enables directSwitch functionality (I do use it for light switches), you will almost not see any difference between it or if you let HA do the desired action. Latency between an input signal change and action executed by HA is very low.

I was planning (this is still on my whish list) to integrate the component directly into home-assistant repo but to get things available for others to use, play around and extend, I decided to just release it as a barebone repo for now.

# Usage
# Installation

1. Make sure that EVOK is installed and running on your Unipi devices.

2. Configure Unipi device I/Os.

1. Simply copy the custom_components folder to your own Home Assistant /config folder.

2. Change you configuration yaml file with desired configuration.

# Supported features
Functionality wise, it supports bare minimum (multiple device instances, lights, binary sensors and covers) so that my home-assistant project works.

## TODO
There are tons of things that ar missing or could be added.
Part of my backlog items are: support for MODBUS, 1-Wire sensors, automatic Neuron configuration, etc. 

# Configuration

Example of Basic config for three Unipi Neuron devices. type parameter is not used, others should be self explanatory.
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

Note: Behavior of Unipi I/O's is configured on the Unipi device itself. So if if PWM mode is used by HA, then target output pin on Unipi must be configured accordingly.

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

## Binary sensor component
Port names are the same as defined in Evok API 
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


## Cover component
Used to manage dummy cover/blinds that only support driving motor up and down. No ability to detect location of the blind.

Warning: Based on my cover supplier, driving both signals on up and down my damage the motor. Well in fact this happened to me once but it was not the motor that burned, it was relay outputs on my Unipi! Anyhow I have added a couple of check in the code to prevent this situation but there may still be corner cases that are not fully covered - so use it with caution :) 

port_up and port_down are output ports used to drive blinds up and down.<br/>
full_close_time and full_open_time define the time it takes for blind to fully open (from closed state) or fully close (from open state) in seconds.<br/>
tilt_change_time defines time (in seconds) that the tilt changes (the same for opening or closing the tilt)<br/>
min_reverse_dir_time minimum time between changing the direction of the motor (in seconds) - defined by blind motor supplier.<br/>

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
Your feedback or pull requests or any other contribution is welcome.
# License
MIT License
