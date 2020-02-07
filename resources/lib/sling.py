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
                    elif self.params['action'] == 'play':
                        self.playEpisode()
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

        xbmc.executebuiltin('Container.SetSortMethod(1)')

    def checkDebug(self):
        global DEBUG_CODE
        DEBUG_CODE = SETTINGS.getSetting('Debug')

        debug = dict(urlParse.parse_qsl(DEBUG_CODE))
        if 'sql_add' in debug:
            sql_array = debug['sql_add'].split(',')
            for sql in sql_array:
                temp = Channel(sql, self.endPoints, self.db)
                query = "UPDATE Channels SET Protected = 1 WHERE GUID = '%s'" % sql
                try:
                    cursor = self.db.cursor()
                    cursor.execute(query)
                    self.db.commit()
                except sqlite3.Error as err:
                    log('setSetting(): Failed execute sql_add for %s in DB, error => %s' % (sql, err))
                except Exception as exc:
                    log('setSetting(): Failed execute sql_add for %s in DB, exception => %s' % (sql, exc))
        if 'sql_del' in debug:
            temp_list = ''
            if ',' in debug['sql_del']:
                sql_array = debug['sql_del'].split(',')
                for sql in sql_array:
                    temp_list += "'%s'" % sql if temp_list == '' else ",'%s'" % sql
            else:
                temp_list = "'%s'" % debug['sql_del']
            
            query = "DELETE FROM Channels WHERE GUID IN (%s)" % temp_list
            try:
                cursor = self.db.cursor()
                cursor.execute(query)
                self.db.commit()
            except sqlite3.Error as err:
                log('setSetting(): Failed execute sql_del for %s in DB, error => %s' % (temp_list, err))
            except Exception as exc:
                log('setSetting(): Failed execute sql_del for %s in DB, exception => %s' % (temp_list, exc))
        new_debug = ''
        for key in debug:
            new_debug += '&%s=%s' % (key, debug[key]) if key not in ('sql_add', 'sql_del') else ''
        new_debug = new_debug[1:]
        DEBUG_CODE = new_debug
        SETTINGS.setSetting('Debug', DEBUG_CODE)

        return

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
            play_back_started = time.time()
            while xbmc.Player().isPlayingVideo() and not xbmc.Monitor().abortRequested():
                position = int(float(xbmc.Player().getTime()))
                duration = int(float(xbmc.Player().getTotalTime()))
                xbmc.Monitor().waitForAbort(3)

            if int(time.time() - play_back_started) > 45:
                self.setResume(external_id, position, duration)

    def setResume(self, external_id, position, duration):
        # If there's only 2 min left delete the resume point
        if duration - position < 120:
            url = '%s/resumes/v4/resumes/%s' % (self.endPoints['cmwnext_url'], str(external_id))
            payload = '{"platform":"browser","product":"sling"}'
            requests.delete(url, headers=HEADERS, data=payload, auth=self.auth.getAuth(), verify=VERIFY)
        else:
            url = '%s/resumes/v4/resumes' % (self.endPoints['cmwnext_url'])
            payload = '{"external_id":"' + str(external_id) + '","position":' + str(position) + ',"duration":' + str(
                duration) + ',"resume_type":"fod","platform":"browser","product":"sling"}'
            requests.put(url, headers=HEADERS, data=payload, auth=self.auth.getAuth(), verify=VERIFY)

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

            if self.params['name'] == 'update_channels' and self.params['value'] == 'true':
                self.setUpdate('Update Channels')
            if self.params['name'] == 'update_guide' and self.params['value'] == 'true':
                self.setUpdate('Update Guide')
            if self.params['name'] == 'update_on_demand' and self.params['value'] == 'true':
                self.setUpdate('Update On Demand')
            if self.params['name'] == 'update_shows' and self.params['value'] == 'true':
                self.setUpdate('Update Shows')
            if self.params['name'] == 'update_vod' and self.params['value'] == 'true':
                self.setUpdate('Update VOD')
            if self.params['name'] == 'hide_channel' and self.params['value'] != '':
                self.hideChannel(self.params['value'])
            if self.params['name'] == 'reset_hidden' and self.params['value'] == 'true':
                self.hiddenReset()
            if self.params['name'] == 'view_slinger' and self.params['value'] == 'true':
                self.viewSlinger()
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

    def setUpdate(self, update):
        if not xbmcvfs.exists(TRACKER_PATH):
            temp_json = {
                "Tasks": {},
                "State": "",
                "Current_Job": "",
                "Last_Update": "",
                "Last_Error": ""
            }
            with open(TRACKER_PATH, 'w') as tracker_file:
                json.dump(temp_json, tracker_file, indent=4)

        with open(TRACKER_PATH) as tracker_file:
            task = update

            json_data = json.load(tracker_file)
            if 'Tasks' in json_data:
                tasks = json_data['Tasks']
            if 'State' in json_data:
                state = json_data['State']
            if 'Current_Job' in json_data:
                current_job = json_data['Current_Job']
            if 'Last_Update' in json_data:
                last_update = json_data['Last_Update']
            if 'Last_Error' in json_data:
                last_error = json_data['Last_Error']

            location = -1
            for id in tasks:
                if tasks[id] == task:
                    location = int(id)
            
            if location != -1:
                del tasks[str(location)]
            location = -1 * int(time.time())
            tasks[location] = task

            temp_json = {
                "Tasks": tasks,
                "State": state,
                "Current_Job": current_job,
                "Last_Update": last_update,
                "Last_Error": last_error
            }
            with open(TRACKER_PATH, 'w') as tracker_file:
                json.dump(temp_json, tracker_file, indent=4)

        return

    def hideChannel(self, channel_guid):
        log('Hiding channel %s...' % channel_guid)
        query = "UPDATE Channels SET Hidden = 1 WHERE GUID = '%s'" % channel_guid
        try:
            cursor = self.db.cursor()
            cursor.execute(query)
            self.db.commit()
            notificationDialog(LANGUAGE(30142))
        except sqlite3.Error as err:
            log('setSetting(): Failed to hide channel %s in DB, error => %s' % (channel_guid, err))
        except Exception as exc:
            log('setSetting(): Failed to hide channel %s in DB, exception => %s' % (channel_guid, exc))
        
        return

    def hiddenReset(self):
        log('Resetting hidden channels...')
        query = "UPDATE Channels SET Hidden = 0"
        try:
            cursor = self.db.cursor()
            cursor.execute(query)
            self.db.commit()
            notificationDialog(LANGUAGE(30144))
        except sqlite3.Error as err:
            log('setSetting(): Failed to reset hidden channels in DB, error => %s' % err)
        except Exception as exc:
            log('setSetting(): Failed to reset hidden channels in DB, exception => %s' % exc)

        return

    def viewSlinger(self):
        log('viewSlinger(): Displaying Slinger.json file')

        window_id = 10147 #Kodi textviewer window id
        label = 1
        textbox = 5

        json_data = {}
        with open(TRACKER_PATH) as tracker_file:
            json_data = json.load(tracker_file)

        xbmc.executebuiltin("ActivateWindow({})".format(window_id))
        window = xbmcgui.Window(window_id)
        window.show()
        window.getControl(label).setLabel(LANGUAGE(30146))
        window.getControl(textbox).setText(json.dumps(json_data, indent=4))

    def playEpisode(self):
        guid = self.params['guid']
        log('playEpisode() attempting to play %s' % guid)

        query = "SELECT Name, Playlist_URL FROM Episodes WHERE GUID = '%s'" % guid
        try:
            cursor = self.db.cursor()
            cursor.execute(query)
            episode = cursor.fetchone()
            if episode is not None:
                episode_name = episode[0]
                episode_url = episode[1]

                self.name = episode_name
                self.url = episode_url
                self.play()
        except sqlite3.Error as err:
            log('playEpisode(): Failed to play episode %s from DB, error => %s' % (guid, err))
        except Exception as exc:
            log('playEpisode(): Failed to play episode %s from DB, exception => %s' % (guid, exc))
