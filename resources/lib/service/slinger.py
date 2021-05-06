from resources.lib.globals import *
from resources.lib.classes.auth import Auth

from resources.lib.service.guide import Guide
import threading

class Slinger(object):

    Channels_Updated = 0
    Guide_Updated = 0
    Shows_Updated = 0
    On_Demand_Updated = 0
    VOD_Updated = 0

    Seconds_Per_Hour = 60 * 60
    Channels_Interval = 24 * Seconds_Per_Hour  # One Week
    Guide_Interval = 12 * Seconds_Per_Hour  # Twelve Hours
    Shows_Interval = 168 * Seconds_Per_Hour  # One Week
    On_Demand_Interval = 168 * Seconds_Per_Hour  # One Week
    VOD_Interval = 12 * Seconds_Per_Hour  # Twelve Hours
    Guide_Days = 1
    EPG_Path = os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')), 'sling_epg.xml')
    Playlist_Path = os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('profile')), 'sling_playlist.m3u')

    Monitor = None
    Auth = None
    DB = None
    EndPoints = None
    
    First_Pass = True
    Force_Update = False
    Tasks = {}
    State = "Idle"
    Current_Job = ""
    Last_Update = ""
    Last_Error = ""

    Guide_Thread = None

    def __init__(self):
        global USER_SUBS, USER_DMA, USER_OFFSET
        log('Slinger Service:  __init__')

        self.Guide_Thread = threading.Thread(target=Guide)
        self.Guide_Thread.daemon = True
        self.Guide_Thread.start()

        self.Monitor = xbmc.Monitor()
        self.EndPoints = self.buildEndPoints()
        self.Auth = Auth()
        loggedIn, message = self.Auth.logIn(self.EndPoints, USER_EMAIL, USER_PASSWORD)
        log("__init__: logIn() ==> Success: " + str(loggedIn) + " | Message: " + message)
        if loggedIn:
            log("__init__: self.user Subscriptions URL => " + USER_INFO_URL)
            gotSubs, message = self.Auth.getUserSubscriptions()
            log("__init__: self.user Subscription Attempt, Success => " + str(gotSubs) + "Message => " + message)
            self.Auth.getAccessJWT(self.EndPoints)
            if gotSubs:
                USER_SUBS = message

                success, region = self.Auth.getRegionInfo()
                if not success:
                    log("__init__: Failed to get User Region Info, exiting.")
                    self.close()

                USER_DMA = region['USER_DMA']
                USER_OFFSET = region['USER_OFFSET']
            else:
                log("__init__: Failed to get User Subscriptions, exiting.")
                self.close()

        if not xbmcvfs.exists(TRACKER_PATH):
            self.updateTracker(state="Init", job="Creating tracker file")

        if not xbmcvfs.exists(DB_PATH):
            self.createDB()
        self.DB = sqlite3.connect(DB_PATH)

        if self.DB is not None:
            self.main()
        else:
            log('Slinger __init__: Failed to initialize DB, closing.')
            self.close()

    def main(self):
        log('Slinger Service: main()')
        
        self.checkLastUpdate()
        self.checkUpdateIntervals()
        if SETTINGS.getSetting('Enable_EPG') == 'true':
            self.pvrON()
            if GUIDE_ON_START:
                xbmc.executebuiltin("ActivateWindow(TVGuide)")

        while not self.Monitor.abortRequested():
            timestamp = int(time.time())

            if RUN_UPDATES:
                self.checkTracker()
                if (self.Channels_Updated + self.Channels_Interval) < timestamp:
                    if not self.inTasks("Update Channels")[0]:
                        log('Channels need updated')
                        self.Tasks[timestamp] = "Update Channels"
                if (self.Guide_Updated + self.Guide_Interval) < timestamp:
                    if not self.inTasks("Update Guide")[0]:
                        self.Tasks[timestamp + 1] = "Update Guide"
                if (self.On_Demand_Updated + self.On_Demand_Interval) < timestamp:
                    if not self.inTasks("Update On Demand")[0]:
                        self.Tasks[timestamp + 2] = "Update On Demand"
                if (self.Shows_Updated + self.Shows_Interval) < timestamp:
                    if not self.inTasks("Update Shows")[0]:
                        self.Tasks[timestamp + 3] = "Update Shows"
                if (self.VOD_Updated + self.VOD_Interval) < timestamp:
                    if not self.inTasks("Update VOD")[0]:
                        self.Tasks[timestamp + 4] = "Update VOD"
                self.updateTracker(state="Idle", job="")

                if len(self.Tasks):
                    self.doTasks()
            
            # Sleep for 30 minutes or exit on break
            count = 0
            abort = False
            while count < 30:
                self.updateTracker(state="Sleeping", job="Sleeping for 60 seconds")
                if self.Monitor.waitForAbort(60):
                    log("Shutting down slinger service...")
                    try:
                        requests.get('http://%s:9999/stop' % xbmc.getIPAddress())
                    except:
                        log('Guide Service has been shut down.')
                    abort = True
                    break
                
                self.checkTracker()
                if len(self.Tasks):
                    break

                self.updateTracker(state="Idle", job="")
                count += 1

            if abort:
                log('Slinger Service: Stopping...')
                break
            else:
                self.doTasks()

            self.checkLastUpdate()
            self.checkUpdateIntervals()

        self.close()

    def checkTracker(self):
        log('Slinger Service: checkTracker()')

        with open(TRACKER_PATH) as tracker_file:
            try:
                json_data = json.load(tracker_file)
                for key in json_data:
                    log('%s: %s' % (key, str(json_data[key])))
                    if key == "Tasks":
                        self.Tasks = {}
                        for task_id in json_data[key]:
                            self.Tasks[int(task_id)] = json_data[key][task_id]
                    if key == "State":
                        self.State = json_data[key]
                    if key == "Current_Job":
                        self.Current_Job = json_data[key]
                    if key == "Last_Update":
                        self.Last_Update = json_data[key]
                    if key == "Last_Error":
                        self.Last_Error = json_data[key]
            except:
                log('Slinger Service: tracker file read error. Recreating')
                self.updateTracker(state="Init", job="Creating tracker file")

        return

    def updateTracker(self, state, job):
        log('Slinger Service: updateTracker()')
        
        self.State = state
        self.Current_Job = job
        if self.First_Pass:
            self.Last_Error = ""
            self.First_Pass = False

        temp_json = {
            "Tasks": self.Tasks,
            "State": self.State,
            "Current_Job": self.Current_Job,
            "Last_Update": self.Last_Update,
            "Last_Error": self.Last_Error
        }
        log(str(temp_json))
        with open(TRACKER_PATH, 'w') as tracker_file:
            json.dump(temp_json, tracker_file, indent=4)

        return

    def inTasks(self, task):
        log('Slinger Service: inTasks()')
        found = False
        location = -1
        for id in self.Tasks:
            if self.Tasks[id] == task:
                found = True
                location = id

        return found, location

    def doTasks(self):
        log('Slinger Service: doTasks()')
        for id in sorted(self.Tasks.keys()):
            if id < 0:
                self.Force_Update = True
            if self.Tasks[id] == "Update Channels" and UPDATE_CHANNELS:
                self.updateTracker(state="Working", job="Updating Channels")
                self.updateChannels()
            if self.Tasks[id] == "Update Guide" and UPDATE_GUIDE:
                self.updateTracker(state="Working", job="Updating Guide")
                self.updateGuide()
            if self.Tasks[id] == "Update On Demand" and UPDATE_ON_DEMAND:
                self.updateTracker(state="Working", job="Updating On Demand")
                self.updateOnDemand()
            if self.Tasks[id] == "Update Shows" and UPDATE_SHOWS:
                self.updateTracker(state="Working", job="Updating Shows")
                self.updateShows()
            if self.Tasks[id] == "Update VOD" and UPDATE_VOD:
                self.updateTracker(state="Working", job="Updating VOD")
                self.updateVOD()

            self.Last_Update = self.Tasks[id]
            del self.Tasks[id]
            self.updateTracker(state="Idle", job="")
            self.Force_Update = False

        return

    def checkLastUpdate(self):
        log('Slinger Service: checkLastUpdate()')
        result = False  # Return False if something needs updated, else True

        query = "SELECT \
                (SELECT Last_Update FROM Channels WHERE Hidden = 0 ORDER BY Last_Update ASC LIMIT 1, 1) AS Channels_Last_Update, \
                (SELECT Last_Update FROM Guide ORDER BY Last_Update ASC LIMIT 1, 1) AS Guide_Last_Update, \
                (SELECT Last_Update FROM Shows ORDER BY Last_Update ASC LIMIT 1, 1) AS Shows_Last_Update, \
                (SELECT Last_Update FROM On_Demand_Folders ORDER BY Last_Update ASC LIMIT 1, 1) AS On_Demand_Last_Update, \
                (SELECT Last_Update FROM VOD_Assets ORDER BY Last_Update ASC LIMIT 1, 1) AS VOD_Last_Update"

        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            updates = cursor.fetchone()
            if updates is not None and len(updates) > 0:
                self.Channels_Updated = updates[0] if updates[0] is not None else 0
                self.Guide_Updated = updates[1] if updates[1] is not None else 0
                self.Shows_Updated = updates[2] if updates[2] is not None else 0
                self.On_Demand_Updated = updates[3] if updates[3] is not None else 0
                self.VOD_Updated = updates[4] if updates[4] is not None else 0

                log('checkLastUpdate(): Last Updates => Channels: %i | Guide: %i | Shows: %i | On Demand: %i | VOD: %i' %
                    (self.Channels_Updated, self.Guide_Updated, self.Shows_Updated, self.On_Demand_Updated,
                     self.VOD_Updated))

                result = True
        except sqlite3.Error as err:
            error = 'checkLastUpdate(): Failed to read Last Update times from DB, error => %s' % err
            log(error)
            self.Last_Error = error
        except Exception as exc:
            error = 'checkLastUpdate(): Failed to read Last Update times from DB, exception => %s' % exc
            log(error)
            self.Last_Error = error

        return result

    def checkUpdateIntervals(self):
        log('Slinger Service: checkUpdateIntervals()')

        self.Channels_Interval = int(SETTINGS.getSetting('Channels_Interval')) * 24 * self.Seconds_Per_Hour
        self.Guide_Interval = float(SETTINGS.getSetting('Guide_Interval')) * 24 * self.Seconds_Per_Hour
        self.Shows_Interval = int(SETTINGS.getSetting('Shows_Interval')) * 24 * self.Seconds_Per_Hour
        self.On_Demand_Interval = int(SETTINGS.getSetting('On_Demand_Interval')) * 24 * self.Seconds_Per_Hour
        self.VOD_Interval = int(SETTINGS.getSetting('Shows_Interval')) * 24 * self.Seconds_Per_Hour
        self.Guide_Days = int(SETTINGS.getSetting('Guide_Days'))

        log('checkUpdateIntervals(): Updated Intervals => Channels: %i | Guide: %i | Shows: %i | On Demand: %i | VOD: %i' %
            (self.Channels_Interval, self.Guide_Interval, self.Shows_Interval, self.On_Demand_Interval,
             self.VOD_Interval))

    def updateChannels(self):
        log('Slinger Service: updateChannels()')
        result = False
        channels = {}

        db_channels = {}
        try:
            db_query = "SELECT GUID, Hidden, Protected FROM Channels"
            cursor = self.DB.cursor()
            cursor.execute(db_query)
            db_data = cursor.fetchall()
            for channel in db_data:
                db_channels[channel[0]] = {
                    'Hidden': bool(channel[1]),
                    'Protected': bool(channel[2])
                }
        except sqlite3.Error as err:
            error = 'updateChannels(): Failed to retrieve channels from DB, error => %s' % err
            log(error)
            self.Last_Error = error
        except Exception as exc:
            error = 'updateChannels(): Failed to retrieve channels from DB, exception => %s' % exc
            log(error)
            self.Last_Error = error
        
        subs = binascii.b2a_base64(str.encode(LEGACY_SUBS.replace('+', ','))).decode().strip()
        channels_url = '%s/cms/publish3/domain/channels/v4/%s/%s/%s/1.json' % \
                       (self.EndPoints['cms_url'], USER_OFFSET, USER_DMA, subs)
        log('updateChannels()\r%s' % channels_url)
        response = requests.get(channels_url, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            response = response.json()
            if 'subscriptionpacks' in response:
                sub_packs = response['subscriptionpacks']
                for sub_pack in sub_packs:
                    if 'channels' in sub_pack:
                        channel_count = 0
                        if SHOW_PROGRESS:
                            progress = xbmcgui.DialogProgressBG()
                            progress.create('Sling TV')
                            progress.update(0, 'Downloading Channel Info...')
                        for channel in sub_pack['channels']:
                            if channel['channel_guid'] not in db_channels or not db_channels[channel['channel_guid']]['Hidden']:
                                channels[channel['channel_guid']] = Channel(channel['channel_guid'], self.EndPoints, self.DB, update=True)
                                channel_count += 1
                            else:
                                log('Skipping channel %s\r\n%s' % (channel['network_affiliate_name'], json.dumps(db_channels[channel['channel_guid']], indent=4)))
                                
                            if SHOW_PROGRESS:
                                progress.update(int((float(channel_count) / len(sub_pack['channels'])) * 100), 'Downloading Channel Info: %s' % channel['network_affiliate_name'])
                            if self.Monitor.abortRequested():
                                break
                        if SHOW_PROGRESS:
                            progress.close()
                        
                        try:
                            query = "SELECT GUID FROM Channels WHERE Protected = 1"
                            cursor = self.DB.cursor()
                            cursor.execute(query)
                            protected = cursor.fetchall()
                            for record in protected:
                                if record[0] not in channels:
                                    channels[record[0]] = Channel(record[0], self.EndPoints, self.DB, update=True)
                        except sqlite3.Error as err:
                            log('setSetting(): Failed retrieve protected records from DB, error => %s' % err)
                        except Exception as exc:
                            log('setSetting(): Failed retrieve protected records from DB, exception => %s' % exc)

        query = "SELECT GUID FROM Channels WHERE Hidden = 0 and Protected = 0"
        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            db_channels = cursor.fetchall()
            if db_channels is not None and len(db_channels) > 0:
                delete_query = ''
                for channel in db_channels:
                    guid = channel[0]
                    if guid not in channels:
                        temp_query = "DELETE FROM Channels WHERE GUID = '%s' AND Protected = 0" % guid
                        delete_query = '%s; %s' % (delete_query, temp_query) if delete_query != '' else temp_query
                        log('Channel %s not in Subscription package, will DELETE.' % guid)
                if delete_query != '':
                    try:
                        cursor.executescript(delete_query)
                        self.DB.commit()
                        result = True
                    except sqlite3.Error as err:
                        error = 'updateChannels(): Failed to delete extra channels from DB, error => %s' % err
                        log(error)
                        self.Last_Error = error
                    except Exception as exc:
                        error = 'updateChannels(): Failed to delete extra channels from DB, exception => %s' % exc
                        log(error)
                        self.Last_Error = error
                else:
                    result = True
        except sqlite3.Error as err:
            error = 'updateChannels(): Failed to read Last Update times from DB, error => %s' % err
            log(error)
            self.Last_Error = error
        except Exception as exc:
            error = 'updateChannels(): Failed to read Last Update times from DB, exception => %s' % exc
            log(error)
            self.Last_Error = error

        return result

    def updateGuide(self):
        log('Slinger Service: updateGuide()')
        result = False

        log('updateGuide(): Guide Days %i' % self.Guide_Days)
        for day in range(0, self.Guide_Days):  #Range is non-inclusive
            timestamp = timeStamp(datetime.date.today() + datetime.timedelta(days=day))
            url_timestamp = (datetime.date.today() + datetime.timedelta(days=day)).strftime("%y%m%d") + \
                            datetime.datetime.utcnow().strftime("%H%M")
            log('updateGuide(): Timestamp: %i | URL Timestamp %s' % (timestamp, url_timestamp))
            current_timestamp = int(time.time())
            log('Start Timestamp: %i | Interval: %i' % (current_timestamp, self.Seconds_Per_Hour*24))
            query = "SELECT GUID, Poster, Name FROM Channels WHERE Hidden = 0 ORDER BY Name ASC"
            try:
                cursor = self.DB.cursor()
                cursor.execute(query)
                channels = cursor.fetchall()
                if channels is not None and len(channels):
                    if SHOW_PROGRESS:
                        progress = xbmcgui.DialogProgressBG()
                        progress.create('Sling TV')
                        progress.update(0, 'Downloading Day %i Guide Info...' % (day + 1))
                    channel_count = 0

                    start_str = time.strftime("%m/%d/%Y") + " 00:00:00"
                    end_str = time.strftime("%m/%d/%Y ") + " 23:59:59"
                    start_ts = int(time.mktime(time.strptime(start_str, "%m/%d/%Y %H:%M:%S")))
                    end_ts = int(time.mktime(time.strptime(end_str, "%m/%d/%Y %H:%M:%S")))

                    session = createResilientSession()
                    for channel in channels:
                        channel_guid = channel[0]
                        channel_poster = channel[1]
                        channel_name = channel[2]
                        if SHOW_PROGRESS:
                            progress.update(int((float(channel_count) / len(channels)) * 100), 'Downloading Day %i Guide Info: %s' % (day + 1, channel_name))

                        query = "SELECT Stop AS Guide_TS FROM Guide Where Channel_GUID = '%s' Order By Stop ASC LIMIT 1, 1" % channel_guid
                        cursor.execute(query)
                        db_last_update = cursor.fetchone()
                        if db_last_update is not None and len(db_last_update):
                            first_ts = start_ts + (day * 24 * self.Seconds_Per_Hour)
                            last_ts = end_ts + (day * 24 * self.Seconds_Per_Hour)
                            guide_ts = int(db_last_update[0])
                        else:
                            first_ts = start_ts + (day * 24 * self.Seconds_Per_Hour)
                            last_ts = end_ts + (day * 24 * self.Seconds_Per_Hour)
                            guide_ts = 0

                        log('Channel: %s | Current Day: %i | First TS: %i | Last TS: %i | Guide TS: %i' % (channel_name, day, first_ts, last_ts, guide_ts))
                        if guide_ts < first_ts or (first_ts <= guide_ts <= last_ts) or self.Force_Update:
                            schedule_url = "%s/cms/publish3/channel/schedule/24/%s/1/%s.json" % \
                                           (self.EndPoints['cms_url'], url_timestamp, channel_guid)
                            log('updateGuide(): %s Schedule URL =>\r%s' % (channel_name, schedule_url))
                            response = session.get(schedule_url, headers=HEADERS, verify=VERIFY)
                            if response.status_code == 200:
                                channel_json = response.json()
                                if channel_json is not None:
                                    try:
                                        self.processSchedule(channel_guid, channel_poster, channel_json['schedule'], timestamp)
                                    except sqlite3.Error as err:
                                        error = 'updateGuide(): Failed to process schedule for channel %s, error => %s' % (channel_guid, err)
                                        log(error)
                                        self.Last_Error = error
                                    except Exception as exc:
                                        error = 'updateGuide(): Failed to process schedule for channel %s, exception => %s' % (channel_guid, exc)
                                        log(error)
                                        self.Last_Error = error
                        channel_count += 1
                        if self.Monitor.abortRequested():
                            break
                    session.close()
                    if SHOW_PROGRESS:
                        progress.close()
                result = True
            except sqlite3.Error as err:
                error = 'updateGuide(): Failed to retrieve channels from DB, error => %s' % err
                log(error)
                self.Last_Error = error
                result = False
                if SHOW_PROGRESS:
                    progress.close()
            except Exception as exc:
                error = 'updateGuide(): Failed to retrieve channels from DB, exception => %s' % exc
                log(error)
                self.Last_Error = error
                result = False
                if SHOW_PROGRESS:
                    progress.close()

        self.cleanGuide()

        if xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)') and SETTINGS.getSetting('Enable_EPG') == 'true':
            self.checkIPTV()
            if self.Force_Update:
                self.toggleIPTV()

        return result

    def processSchedule(self, channel_guid, channel_poster, json_data, timestamp):
        log('Slinger Service: processSchedule()')
        result = False
        schedule = {}

        log('processSchedule(): Retrieving channel %s guide from Sling for %i' %
            (channel_guid, timestamp))
        if 'scheduleList' in json_data:
            schedule_list = []
            for slot in json_data['scheduleList']:
                new_slot = {'Name': slot['title'] if 'title' in slot else '',
                            'Thumbnail': ICON,
                            'Poster': ICON,
                            'Rating': '',
                            'Genre': '',
                            'Start': int(slot['schedule_start'].split('.')[0]),
                            'Stop': int(slot['schedule_stop'].split('.')[0])}
                if 'thumbnail' in slot:
                    if slot['thumbnail'] is not None:
                        if 'url' in slot['thumbnail']:
                            new_slot['Thumbnail'] = slot['thumbnail']['url']
                if 'metadata' in slot:
                    metadata = slot['metadata']
                    ratings = ''
                    if 'ratings' in metadata:
                        for rating in metadata['ratings']:
                            ratings = '%s, %s' % (ratings, rating) if len(ratings) > 0 else rating
                    new_slot['Rating'] = ratings
                    description = ''
                    if 'episode_season' in metadata:
                        description = 'S%i' % int(metadata['episode_season'])
                    if 'episode_number' in metadata:
                        if len(description) == 0:
                            description = 'E%i' % int(metadata['episode_number'])
                        else:
                            description = '%sE%i ' % (description, int(metadata['episode_number']))
                    if 'episode_title' in description:
                        if len(description) == 0:
                            description = metadata['episode_title']
                        else:
                            description = '%s%s' % (description, metadata['episode_title'])
                    if 'description' in metadata:
                        description = '%s %s' % (description, metadata['description'])
                    new_slot['Description'] = description
                    genres = ''
                    if 'genre' in metadata:
                        for genre in metadata['genre']:
                            genres = '%s, %s' % (genres, genre) if len(genres) > 0 else genre
                    new_slot['Genre'] = genres
                if 'program' in slot:
                    program = slot['program']
                    if 'background_image' in program:
                        if program['background_image'] is not None:
                            new_slot['Poster'] = program['background_image']['url']
                    else:
                        new_slot['Poster'] = channel_poster

                new_slot['Name'] = new_slot['Name'].strip()
                new_slot['Description'] = new_slot['Description'].strip()
                new_slot['Genre'] = new_slot['Genre'].strip()
                new_slot['Rating'] = new_slot['Rating'].strip().replace('_', ' ')

                schedule[new_slot['Start']] = new_slot
                schedule_list.append(
                    (channel_guid, new_slot['Start'], new_slot['Stop'],
                     new_slot['Name'].replace("'", "''"), new_slot['Description'].replace("'", "''"),
                     new_slot['Thumbnail'], new_slot['Poster'], new_slot['Genre'],
                     new_slot['Rating'], int(time.time()))
                )

            if schedule_list:
                self.saveSlot(channel_guid, schedule_list)
                
        else:
            log('processSchedule(): scheduleList is empty, skipping.' )
        if len(schedule):
            result = True

        return result

    def saveSlot(self, channel_guid, schedule_list):
        log('Slinger Service: saveSlot()')
        
        log('saveSlot(): Saving guide info into DB for channel %s' % channel_guid)
        cursor = self.DB.cursor()

        try:
            slot_query = "REPLACE INTO Guide (Channel_GUID, Start, Stop, Name, Description, Thumbnail, Poster, " \
                         "Genre, Rating, Last_Update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            
            cursor.executemany(slot_query, schedule_list)
            self.DB.commit()
        except sqlite3.Error as err:
            error = 'saveSlot(): Failed to save guide information for channel %s to DB, error => %s' % (channel_guid, err)
            log(error)
            self.Last_Error = error
        except Exception as exc:
            error = 'saveSlot(): Failed to save guide information for channel %s to DB, exception => %s' % (channel_guid, exc)
            log(error)
            self.Last_Error = error

    def cleanGuide(self):
        log('Slinger Service: cleanGuide()')

        timestamp = int(time.time()) - (60 * 60 * 12)
        query = "DELETE FROM Guide WHERE Stop < %i" % timestamp
        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            self.DB.commit()
        except sqlite3.Error as err:
            error = 'saveSlot(): Failed to clean guide in DB, error => %s' % err
            log(error)
            self.Last_Error = error
        except Exception as exc:
            error = 'saveSlot(): Failed to clean guide in DB, exception => %s' % exc
            log(error)
            self.Last_Error = error

    def checkIPTV(self):
        log('Slinger Service: checkIPTV()')

        channels_url = 'http://%s:9999/channels.m3u' % xbmc.getIPAddress()
        guide_url = 'http://%s:9999/guide.xml' % xbmc.getIPAddress()

        if xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)'):
            iptv_settings = [['epgPathType', '1'],
                             ['epgTSOverride', 'true'],
                             ['epgUrl', guide_url],
                             ['epgCache', 'true'],
                             ['m3uPathType', '1'],
                             ['m3uUrl', channels_url],
                             ['m3uCache', 'true'],
                             ['logoFromEpg', '1'],
                             ['logoPathType', '1']
                             ]
            for id, value in iptv_settings:
                if xbmcaddon.Addon('pvr.iptvsimple').getSetting(id) != value:
                    xbmcaddon.Addon('pvr.iptvsimple').setSetting(id=id, value=value)

    def toggleIPTV(self):
        log('Slinger Service: toggleIPTV()')
        
        if not xbmc.getCondVisibility('System.HasAddon(pvr.iptvsimple)'):
            dialog = xbmcgui.Dialog()
            dialog.notification('Sling', 'Please enable PVR IPTV Simple Client', xbmcgui.NOTIFICATION_INFO, 5000, False)
        else:
            self.pvrOFF()
            self.pvrON()

    def pvrOFF(self):
        pvr_toggle_off = '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": ' \
                         '{"addonid": "pvr.iptvsimple", "enabled": false}, "id": 1}'
        xbmc.executeJSONRPC(pvr_toggle_off)

    def pvrON(self):
        pvr_toggle_on = '{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": ' \
                        '{"addonid": "pvr.iptvsimple", "enabled": true}, "id": 1}'
        xbmc.executeJSONRPC(pvr_toggle_on)

    def updateShows(self):
        log('Slinger Service: updateShows()')
        query = "SELECT * FROM Shows ORDER BY Name ASC"
        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            shows = cursor.fetchall()
            if shows is not None and len(shows):
                if SHOW_PROGRESS:
                    progress = xbmcgui.DialogProgressBG()
                    progress.create('Sling TV')
                    progress.update(0, 'Updating Shows...' )
                show_count = 0
                for show in shows:
                    show_guid = show[0]
                    show_name = show[1]
                    if SHOW_PROGRESS:
                        progress.update(int((float(show_count) / len(shows)) * 100), 'Updating Shows: %s' % show_name)
                    query = "SELECT Last_Update AS Updated FROM Seasons WHERE Seasons.Show_GUID = '%s' " \
                            "ORDER BY Last_Update ASC LIMIT 1" % show_guid
                    cursor.execute(query)
                    update_check = cursor.fetchone()
                    if update_check is not None:
                        if len(update_check) == 1:
                            check_timestamp = update_check[0]
                        else:
                            check_timestamp = 0
                    else:
                        check_timestamp = 0
                    timestamp = int(time.time()) - self.Shows_Interval
                    if check_timestamp < timestamp or self.Force_Update:
                        db_show = Show(show_guid, self.EndPoints, self.DB, silent=True)
                        if db_show.GUID != '':
                            db_show.getSeasons(update=True, silent=True)
                    show_count += 1
                    if self.Monitor.abortRequested():
                        break
                if SHOW_PROGRESS:
                    progress.close()
            result = True
        
        except sqlite3.Error as err:
            error = 'updateShows(): Failed to retrieve shows from DB, error => %s' % err
            log(error)
            self.Last_Error = error
            result = False
        except Exception as exc:
            error = 'updateShows(): Failed to retrieve shows from DB, exception => %s' % exc
            log(error)
            self.Last_Error = error
            result = False
        
        return result

    def updateOnDemand(self):
        log('Slinger Service: updateOnDemand()')
        timestamp = int(time.time())
        query = "SELECT GUID, Name FROM Channels WHERE Hidden = 0 AND On_Demand = 1 ORDER BY Name ASC"
        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            channels = cursor.fetchall()
            if channels is not None and len(channels):
                if SHOW_PROGRESS:
                    progress = xbmcgui.DialogProgressBG()
                    progress.create('Sling TV')
                    progress.update(0, 'Updating On Demand...' )
                channel_count = 0
                for channel in channels:
                    channel_guid = channel[0]
                    channel_name = channel[1]
                    if SHOW_PROGRESS:
                        progress.update(int((float(channel_count) / len(channels)) * 100), 'Updating On Demand: %s' % channel_name)
                    query = "SELECT Last_Update AS Updated FROM On_Demand_Folders Folders WHERE Folders.Channel_GUID = '%s' " \
                            "ORDER BY Last_Update ASC LIMIT 1" % channel_guid
                    cursor.execute(query)
                    update_check = cursor.fetchone()
                    if update_check is not None:
                        if len(update_check) == 1:
                            check_timestamp = update_check[0]
                        else:
                            check_timestamp = 0
                    else:
                        check_timestamp = 0
                    timestamp = int(time.time()) - self.On_Demand_Interval
                    if check_timestamp < timestamp:
                        db_channel = Channel(channel_guid, self.EndPoints, self.DB)
                        if db_channel.GUID != '':
                            categories = db_channel.getOnDemandCategories()
                            for category in categories:
                                db_channel.getOnDemandAssets(category['Name'], update=True)
                                if self.Monitor.abortRequested():
                                    break
                    channel_count += 1
                    if self.Monitor.abortRequested():
                        break

                query = "DELETE FROM On_Demand_Folders WHERE Expiration < %i" % timestamp
                cursor.execute(query)
                self.DB.commit()
                if SHOW_PROGRESS:
                    progress.close()
            result = True
        except sqlite3.Error as err:
            error = 'updateOnDemand(): Failed to retrieve On Demand Channels from DB, error => %s' % err
            log(error)
            self.Last_Error = error
            result = False
        except Exception as exc:
            error = 'updateOnDemand(): Failed to retrieve On Demand Channels from DB, exception => %s' % exc
            log(error)
            self.Last_Error = error
            result = False
        return result


    def updateVOD(self):
        log('Slinger Service: updateVOD()')
        timestamp = int(time.time())

        query = "DELETE FROM VOD_Assets WHERE Stop < %i" % timestamp
        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            self.DB.commit()
            result = True
        except sqlite3.Error as err:
            error = 'updateShows(): Failed to clean up VOD from DB, error => %s' % err
            log(error)
            self.Last_Error = error
            result = False
        except Exception as exc:
            error = 'updateShows(): Failed to clean up VOD from DB, exception => %s' % exc
            log(error)
            self.Last_Error = error
            result = False
        return result

    def createDB(self):
        log('Slinger Service: createDB()')
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
                error = 'createDB(): Failed to create DB tables, error => %s' % err
                log(error)
                self.Last_Error = error
            except Exception as exc:
                error = 'createDB(): Failed to create DB tables, exception => %s' % exc
                log(error)
                self.Last_Error = error
        db.close()

    def buildEndPoints(self):
        log('Slinger Service: buildEndPoints()\r%s' % WEB_ENDPOINTS)
        endpoints = {}
        response = requests.get(WEB_ENDPOINTS, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            endpoints = response.json()['environments']['production']

        return endpoints

    def close(self):
        log('Slinger Service: close()')
        self.DB.close()
        del self.Monitor
