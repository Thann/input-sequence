#!/bin/env python

# multi-tap sequence mapping config
sequence_mapping = {
  # 'TRIGGER_KEY': ('SIMULATE_KEY', ..., COOLDOWN_MS)
    'KEY_W': ('KEY_5', 'KEY_4', 'KEY_3', 'KEY_2', 4000),
    # w5432wwwwwwwwww5432wwww...
}
double_tap_time = 1000  # milliseconds


################################################################################
################################################################################
################################################################################


import evdev
from evdev import UInput, ecodes

remapping = {ecodes.ecodes[key]: tuple(ecodes.ecodes[v]
                                       for v in value[:-1]) + value[-1:]
             for key,value in sequence_mapping.items()}
print(remapping)

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

for device in devices:
    print(device.path, device.name, device.phys)
# TODO: ask which device? argv?

device = evdev.InputDevice('/dev/input/event10')
print(device)
ui = UInput.from_device(device, name='input-sequence-keyboard')
device.grab()

downs = {}

try:
    for event in device.read_loop():
        if event and event.type == evdev.ecodes.EV_KEY:
            print(' ->', evdev.categorize(event), "--", event.value)
            if event.code == ecodes.KEY_C and any(k for k in device.active_keys(verbose=True) if k[0].endswith("CTRL")):
                print("shutting down...")
                break  # exit on CTRL-C

            sequence = remapping.get(event.code)
            if sequence:
                prev = downs.get(event.code)
                if prev:
                    print("PREV:", prev, '---', event.sec - prev[0], event.usec - prev[1])
                if event.value == 1:  # key-down
                    cooldown = sequence[-1]
                    cdt = prev and prev[0] + cooldown / 1000
                    dtt = prev and prev[0] + double_tap_time / 1000
                    if prev and prev[2]%2 == 1 and (event.sec < dtt or (
                          (event.sec == dtt and event.usec < prev[1] + (double_tap_time%1000)*1000))):
                        # if not cooling down and before the double-tap-timeout,
                        # multi-tapped!
                        idx  = int((prev[2]+1)/2)
                        if len(sequence) > idx:
                            sim_code = sequence[idx-1]
                            # print(f" ----> DOWN[{idx+1}]:", ecodes.KEY[sim_code])
                            print(f" ----> DOWN[{idx+1}]:", sim_code)
                            downs[event.code] = (event.sec, event.usec, prev[2] +1)
                            ui.write(ecodes.EV_KEY, sim_code, event.value)
                            ui.syn()
                            continue  # dont forward
                        else:
                            print(" -- end of sequence -- ")
                            downs[event.code] = prev[:2] + (0,)
                    elif not prev or prev[2] == 1 or event.sec > cdt or (
                          (event.sec == cdt and event.usec > prev[1] + (cooldown%1000)*1000)):
                        # if the last press was a single-tap, or past the cooldown period
                        print(" -- single tap --")
                        downs[event.code] = (event.sec, event.usec, 1)
                    else:
                        print(" -- cooling down -- ")

                elif prev and prev[2] and prev[2]%2 == 0:  # key-up
                    idx  = int((prev[2]+1)/2)
                    # print(f" <---- UP:{idx+1}", ecodes.KEY[sim_code])
                    print(f" <---- UP:{idx+1}", sim_code)
                    downs[event.code] = prev[:2] + (prev[2] +(1 if event.value == 0 else 0),)
                    # downs[event.code] = prev[:2] + (prev[2] +1,)
                    ui.write(ecodes.EV_KEY, sim_code, event.value)
                    ui.syn()
                    continue  # dont forward

            # forward event along
            ui.write(event.type, event.code, event.value)
            ui.syn()

    device.ungrab()
    ui.close()
except Exception as e:
    device.ungrab()
    ui.close()
    raise e


print("EXITING!")
exit(0)
# TODO: why no exit?
