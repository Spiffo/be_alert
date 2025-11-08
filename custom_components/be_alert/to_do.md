TO DO / TO FIX:

# DONE: sensor.be_alert_all_ hangt onder zelfde hub als eerste sensor, eigen hub geven

# TODO: Vertaling wordt nog steeds niet netjes opgepikt

# DONE: sensor update moet kijken naar huidige lat long  van device / zone waarop gebaseerd is

# DONE: volgens mij worden maar een paar van de sensoren gerefreshed...

# TODO: Logo overal toevoegen

# DONE: set icon for sensor

# DONE: be alert sensor that is created, has lat long, so when I want to add a new device based sensor, it shows in that list. Options are to only show device tracker and persons, OR filter out be-alert from list

# DONOT: can an automation be added to the package? or do I provide it in the documentation as an example?

# DONE: add a service to the integration: it shoud be something to update all created sensors (all, device based and zone based).

# DONE:  have the polling interval in minutes configurable in the config flow but with minimum (and default) of 5 minutes

# DONE: zone or device alerts should be boolean sensors: alerting or not alerting

# TODO: before you call the webservice, check if there are any sensors or binary sensors that exist under this integration

# DONE: check if unloading a sensor actually happens

# TODO: Can you help me create a `hacs.json` file for this integration?

# TODO: deleting sensors does not delete device