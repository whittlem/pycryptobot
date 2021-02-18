import json

try:
    with open('config.json') as config_file:
        config = json.load(config_file)

        print (config)
except IOError:
    print ('Unable to open config.json')
    pass