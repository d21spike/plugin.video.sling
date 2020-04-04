import xbmcaddon, xbmc
from resources.lib.globals import *
from resources.lib.service.slinger import Slinger

if USE_SLINGER:
    if SETTINGS.getSetting('Enable_EPG') == 'true':
        pvr_toggle_off = '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": ' \
                         '{"addonid": "pvr.iptvsimple", "enabled": false}, "id": 1}'
        xbmc.executeJSONRPC(pvr_toggle_off)
        xbmc.sleep(1000)
        pvr_toggle_on = '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": ' \
                        '{"addonid": "pvr.iptvsimple", "enabled": true}, "id": 1}'
        xbmc.executeJSONRPC(pvr_toggle_on)
    Slinger()
