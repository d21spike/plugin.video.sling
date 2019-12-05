# You should have received a copy of the GNU General Public License
# along with Sling.TV.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-

from resources.lib.classes.auth import Auth
from resources.lib.menus.my_favorites import *
from resources.lib.menus.on_demand import *
from resources.lib.menus.shows import *
from resources.lib.menus.on_now import *
from resources.lib.menus.my_tv import *
from resources.lib.menus.search import *

class Sling(object):
    Channels = {}
    Favorites = {}
    Shows = {}

    def __init__(self, sysARG):
        global HANDLE_ID

        log('__init__')
        self.sysARG = sysARG
        HANDLE_ID = int(self.sysARG[1])
        log('Handle ID => %i' % HANDLE_ID)
        self.endPoints = self.buildEndPoints()
        self.handleID = int(self.sysARG[1])
        self.mode = None
        self.url = None
        self.params = None
        self.name = None
        self.auth = Auth()
        log('DB Exists => %s\r%s' % (str(xbmcvfs.exists(DB_PATH)), DB_PATH))
        if not xbmcvfs.exists(DB_PATH):
            self.createDB()
        self.db = sqlite3.connect(DB_PATH)

        self.getParams()

    def createDB(self):
        sql_file = xbmcvfs.File(SQL_PATH)
        sql = sql_file.read()
        sql_file.close()

        db = sqlite3.connect(DB_PATH)
        cursor = db.cursor()
        if sql != "":
            try:
                cursor.executescript(sql)
                db.commit()
            except sqlite3.Error as err:
                log('Failed to create DB tables, error => %s' % err, )
            except Exception as exc:
                log('Failed to create DB tables, exception => %s' % exc, )
        db.close()

    def run(self):
        global USER_SUBS, HANDLE_ID
        log('Addon %s entry...' % ADDON_NAME)

        self.checkDebug()
        loginURL = '%s/sling-api/oauth/authenticate-user' % self.endPoints['micro_ums_url']
        loggedIn, message = self.auth.logIn(loginURL, USER_EMAIL, USER_PASSWORD)
        log("Sling Class is logIn() ==> Success: " + str(loggedIn) + " | Message: " + message)
        if loggedIn:
            log("self.user Subscriptions URL => " + USER_INFO_URL)
            gotSubs, message = self.auth.getUserSubscriptions(USER_INFO_URL)
            self.auth.getAccessJWT(self.endPoints)
            if gotSubs:
                USER_SUBS = message
            log("self.user Subscription Attempt, Success => " + str(gotSubs) + "Message => " + message)
        else:
            sys.exit()

        if self.mode is None: self.buildMenu()
        if self.mode == "play": self.play()
        if self.mode == "channels": myChannels(self)
        if self.mode == "favorites": myFavorites(self)
        if self.mode == "show":
            if 'guid' not in self.params:
                myShows(self)
            else:
                if 'action' in self.params:
                    if self.params['action'] == 'favorite':
                        myShowsSetFavorite(self)
                        sys.exit()
                    elif self.params['action'] == 'unfavorite':
                        myShowsResetFavorite(self)
                        sys.exit()
                    elif self.params['action'] == 'update':
                        myShowsUpdate(self)
                        sys.exit()
                elif 'season' not in self.params:
                    myShowsSeasons(self)
                else:
                    myShowsEpisodes(self)
        if self.mode == "demand":
            if 'guid' not in self.params:
                onDemand(self)
            else:
                if 'action' in self.params:
                    if self.params['action'] == 'update':
                        onDemandUpdate(self)
                        sys.exit()
                else:
                    if 'category' not in self.params:
                        onDemandChannel(self)
                    else:
                        onDemandChannelCategory(self)
        if self.mode == 'on_now':
            if 'url' not in self.params:
                onNow(self)
            else:
                onNowRibbon(self)
        if self.mode == 'my_tv':
            if 'url' not in self.params:
                myTV(self)
            else:
                myTVRibbon(self)
        if self.mode == 'search':
            if 'query' not in self.params:
                search(self)
            else:
                executeSearch(self, self.params['query'])
        if self.mode == 'setting':
            self.setSetting()

        xbmcplugin.setContent(int(self.sysARG[1]), CONTENT_TYPE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(int(self.sysARG[1]), xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.endOfDirectory(int(self.sysARG[1]), updateListing=UPDATE_LISTING, cacheToDisc=CACHE)

    def checkDebug(self):
        global DEBUG_CODE
        DEBUG_CODE = SETTINGS.getSetting('Debug')

    def getParams(self):
        log('Retrieving parameters')

        self.params = dict(urlParse.parse_qsl(self.sysARG[2][1:]))
        if 'category' in self.params:
            self.params['category'] = binascii.unhexlify(self.params['category']).decode()
        try: self.url = urlLib.unquote(self.params['url'])
        except: pass
        try: self.name = urlLib.unquote_plus(self.params['name'])
        except: pass
        try: self.mode = self.params['mode']
        except: pass

        log('\rName: %s | Mode: %s\rURL: %s%s\rParams:\r%s' %
            (self.name, self.mode, self.sysARG[0], self.sysARG[2], json.dumps(self.params, indent=1)))

    def buildMenu(self):
        log('Building Menu')

        if self.mode is None:
            addDir(LANGUAGE(30100), self.handleID, '', mode='favorites')
            addDir(LANGUAGE(30101), self.handleID, '', mode='channels')
            addDir(LANGUAGE(30102), self.handleID, '', mode='demand')
            addDir(LANGUAGE(30103), self.handleID, '', mode='show')
            addDir(LANGUAGE(30104), self.handleID, '', mode='on_now')
            addDir(LANGUAGE(30105), self.handleID, '', mode='my_tv')
            addDir(LANGUAGE(30106), self.handleID, '', mode='search')

    def play(self):
        url = self.url
        name = self.name

        log('Playing stream %s' % name)

        try:
            url, license_key, external_id = self.auth.getPlaylist(url, self.endPoints)
        except:
            license_key = ''
            external_id = ''

        if 'mpd' in url:
            is_helper = inputstreamhelper.Helper('mpd', drm='widevine')
            if not is_helper.check_inputstream():
                sys.exit()
            liz = xbmcgui.ListItem(name, path=url)
            liz.setProperty('inputstreamaddon', 'inputstream.adaptive')
            liz.setProperty('inputstream.adaptive.manifest_type', 'mpd')
            liz.setProperty('inputstream.adaptive.stream_headers', 'User-Agent=' + USER_AGENT)
            if license_key != '':
                liz.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
                liz.setProperty('inputstream.adaptive.license_key', license_key)
            liz.setMimeType('application/dash+xml')
            liz.setContentLookup(False)
            xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)
        else:
            liz = xbmcgui.ListItem(name, path=url)
            xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)

        while not xbmc.Player().isPlayingVideo():
            xbmc.Monitor().waitForAbort(0.25)

        if xbmc.Player().isPlayingVideo() and len(xbmc.Player().getAvailableAudioStreams()) > 1:
            xbmc.Player().setAudioStream(0)

        if external_id != '':
            while xbmc.Player().isPlayingVideo() and not xbmc.Monitor().abortRequested():
                position = int(float(xbmc.Player().getTime()))
                duration = int(float(xbmc.Player().getTotalTime()))
                xbmc.Monitor().waitForAbort(3)

    def buildEndPoints(self):
        log('Building endPoints\r%s' % WEB_ENDPOINTS)
        endpoints = {}
        response = requests.get(WEB_ENDPOINTS, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            endpoints = response.json()['environments']['production']

        return endpoints

    def setSetting(self):
        log('Current setting %s value: %s' % (self.params['name'], SETTINGS.getSetting(self.params['name'])))

        if self.params['name'] != 'delete_db':
            log('Changing setting %s to value %s' % (self.params['name'], self.params['value']))
            SETTINGS.setSetting(self.params['name'], self.params['value'])
            log('New setting %s value: %s' % (self.params['name'], SETTINGS.getSetting(self.params['name'])))
        else:
            log('Deleting DB contents...')
            query = 'DELETE FROM Channels; ' \
                    'DELETE FROM Guide; ' \
                    'DELETE FROM On_Demand_Folders; ' \
                    'DELETE FROM On_Demand_Assets; ' \
                    'DELETE FROM VOD_Assets; ' \
                    'DELETE FROM Shows; ' \
                    'DELETE FROM Favorite_Shows; ' \
                    'DELETE FROM Seasons; ' \
                    'DELETE FROM Episodes;'
            try:
                cursor = self.db.cursor()
                cursor.executescript(query)
                cursor.execute('vacuum')
                self.db.commit()
            except sqlite3.Error as err:
                log('setSetting(): Failed to clear data from DB, error => %s' % err)
            except Exception as exc:
                log('setSetting(): Failed to clear data from DB, exception => %s' % exc)
