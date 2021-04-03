## GLOBALS ##

import base64, calendar, datetime, hashlib, inputstreamhelper, json, os, random, requests, sys, time, pytz, re
import traceback, urllib, xmltodict, string, sqlite3, binascii
from pytz import timezone
from kodi_six import xbmc, xbmcvfs, xbmcplugin, xbmcgui, xbmcaddon
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

if sys.version_info[0] < 3:
    PY = 2
    import urlparse
    urlLib = urllib
    urlParse = urlparse
else:
    PY = 3
    urlLib = urllib.parse
    urlParse = urlLib

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass

ADDON_NAME = 'Sling'
ADDON_ID = 'plugin.video.sling'
ADDON_URL = 'plugin://plugin.video.sling/'
SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
SETTINGS_LOC = SETTINGS.getAddonInfo('profile')
ADDON_PATH = SETTINGS.getAddonInfo('path')
DB_PATH = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'sling.db'))
SQL_PATH = xbmc.translatePath(os.path.join(ADDON_PATH, 'resources', 'lib', 'tables.sql'))
UPDATE_PATH = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'update.now'))
ADDON_VERSION = SETTINGS.getAddonInfo('version')
ICON = SETTINGS.getAddonInfo('icon')
FANART = SETTINGS.getAddonInfo('fanart')
LANGUAGE = SETTINGS.getLocalizedString

TIMEOUT = 15
USER_EMAIL = SETTINGS.getSetting('User_Email')
USER_PASSWORD = SETTINGS.getSetting('User_Password')
USE_SLINGER = SETTINGS.getSetting(id='Use_Slinger') == 'true'
FIX_LIVE = SETTINGS.getSetting(id='Fix_Live') == 'true'
RUN_UPDATES = SETTINGS.getSetting(id='Run_Updates') == 'true'
ACCESS_TOKEN = SETTINGS.getSetting('access_token')
ACCESS_TOKEN_JWT = SETTINGS.getSetting('access_token_jwt')
SUBSCRIBER_ID = SETTINGS.getSetting('subscriber_id')
DEVICE_ID = SETTINGS.getSetting('device_id')
USER_SUBS = SETTINGS.getSetting('user_subs')
LEGACY_SUBS = SETTINGS.getSetting('legacy_subs')
USER_DMA = SETTINGS.getSetting('user_dma')
USER_OFFSET = SETTINGS.getSetting('user_offset')
USER_ZIP = SETTINGS.getSetting('user_zip')
GUIDE_ON_START = SETTINGS.getSetting('start_guide') == 'true' and USE_SLINGER

CACHE = False
PLUGIN_CACHE = None
UPDATE_LISTING = False
DEBUG = SETTINGS.getSetting('Enable_Debugging') == 'true'
DEBUG_CODE = SETTINGS.getSetting('Debug')

ANDROID_USER_AGENT = 'SlingTV/6.17.9 (Linux;Android 10) ExoPlayerLib/2.7.1'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/69.0.3497.100 Safari/537.36'

HEADERS = {'Accept': '*/*',
           'Origin': 'https://www.sling.com',
           'User-Agent': USER_AGENT,
           'Content-Type': 'application/json;charset=UTF-8',
           'Referer': 'https://www.sling.com',
           'Accept-Encoding': 'gzip, deflate, br',
           'Accept-Language': 'en-US,en;q=0.9'}
BASE_URL = 'https://watch.sling.com'
BASE_API = 'https://ums.p.sling.com'
BASE_WEB = 'https://webapp.movetv.com'
BASE_GEO = 'https://p-geo.movetv.com/geo?subscriber_id={}&device_id={}'
MAIN_URL = '%s/config/android/sling/menu_tabs.json' % BASE_WEB
USER_INFO_URL = '%s/v2/user.json' % BASE_API
WEB_ENDPOINTS = '%s/config/env-list/browser-sling.json' % (BASE_WEB)
MYTV = '%s/config/shared/pages/mytv.json' % (BASE_WEB)
CONFIG = '%s/config/browser/sling/config.json' % (BASE_WEB)
VERIFY = True
PRINTABLE = set(string.printable)
CONTENT_TYPE = 'Episodes'

TRACKER_PATH = xbmc.translatePath(os.path.join(SETTINGS_LOC, 'slinger.json'))


def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    if PY == 3:
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '- ' + msg, level)
    else:
        try:
            xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '- ' + msg, level)
        except:
            xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '- ' + strip(msg), level)


def inputDialog(heading=ADDON_NAME, default='', key=xbmcgui.INPUT_ALPHANUM, opt=0, close=0):
    retval = xbmcgui.Dialog().input(heading, default, key, opt, close)
    if len(retval) > 0: return retval


def okDialog(str1, str2='', str3='', header=ADDON_NAME):
    xbmcgui.Dialog().ok(header, str1, str2, str3)


def yesNoDialog(str1, header=ADDON_NAME, yes='', no='', autoclose=0):
    return xbmcgui.Dialog().yesno(header, str1, no, yes, autoclose)


def notificationDialog(message, header=ADDON_NAME, sound=False, time=1000, icon=ICON):
    try:
        xbmcgui.Dialog().notification(header, message, icon, time, sound)
    except:
        xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))


def loadJSON(string1):
    try:
        return json.loads(string1)
    except Exception as e:
        log("loadJSON Failed! " + str(e), xbmc.LOGERROR)
        return {}


def dumpJSON(string1):
    try:
        return json.dumps(string1)
    except Exception as e:
        log("dumpJSON Failed! " + str(e), xbmc.LOGERROR)
        return ''


def stringToDate(string, date_format):
    if "." in string:
        string = string[0:string.index(".")]
    try:
        return datetime.datetime.strptime(str(string), date_format)
    except TypeError:
        return datetime.datetime(*(time.strptime(str(string), date_format)[0:6]))


def sortGroup(str):
    arr = str.split(',')
    arr = sorted(arr)
    return ','.join(arr)


def utcToLocal(utc_dt):
    # get integer timestamp to avoid precision lost
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)


def strip(str):
    return "".join(list(filter(lambda x: x in PRINTABLE, str)))


def addDir(name, handleID, url, mode, info=None, art=None, menu=None):
    global CONTENT_TYPE, ADDON_URL
    log('Adding directory %s' % name)
    directory = xbmcgui.ListItem(name)
    directory.setProperty('IsPlayable', 'false')
    if info is None: directory.setInfo(type='Video', infoLabels={'mediatype': 'videos', 'title': name})
    else:
        if 'mediatype' in info: CONTENT_TYPE = '%ss' % info['mediatype']
        directory.setInfo(type='Video', infoLabels=info)
    if art is None: directory.setArt({'thumb': ICON, 'fanart': FANART})
    else: directory.setArt(art)

    if menu is not None:
        directory.addContextMenuItems(menu)

    try:
        name = urlLib.quote_plus(name)
    except:
        name = urlLib.quote_plus(strip(name))
    if url != '':
        url = ('%s?url=%s&mode=%s&name=%s' % (ADDON_URL, urlLib.quote_plus(url), mode, name))
    else:
        url = ('%s?mode=%s&name=%s' % (ADDON_URL, mode, name))
    log('Directory %s URL: %s' % (name, url))
    xbmcplugin.addDirectoryItem(handle=handleID, url=url, listitem=directory, isFolder=True)
    xbmcplugin.addSortMethod(handle=handleID, sortMethod=xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)


def addLink(name, handleID,  url, mode, info=None, art=None, total=0, contextMenu=None, properties=None):
    global CONTENT_TYPE, ADDON_URL
    log('Adding link %s' % name)
    link = xbmcgui.ListItem(name)
    if mode == 'info': link.setProperty('IsPlayable', 'false')
    else: link.setProperty('IsPlayable', 'true')
    if info is None: link.setInfo(type='Video', infoLabels={'mediatype': 'video', 'title': name})
    else:
        if 'mediatype' in info: CONTENT_TYPE = '%ss' % info['mediatype']
        link.setInfo(type='Video', infoLabels=info)
    if art is None: link.setArt({'thumb': ICON, 'fanart': FANART})
    else: link.setArt(art)
    if contextMenu is not None: link.addContextMenuItems(contextMenu)
    if properties is not None:
        log('Adding Properties: %s' % str(properties))
        for key, value in properties.items():
            link.setProperty(key, str(value))
    try:
        name = urlLib.quote_plus(name)
    except:
        name = urlLib.quote_plus(strip(name))
    if url != '':
        url = ('%s?url=%s&mode=%s&name=%s' % (
            ADDON_URL, urlLib.quote_plus(url), mode, name))
    else:
        url = ('%s?mode=%s&name=%s' % (ADDON_URL, mode, name))
    xbmcplugin.addDirectoryItem(handle=handleID, url=url, listitem=link, totalItems=total)
    xbmcplugin.addSortMethod(handle=handleID, sortMethod=xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)


def timeStamp(date):
    return calendar.timegm(date.timetuple())


def subscribedChannel(self, channel_guid):
    subscribed = False
    cursor = self.DB.cursor()
    query = "SELECT Name FROM Channels WHERE GUID = '%s'" % channel_guid
    cursor.execute(query)
    channel = cursor.fetchone()
    if channel is not None:
        subscribed = True

    return subscribed


def createResilientSession():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session

from resources.lib.classes.channel import Channel
from resources.lib.classes.show import Show
