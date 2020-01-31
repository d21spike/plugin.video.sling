import xbmcaddon
from resources.lib.service.slinger import Slinger

if xbmcaddon.Addon().getSetting(id='Use_Slinger') == 'true':
    Slinger()
