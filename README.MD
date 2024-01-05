 # Switch Inventory 
    This script has 2 Functions it inventories cisco switch stacks and also list ports that have not been used in X number of days


# setup
    1. install Python https://www.python.org/downloads/ 
    2. run "pip install requirements.txt
    3. Frist create a file named list.json (see below)


# list.json examples
    You can add all your devices in the file in this format.


    [
        {
            "ip": "192.168.1.1",
            "Shutdown": 1,
            "disabletime": 2592000, 
            "enabled": true
        },
        {
            "ip": "192.168.1.0",
            "Shutdown": 1,
            "disabletime": 2592000, 
            "enabled": true
        }
    ]

# key map for the list.json file
    ip=<ip address of the device>
    shutdown  = this has 3 options
            1 = Create a list of ports that can be disabled.
            2 = update the description on the port with a "!" for the ports that can be disabled (also does option 1)
            3 = disable the port (also does option 1 and 2)
    disabletime = this is the time a port must be inactive before it is shutdown. The time is in seconds
    enable = True or False (The device must be enable for the script to check it)