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
        self.DB = sqlite3.connect(DB_PATH)

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
        # loginURL = '%s/sling-api/oauth/authenticate-user' % self.endPoints['micro_ums_url']
        loggedIn, message = self.auth.logIn(self.endPoints, USER_EMAIL, USER_PASSWORD)
        log("Sling Class is logIn() ==> Success: " + str(loggedIn) + " | Message: " + message)
        if message != "Already logged in.":
            notificationDialog(message)
        if loggedIn:
            gotSubs, message = self.auth.getUserSubscriptions()
            self.auth.getAccessJWT(self.endPoints)
            if gotSubs:
                USER_SUBS = message
            log("self.user Subscription Attempt, Success => " + str(gotSubs) + " Message => " + message)
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
        if self.mode == 'tryRecord':
            self.tryRecord()
        if self.mode == 'record':
            self.setRecord()
        if self.mode == 'record_show':
            self.setRecordShow()
        if self.mode == 'del_record':
            self.delRecord()

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
                temp = Channel(sql, self.endPoints, self.DB)
                query = "UPDATE Channels SET Protected = 1 WHERE GUID = '%s'" % sql
                try:
                    cursor = self.DB.cursor()
                    cursor.execute(query)
                    self.DB.commit()
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
                cursor = self.DB.cursor()
                cursor.execute(query)
                self.DB.commit()
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
        
        log('%s | %s | %s' % (url, license_key, external_id))
        liz = xbmcgui.ListItem(name, path=url)
        
        protocol = 'mpd'
        drm = 'com.widevine.alpha'
        mime_type = 'application/dash+xml'

        if protocol in url:
            is_helper = inputstreamhelper.Helper(protocol, drm=drm)

            if not is_helper.check_inputstream():
                sys.exit()
            if KODI_VERSION_MAJOR >= 19:
                liz.setProperty('inputstream', is_helper.inputstream_addon)
            else:
                liz.setProperty('inputstreamaddon', is_helper.inputstream_addon)

            liz.setProperty('inputstream.adaptive.manifest_type', protocol)
            liz.setProperty('inputstream.adaptive.stream_headers', 'User-Agent=' + USER_AGENT)

            if license_key != '':
                liz.setProperty('inputstream.adaptive.license_type', drm)
                liz.setProperty('inputstream.adaptive.license_key', license_key)
            liz.setMimeType(mime_type)

            liz.setContentLookup(False)

        xbmcplugin.setResolvedUrl(int(self.sysARG[1]), True, liz)

        while not xbmc.Player().isPlayingVideo():
            xbmc.Monitor().waitForAbort(0.25)

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
                cursor = self.DB.cursor()
                cursor.executescript(query)
                cursor.execute('vacuum')
                self.DB.commit()
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
            cursor = self.DB.cursor()
            cursor.execute(query)
            self.DB.commit()
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
            cursor = self.DB.cursor()
            cursor.execute(query)
            self.DB.commit()
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
            cursor = self.DB.cursor()
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

    def tryRecord(self):
        log('tryRecord(): Attempting to get record asset for channel %s @ %s' % (self.params['channel'], self.params['start']))

        channel_guid = self.params['channel']
        rec_start = int(self.params['start'])
        url_timestamp = datetime.datetime.fromtimestamp(rec_start).strftime("%y%m%d") + datetime.datetime.fromtimestamp(rec_start).strftime("%H%M")
        schedule_url = "%s/cms/publish3/channel/schedule/24/%s/1/%s.json" % (self.endPoints['cms_url'], url_timestamp, channel_guid)
        log('tryRecord(): Schedule URL =>\r%s' % schedule_url)

        asset_found = False
        response = requests.get(schedule_url, headers=HEADERS, verify=VERIFY)
        if response.status_code == 200:
            channel_json = response.json()
            if channel_json is not None:
                if 'schedule' in channel_json:
                    schedule = channel_json['schedule']
                    if 'scheduleList' in schedule:
                        for program in schedule['scheduleList']:
                            if 'schedule_start' in program:
                                if str(rec_start) in program['schedule_start']:
                                    log('tryRecord: Found %s' % program['title'])
                                    if 'external_id' in program:
                                        asset_id = program['external_id']
                                        asset_url = '%s/cms/publish3/asset/info/%s.json' % (self.endPoints['cms_url'], asset_id)
                                        log('tryRecord: Found %s, URL: %s' % (program['title'], asset_url))        
                                        self.params['guid'] = channel_guid
                                        self.params['asset_url'] = asset_url
                                        self.setRecord()
                                        asset_found = True
                                    else:
                                        log('tryRecord: Failed to find asset in schedule')
                    else:
                        log('tryRecord: Failed to get schedule listing for channel')
                else:
                        log('tryRecord: Failed to get schedule for channel')
            else:
                log('tryRecord: Failed to get channel JSON')
        else:
            log('tryRecord: Failed to get channel information')

        if not asset_found:
            notificationDialog("Failed find asset to set recording")

    def setRecord(self):
        log('setRecord(): Attempting to record asset %s \nURL: %s' % (self.params['guid'], self.params['asset_url']))

        asset = self.params['guid']
        asset_url = self.params['asset_url']
        channel_guid = ''
        if asset is not None and asset_url is not None:
            if asset_url != '':
                response = requests.get(asset_url, headers=HEADERS, verify=VERIFY)
                if response is not None and response.status_code == 200:
                    response = response.json()
                    if 'schedules' in response:
                        for schedule in response['schedules']:
                            if 'channel_guid' in schedule:
                                temp_guid = schedule['channel_guid']
                                if subscribedChannel(self, temp_guid):
                                    channel_guid = temp_guid
                                    break
                        log('Asset channel guid: %s' % channel_guid)
                        if channel_guid == '' and len(response['schedules']) == 1:
                            if 'channel_guid' in response['schedules'][0]:
                                channel_guid = response['schedules'][0]['channel_guid']
                    if 'external_id' in response:
                        asset = response['external_id']
        message = ''
        if channel_guid != '':
            record_url = '%s/rec/v4/rec-create' % self.endPoints['cmwnext_url']
            payload = {
                "data": [
                    {
                        "external_id": asset,
                        "channel": channel_guid
                    }
                ],
                "product": "sling",
                "platform": "browser"
            }
            log ('Record URL: %s \nPayload: %s' % (record_url, json.dumps(payload, indent=4)))
            response = requests.post(record_url, data=json.dumps(payload), auth=self.auth.getAuth(), verify=VERIFY)
            response = response.json()
            log (json.dumps(response, indent=4))
            if 'error_code' in response:
                message = '%i - %s' % (response['error_code'], response['message'])
            elif 'error' in response:
                message = response['error']
            else:
                message = 'Recording set'
        else:
            message = "Failed to set recording"
        if message != '':
            notificationDialog(message)

    def setRecordShow(self):
        log('setRecordShow(): Attempting to record show %s, episodes: %s' % (self.params['guid'], self.params['type']))

        asset = self.params['guid']
        episode_type = self.params['type']
            
        message = ''
        if len(asset) > 0 and len(episode_type) > 0:
            record_url = '%s/rec/v4/rule-create' % self.endPoints['cmwnext_url']
            payload = {
                "data": [
                    {
                        "franchise": asset,
                        "mode": episode_type,
                        "type": "franchise"
                    }
                ],
                "product": "sling",
                "platform": "browser"
            }
            log ('Record URL: %s \nPayload: %s' % (record_url, json.dumps(payload, indent=4)))
            response = requests.post(record_url, data=json.dumps(payload), auth=self.auth.getAuth(), verify=VERIFY)
            response = response.json()
            log (json.dumps(response, indent=4))
            if 'error_code' in response:
                message = '%i - %s' % (response['error_code'], response['message'])
            elif 'error' in response:
                message = response['error']
            else:
                message = 'Recording set'
        else:
            message = "Failed to set recording"
        if message != '':
            notificationDialog(message)

    def delRecord(self):
        log('delRecord(): Attempting to delete recorded asset %s \nURL: %s' % (self.params['guid'], self.params['asset_url']))
        asset = self.params['guid']
        asset_url = self.params['asset_url']
        recording_type = ''
        recording_guid = ''
        
        recordings_url = '%s/rec/v4/user-recordings' % self.endPoints['cmwnext_url']
        payload = {
            "type": "recorded_by_name",
            "product": "sling",
            "platform": "browser"
        }
        log('Recordings URL: %s \nPayload: %s' % (recordings_url, json.dumps(payload, indent=4)))
        if asset is not None:
            response = requests.post(recordings_url, headers=HEADERS, data=json.dumps(payload), auth=self.auth.getAuth(), verify=VERIFY)
            log(response.text)
            if response is not None and response.status_code == 200:
                response = response.json()
                if 'ls_recordings' in response:
                    for recording in response['ls_recordings']:
                        if recording['external_id'] == asset or recording['_href'] == asset_url:
                            if 'recording_info' in recording:
                                if 'guid' in recording['recording_info']:
                                    recording_guid = recording['recording_info']['guid']
                                    recording_type = recording['recording_info']['type']
                                    break
                if 'rs_recordings' in response and recording_guid == '':
                    for recording in response['rs_recordings']:
                        if 'external_id' in recording:
                            if recording['external_id'] == asset or recording['_href'] == asset_url:
                                if 'recording_info' in recording:
                                    if 'guid' in recording['recording_info']:
                                        recording_guid = recording['recording_info']['guid']
                                        recording_type = recording['recording_info']['type']
                                        break
                if recording_guid == '':
                    recording_guid = asset
                    recording_type = 'rs'

        log('Recording Type: %s | GUID: %s' % (recording_type, recording_guid))
        if recording_type != '' and recording_guid != '':
            delete_url = '%s/rec/v1/rec-delete' % self.endPoints['cmwnext_url']
            payload = {
                "data": [
                    {
                        "type": recording_type,
                        "guid": recording_guid
                    }
                ],
                "product": "sling",
                "platform": "browser"
            }
            message = ''
            response = requests.post(delete_url, data=json.dumps(payload), auth=self.auth.getAuth(), verify=VERIFY)
            log(response.text)
            if response.text != '':
                response = response.json()
                log(json.dumps(response, indent=4))
                message = ''
                if 'error_code' in response:
                    message = '%i - %s' % (response['error_code'],
                                        response['message'])
                elif 'error' in response:
                    message = response['error']
            else:
                message = 'Recording deleted'

            if message != '':
                notificationDialog(message)
        else:
            notificationDialog('Failed to find selected recording for deletion')

