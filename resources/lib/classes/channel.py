from resources.lib.globals import *

class Channel(object):

    Name = ''
    Call_Sign = ''
    ID = -1
    GUID = ''
    On_Now = {}
    Thumbnail = ICON
    Poster = FANART
    Language = ''
    Genre = ''
    Offered = True
    Qvt_Url = ''
    On_Demand = -1
    Hidden = False
    Protected = False

    Endpoints = None
    DB = None

    def __init__(self, channel_guid, endpoints=None, db=None, update=False):
        log('Channel initialization')

        self.Endpoints = endpoints
        self.DB = db

        found, db_channel = self.getDBChannel(channel_guid)
        if found and not update:
            self.Name = db_channel['Name']
            self.Call_Sign = db_channel['Call_Sign']
            self.ID = db_channel['ID']
            self.GUID = db_channel['GUID']
            self.On_Now = db_channel['On_Now']
            self.Thumbnail = db_channel['Thumbnail']
            self.Poster = db_channel['Poster']
            self.Language = db_channel['Language']
            self.Genre = db_channel['Genre']
            self.Offered = bool(db_channel['Offered'])
            self.Qvt_Url = db_channel['Qvt_Url']
            self.On_Demand = bool(db_channel['On_Demand'])
            self.Hidden = bool(db_channel['Hidden'])
            self.Protected = bool(db_channel['Protected'])

            log('Added DB channel => \r%s' % json.dumps(self.channelInfo(), indent=4))
        else:
            url_timestamp = datetime.date.today().strftime("%y%m%d") + datetime.datetime.utcnow().strftime("%H%M")
            channel_url = "%s/cms/publish3/channel/schedule/24/%s/1/%s.json" % (self.Endpoints['cms_url'],
                                                                                url_timestamp, channel_guid)
            response = requests.get(channel_url, headers=HEADERS, verify=VERIFY)
            log(channel_url)
            if response is not None and response.status_code == 200:
                channel_json = response.json()
                if channel_json is not None:
                    if 'channel_guid' in channel_json['schedule']:
                        self.processJSON(channel_json['schedule'])
                        log('Added channel => \r%s' % json.dumps(self.channelInfo(), indent=4))
                        result, onNow = self.onNow(response_json=channel_json)
                        if result: self.On_Now = onNow
                        log('Added channel %s On Now => \r%s' % (self.Name, json.dumps(self.On_Now, indent=4)))

    def processJSON(self, channel_json):
        log('Processing channel json')

        self.Name = channel_json['network_affiliate_name'] if 'network_affiliate_name' in channel_json else ''
        self.Call_Sign = channel_json['title'] if 'title' in channel_json else ''
        self.ID = int(channel_json['id']) if 'id' in channel_json else -1
        self.GUID = channel_json['channel_guid'] if 'channel_guid' in channel_json else ''
        if len(self.GUID) == 0:
            self.GUID = channel_json['guid'] if 'guid' in channel_json else ''
        if 'thumbnail' in channel_json:
            self.Thumbnail = channel_json['thumbnail']['url'] if 'url' in channel_json['thumbnail'] else ICON
        self.Qvt_Url = channel_json['qvt_url'] if 'qvt_url' in channel_json else ''
        if len(self.Qvt_Url) == 0:
            self.Qvt_Url = channel_json['qvt'] if 'qvt' in channel_json else ''
        self.Offered = bool(channel_json['offered']) if 'offered' in channel_json else True
        self.Call_Sign = channel_json['call_sign'] if 'call_sign' in channel_json else ''

        if 'metadata' in channel_json:
            metadata = channel_json['metadata']
            self.Name = metadata['channel_name'] if 'channel_name' in metadata else self.Name
            self.Call_Sign = metadata['call_sign'] if 'call_sign' in metadata else self.Call_Sign
            if 'genre' in metadata:
                genres = ''
                for genre in metadata['genre']:
                    genres = '%s, %s' % (genres, genre) if len(genres) > 0 else genre
                self.Genre = genres
            # self.Poster = metadata['default_schedule_image']['url'] if 'default_schedule_image' in metadata else self.Poster
            if 'default_schedule_image' in metadata:
                if metadata['default_schedule_image'] is not None:
                    if 'url' in metadata['default_schedule_image']:
                        self.Poster = metadata['default_schedule_image']['url'] 
            self.Language = metadata['language'] if 'language' in metadata else ''
        if self.Poster == FANART and 'default_schedule_image' in channel_json:
            self.Poster = channel_json['default_schedule_image']['url'] if channel_json['default_schedule_image'] is not None else self.Poster
        if len(self.Language) == 0:
            self.Language = channel_json['language'] if 'language' in channel_json else ''

        self.Name = self.Name.strip()
        self.Genre = self.Genre.strip()
        self.Language = self.Language.strip()
        self.On_Demand = self.onDemand()

        self.saveChannel()

        return

    def infoLabels(self):
        duration = 0
        plot = ''

        if len(self.On_Now) > 0:
            start = datetime.datetime.fromtimestamp(self.On_Now['Start']).strftime('%m/%d/%Y %H:%M:%S')
            stop = datetime.datetime.fromtimestamp(self.On_Now['Stop']).strftime('%m/%d/%Y %H:%M:%S')
            timestamp = int(time.time())
            if timestamp < self.On_Now['Stop']:
                duration = self.On_Now['Stop'] - self.On_Now['Start']
            if self.On_Now['Name'].strip() != self.On_Now['Description'].strip():
                plot = '[B]%s[/B][CR][CR]%s[CR][CR]Start: %s[CR]Stop: %s' % (
                    self.On_Now['Name'], self.On_Now['Description'], start, stop)
            else:
                plot = self.On_Now['Name']
        return {
            'title': self.Name,
            'plot': plot,
            'genre': self.On_Now['Genre'] if 'Genre' in self.On_Now else self.Genre,
            'duration': duration,
            'mediatype': 'Video',
            'mpaa': self.On_Now['Rating'] if 'Rating' in self.On_Now else ''
        }

    def infoArt(self):
        return {
            'thumb': self.Thumbnail,
            'logo': self.Thumbnail,
            'clearlogo': self.Thumbnail,
            'poster': self.Thumbnail,
            'fanart': self.Poster
        }

    def channelInfo(self):
        return {
            'Name': self.Name,
            'Call_Sign': self.Call_Sign,
            'ID': self.ID,
            'GUID': self.GUID,
            'On_Now': self.On_Now,
            'Thumbnail': self.Thumbnail,
            'Poster': self.Poster,
            'Language': self.Language,
            'Genre': self.Genre,
            'Offered': self.Offered,
            'Qvt_Url': self.Qvt_Url,
            'On_Demand': self.On_Demand
        }

    def onNow(self, response_json=None, session=None):
        # http://cbd46b77.cdn.cms.movetv.com/cms/publish3/channel/current_asset/ca0cad8dbb4a4e68962810d8a6aa8b6a.json
        # https://cbd46b77.cdn.cms.movetv.com/cms/publish3/channel/schedule/2ad976f9aa4b4796a52ae3d64b50db9c.json

        result = False
        on_now = {}
        schedule = {}

        timestamp = int(time.time())
        found, db_on_now = self.getDBGuide(timestamp)
        if found:
            on_now = db_on_now
            result = True
        else:
            log('Retrieving channel %s guide from Sling' % self.Name)
            if response_json is None and self.Endpoints is not None:
                url_timestamp = datetime.date.today().strftime("%y%m%d") + datetime.datetime.utcnow().strftime("%H%M")
                channel_url = "%s/cms/publish3/channel/schedule/24/%s/1/%s.json" % (self.Endpoints['cms_url'],
                                                                                    url_timestamp, self.GUID)
                if session is None:
                    response = requests.get(channel_url, headers=HEADERS, verify=VERIFY)
                else:
                    response = session.get(channel_url, headers=HEADERS, verify=VERIFY)

                if response is not None and response.status_code == 200:
                    response_json = response.json()
            if response_json is not None:
                if 'schedule' in response_json:
                    if 'scheduleList' in response_json['schedule']:
                        schedule_list = []
                        for slot in response_json['schedule']['scheduleList']:
                            new_slot = {'Name': slot['title'] if 'title' in slot else '',
                                        'Thumbnail': ICON,
                                        'Poster': '',
                                        'Rating': '',
                                        'Genre': '',
                                        'Start': int(slot['schedule_start'].split('.')[0]),
                                        'Stop': int(slot['schedule_stop'].split('.')[0])}
                            if 'thumbnail' in slot:
                                if slot['thumbnail'] is not None:
                                    if 'url' in slot['thumbnail']:
                                        slot['thumbnail']['url']
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
                                    new_slot['Poster'] = self.Poster
                            if int(slot['schedule_start'].split('.')[0]) <= timestamp <= int(slot['schedule_stop'].split('.')[0]):
                                on_now = new_slot

                            new_slot['Name'] = new_slot['Name'].strip()
                            new_slot['Description'] = new_slot['Description'].strip()
                            new_slot['Genre'] = new_slot['Genre'].strip()
                            new_slot['Rating'] = new_slot['Rating'].strip().replace('_', ' ')

                            schedule[new_slot['Start']] = new_slot
                            schedule_list.append(
                                (self.GUID, new_slot['Start'], new_slot['Stop'],
                                new_slot['Name'].replace(
                                    "'", "''"), new_slot['Description'].replace("'", "''"),
                                new_slot['Thumbnail'], new_slot['Poster'], new_slot['Genre'],
                                new_slot['Rating'], int(time.time()))
                            )

                        if schedule_list:
                            self.saveSlot(self.GUID, schedule_list)

                result = True

        return result, on_now

    def onDemand(self):
        log('Checking if channel is On Demand')
        on_demand = False

        on_demand_url = "%s/cms/api/channels/%s/network" % (self.Endpoints['cms_url'], self.GUID)
        response = requests.get(on_demand_url, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            json = response.json()
            if len(json):
                for category in json:
                    tiles = {}
                    try:
                        tiles = category['tiles']
                    except:
                        pass
                    if len(tiles):
                        on_demand = True
                        break

        return on_demand

    def onDemandCategories(self):
        log('Retrieving channel %s On Demand Folders from DB' % self.Name)
        cursor = self.DB.cursor()
        channel_categories = []
        try:
            category_query = "SELECT * FROM On_Demand_Folders WHERE Channel_GUID = '%s' ORDER BY Name ASC" % self.GUID
            cursor.execute(category_query)
            categories = cursor.fetchall()
            if categories is not None and len(categories) > 0:
                for category in categories:
                    new_category = {
                        'Channel_GUID': category[0],
                        'Name': category[1].replace("''", "'"),
                        'Last_Update': category[2]
                    }
                    channel_categories.append(new_category)
            else:
                channel_categories = self.getOnDemandCategories()
        except sqlite3.Error as err:
            log('Failed to read On Demand Categories for channel %s from DB, error => %s' % (self.Name, err))
        except Exception as exc:
            log('Failed to read On Demand Categories for channel %s from DB, exception => %s' % (self.Name, exc))

        return channel_categories

    def getOnDemandCategories(self):
        log('Retrieving On Demand channel %s Folders from Sling' % self.Name)
        timestamp = int(time.time())
        categories = []
        category_query = ""

        on_demand_url = "%s/cms/api/channels/%s/network" % (self.Endpoints['cms_url'], self.GUID)
        log(on_demand_url)
        response = requests.get(on_demand_url, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            json = response.json()
            if len(json):
                for category in json:
                    new_category = {
                        'Total_Pages': category['num_pages'] if 'num_pages' in category else 1,
                        'Link': category['_href'],
                        'Name': category['title'].replace("''", "'"),
                        'Expiration': str(category['expires_at']).replace('T', ' ').replace('Z', '')
                    }
                    if '.' in new_category['Expiration']: new_category['Expiration'] = new_category['Expiration'][:-4]
                    new_category['Expiration'] = timeStamp(stringToDate(new_category['Expiration'],'%Y-%m-%d %H:%M:%S'))
                    categories.append(new_category)
                    category_query += "REPLACE INTO On_Demand_Folders (Channel_GUID, Name, Pages, Expiration, " \
                                      "Last_Update) VALUES ('%s', '%s', %i, %i, %i); " % \
                                      (self.GUID, new_category['Name'], new_category['Total_Pages'],
                                       new_category['Expiration'], timestamp)

        cursor = self.DB.cursor()
        try:
            cursor.executescript(category_query)
            self.DB.commit()
        except sqlite3.Error as err:
            log('Failed to save categories for channel %s to DB, error => %s' % (self.Name, err))
        except Exception as exc:
            log('Failed to save categories for channel %s to DB, exception => %s' % (self.Name, exc))

        return categories

    def getOnDemandAssets(self, category, update=False):
        log('Retrieving On Demand channel %s Category %s assets from DB' % (self.Name, category))
        assets = []

        cursor = self.DB.cursor()
        try:
            query = "SELECT * FROM On_Demand_Assets WHERE Channel_GUID = '%s' AND Category = '%s' ORDER BY Name ASC" % \
                    (self.GUID, category)
            cursor.execute(query)
            db_assets = cursor.fetchall()
            for db_asset in db_assets:
                asset = {
                    'Channel_GUID': db_asset[0],
                    'Category': db_asset[1],
                    'Asset_GUID': db_asset[2],
                    'Type': db_asset[3],
                    'Name': db_asset[4].replace("''", "'"),
                    'Description': db_asset[5].replace("''", "'"),
                    'Thumbnail': db_asset[6],
                    'Poster': db_asset[7],
                    'Rating': db_asset[8],
                    'Duration': db_asset[9],
                    'Release_Year': db_asset[10],
                    'Start': db_asset[11],
                    'Stop': db_asset[12],
                    'Playlist_URL': db_asset[13]
                }
                assets.append(asset)
        except sqlite3.Error as err:
            log('Failed to retrieve assets for category %s from DB, error => %s' % (category, err))
        except Exception as exc:
            log('Failed to retrieve assets for category %s from DB, exception => %s' % (category, exc))

        if len(assets) == 0 or update:
            url_category = category.replace(' ', '+').replace('&', '_A').replace('/', '_F')
            category_url = "%s/cms/api/channels/%s/network/ribbon=%s;page=%i;page_size=medium" % \
                           (self.Endpoints['cms_url'], self.GUID, url_category, 0)
            log(category_url)
            response = requests.get(category_url, headers=HEADERS, verify=VERIFY)
            if response is not None and response.status_code == 200:
                response = response.json()
            else:
                category_url = "%s/cms/api/channels/%s/network/ribbon=%s;page=%i;page_size=medium/" % \
                               (self.Endpoints['cms_url'], self.GUID, url_category, 0)
                log(category_url)
                response = requests.get(category_url, headers=HEADERS, verify=VERIFY)
                if response is not None and response.status_code == 200:
                    response = response.json()
            if response is not None:
                if 'num_pages' in response:
                    pages = response['num_pages']
                    if 'tiles' in response:
                        assets.extend(self.processOnDemandAssets(category, response))
                        if pages > 1:
                            for page in range(1, pages):
                                category_url = "%s/cms/api/channels/%s/network/ribbon=%s;page=%i;page_size=medium" % \
                                               (self.Endpoints['cms_url'], self.GUID, url_category, page)
                                log(category_url)
                                response = requests.get(category_url, headers=HEADERS, verify=VERIFY)
                                if response is not None and response.status_code == 200:
                                    response = response.json()
                                else:
                                    category_url = "%s/cms/api/channels/%s/network/ribbon=%s;page=%i;page_size=medium/" % \
                                                   (self.Endpoints['cms_url'], self.GUID, url_category, page)
                                    log(category_url)
                                    response = requests.get(category_url, headers=HEADERS, verify=VERIFY)
                                    if response is not None and response.status_code == 200:
                                        response = response.json()
                                if response is not None:
                                    if 'tiles' in response:
                                        assets.extend(self.processOnDemandAssets(category, response))

        return assets

    def processOnDemandAssets(self, category, response):
        log('Processing On Demand channel %s category %s assets from Sling' % (self.Name, category))
        timestamp = int(time.time())
        assets = []
        query = ""
        for asset in response['tiles']:
            log(json.dumps(asset, indent=4))
            start = 0
            stop = 0
            if 'start_time' in asset:
                start = timeStamp(stringToDate(asset['start_time'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
            if 'stop_time' in asset:
                try:
                    stop = timeStamp(stringToDate(asset['stop_time'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
                except:
                    stop = timeStamp(stringToDate('2099-01-01 01:01:01', '%Y-%m-%d %H:%M:%S'))
            new_asset = {
                'Channel_GUID': self.GUID,
                'Category': category,
                'Asset_GUID': asset['external_id'],
                'Type': asset['type'],
                'Name': asset['title'],
                'Description': '',
                'Thumbnail': asset['thumbnail']['url'] if 'thumbnail' in asset else ICON,
                'Poster': asset['thumbnail']['url'] if 'thumbnail' in asset else ICON,
                'Rating': '',
                'Duration': int(asset['duration']) if 'duration' in asset else 0,
                'Release_Year': asset['release_year'] if 'release_year' in asset else 0,
                'Start': start,
                'Stop': stop,
                'Playlist_URL': ''
            }
            ratings = ''
            for rating in asset['ratings']:
                if rating.replace('_', ' ') not in ratings:
                    ratings = '%s, %s' % (ratings, rating.replace('_', ' ')) if len(ratings) > 0 else rating.replace('_', ' ')
            new_asset['Rating'] = ratings
            if asset['type'] == 'svod' or asset['type'] == 'vod' or asset['type'] == 'live_event':
                asset_info = requests.get(asset['_href'], headers=HEADERS, verify=VERIFY)
                if asset_info is not None and asset_info.status_code == 200:
                    asset_info = asset_info.json()
                    if len(asset_info):
                        # log(json.dumps(asset_info, indent=4))
                        if 'program' in asset_info:
                            if 'background_image' in asset_info['program']:
                                new_asset['Poster'] = asset_info['program']['background_image']['url']
                        if 'entitlements' in asset_info:
                            if len(asset_info['entitlements']) > 0:
                                new_asset['Playlist_URL'] = asset_info['entitlements'][0]['qvt_url']
                        if 'metadata' in asset_info:
                            if 'description' in asset_info['metadata']:
                                if asset_info['metadata']['description'] is not None:
                                    new_asset['Description'] = asset_info['metadata']['description']
            elif asset['type'] == 'linear':
                asset_info = requests.get(asset['_href'], headers=HEADERS, verify=VERIFY)
                if asset_info is not None and asset_info.status_code == 200:
                    asset_info = asset_info.json()
                    if len(asset_info):
                        if 'program' in asset_info:
                            if 'background_image' in asset_info['program']:
                                if asset_info['program']['background_image'] is not None:
                                    new_asset['Poster'] = asset_info['program']['background_image']['url']
                        if 'metadata' in asset_info:
                            if 'description' in asset_info['metadata']:
                                if asset_info['metadata']['description'] is not None:
                                    new_asset['Description'] = asset_info['metadata']['description']
                        if 'schedules' in asset_info:
                            for schedule in asset_info['schedules']:
                                if 'playback_info' in schedule:
                                    new_asset['Playlist_URL'] = schedule['playback_info']
                                    break
            elif asset['type'] == 'series':
                asset_url = "%s/cms/api/franchises/%s" % (self.Endpoints['cms_url'], asset['external_id'])
                log(asset_url)
                asset_info = requests.get(asset_url, headers=HEADERS, verify=VERIFY)
                if asset_info is not None and asset_info.status_code == 200:
                    asset_info = asset_info.json()
                    if len(asset_info):
                        # log(json.dumps(asset_info, indent=4))
                        if 'description' in asset_info:
                            if asset_info['description'] is not None:
                                new_asset['Description'] = asset_info['description']
                        if 'image' in asset_info:
                            new_asset['Thumbnail'] = asset_info['image']['url']
                        if 'background_image' in asset_info:
                            new_asset['Poster'] = asset_info['background_image']['url']
                        self.saveSeries(new_asset, asset_url)
            elif asset['type'] == 'linear':
                notificationDialog("linear here", "Alert")

            assets.append(new_asset)
            query += "REPLACE INTO On_Demand_Assets (Channel_GUID, Category, Asset_GUID, Type, Name, " \
                     "Description, Thumbnail, Poster, Duration, Rating, Release_Year, Start, Stop, Playlist_URL, " \
                     "Last_Update) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %i, '%s', %i, %i, %i, '%s', %i); " % \
                     (self.GUID, category, new_asset['Asset_GUID'], new_asset['Type'],
                      new_asset['Name'].replace("'", "''"), new_asset['Description'].replace("'", "''"),
                      new_asset['Thumbnail'], new_asset['Poster'], new_asset['Duration'], new_asset['Rating'],
                      new_asset['Release_Year'], new_asset['Start'], new_asset['Stop'], new_asset['Playlist_URL'],
                      timestamp)

        if query != "":
            cursor = self.DB.cursor()
            try:
                cursor.executescript(query)
                self.DB.commit()
            except sqlite3.Error as err:
                log('Failed to save assets for channel %s category %s to DB, error => %s\r%s' % (self.Name, category, err, query))
            except Exception as exc:
                log('Failed to save assets for channel %s category %s to DB, exception => %s\r%s' % (self.Name, category, exc, query))

        return assets

    def saveSeries(self, series, show_url):
        log('Saving series %s to DB' % (series['Name']))
        timestamp = int(time.time())
        query = "REPLACE INTO SHOWS (GUID, Name, Description, Thumbnail, Poster, Show_URL, Last_Update) VALUES " \
                "(?, ?, ?, ?, ?, ?, ?)"
        cursor = self.DB.cursor()
        try:

            cursor.execute(query, (series['Asset_GUID'], series['Name'].replace("'", "''"),
                                   series['Description'].replace("'", "''"), series['Thumbnail'],
                                   series['Poster'], show_url, timestamp))
            self.DB.commit()
        except sqlite3.Error as err:
            log('Failed to save series %s to DB, error => %s\r%s' % (series['Name'], err, query))
        except Exception as exc:
            log('Failed to save series %s to DB, exception => %s\r%s' % (series['Name'], exc, query))

    def saveChannel(self):
        log('Saving channel %s into DB' % self.Name)
        timestamp = int(time.time())
        cursor = self.DB.cursor()
        channel_query = ''

        self.checkFlags()
        if self.GUID != '':
            try:
                channel_query = "REPLACE INTO Channels (GUID, ID, Name, Call_Sign, Language, Genre, Thumbnail, Poster, " \
                                "Offered, Qvt_Url, On_Demand, Last_Update, Hidden, Protected) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

                cursor.execute(channel_query, (self.GUID, self.ID, self.Name.replace("'", "''"), self.Call_Sign,
                                               self.Language, self.Genre, self.Thumbnail, self.Poster, int(self.Offered),
                                               self.Qvt_Url, int(self.On_Demand), timestamp, int(self.Hidden), int(self.Protected)))
                self.DB.commit()
            except sqlite3.Error as err:
                log('Failed to save channel %s to DB, error => %s\rQuery => %s' % (self.Name, err, json.dumps(self.channelInfo(), indent=4)))
            except Exception as exc:
                log('Failed to save channel %s to DB, exception => %s\rQuery => %s' % (self.Name, exc, json.dumps(self.channelInfo(), indent=4)))
        else:
            log('Channel GUID cannot be blank, not saving.')

    def checkFlags(self):
        log('Checking flags for channel %s in DB' % self.Name)
        cursor = self.DB.cursor()

        try:
            flag_query = "SELECT Hidden, Protected FROM Channels WHERE GUID = '%s'" % self.GUID

            cursor.execute(flag_query)
            flags = cursor.fetchone()
            if flags is not None:
                self.Hidden = bool(flags[0])
                self.Protected = bool(flags[1])

                log('Retrieved channel %s flags from DB, Hidden = %s and Protected = %s' % (self.Name, str(self.Hidden), str(self.Protected)))
        except sqlite3.Error as err:
            log('Failed to check flags for channel %s in DB, error => %s\rQuery => %s' %
                (self.Name, err, json.dumps(self.channelInfo(), indent=4)))
        except Exception as exc:
            log('Failed to check flags for channel %s in DB, exception => %s\rQuery => %s' % (
                self.Name, exc, json.dumps(self.channelInfo(), indent=4)))

    def getDBChannel(self, guid):
        # log('Retrieving channel %s from DB' % guid)
        found = False
        db_channel = None
        timestamp = int(time.time())

        cursor = self.DB.cursor()
        # query = "SELECT * FROM Channels WHERE GUID = '%s'" % guid
        query = "SELECT * FROM Channels LEFT JOIN (SELECT * FROM Guide WHERE Start <= %i AND Stop >= %i) AS Guide ON " \
                "Channels.GUID = Guide.Channel_GUID WHERE GUID = '%s'" % (timestamp, timestamp, guid)
        cursor.execute(query)
        channel = cursor.fetchone()
        if channel is not None:
            db_channel = {
                'GUID': channel[0],
                'ID': channel[1],
                'Name': channel[2].replace("''", "'"),
                'Call_Sign': channel[3],
                'Language': channel[4],
                'Genre': channel[5],
                'Thumbnail': channel[6],
                'Poster': channel[7],
                'Offered': bool(channel[8]),
                'Qvt_Url': channel[9],
                'On_Demand': channel[10],
                'Last_Update': channel[11],
                'Hidden': channel[12],
                'Protected': channel[13]
            }

            on_now = {}
            if channel[14] == channel[0]:
                on_now = {
                    'Channel_GUID': channel[14],
                    'Start': channel[15],
                    'Stop': channel[16],
                    'Name': channel[17].replace("''", "'"),
                    'Description': channel[18].replace("''", "'"),
                    'Thumbnail': channel[19],
                    'Poster': channel[20],
                    'Genre': channel[21],
                    'Rating': channel[22]
                }
            db_channel['On_Now'] = on_now

            if db_channel['On_Demand'] != -1: db_channel['On_Demand'] = bool(db_channel['On_Demand'])

            found = True

        return found, db_channel

    def saveSlot(self, channel_guid, schedule_list):
        log('Saving guide info into DB for channel %s' % self.Name)
        cursor = self.DB.cursor()

        try:
            slot_query = "REPLACE INTO Guide (Channel_GUID, Start, Stop, Name, Description, Thumbnail, Poster, " \
                            "Genre, Rating, Last_Update) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.executemany(slot_query, schedule_list)
        except sqlite3.Error as err:
            log('Failed to save guide info for channel %s into DB, error => %s' % (self.Name, err))
        except Exception as exc:
            log('Failed to save guide info for channel %s into DB, exception => %s' % (self.Name, exc))

        self.DB.commit()

    def getDBGuide(self, timestamp):
        log('Retrieving channel %s guide from DB' % self.Name)
        found = False
        db_on_now = None

        cursor = self.DB.cursor()
        query = "SELECT * FROM Guide WHERE Channel_GUID = '%s' and (Start <= %s and Stop >= %i)" % \
                (self.GUID, timestamp, timestamp)
        cursor.execute(query)
        on_now = cursor.fetchone()
        if on_now is not None:
            db_on_now = {
                'Channel_GUID': on_now[0],
                'Start': on_now[1],
                'Stop': on_now[2],
                'Name': on_now[3].replace("''", "'"),
                'Description': on_now[4].replace("''", "'"),
                'Thumbnail': on_now[5],
                'Poster': on_now[6],
                'Genre': on_now[7],
                'Rating': on_now[8]
            }

            found = True

        return found, db_on_now

    def processVODAsset(self, asset):
        log('Processing VOD %s asset from Sling' % asset['title'])

        timestamp = int(time.time())
        new_asset = {
            'GUID': '',
            'ID': -1,
            'Name': '',
            'Description': '',
            'Thumbnail': ICON,
            'Poster': FANART,
            'Duration': 0,
            'Rating': '',
            'Genre': '',
            'Playlist_URL': '',
            'Start': 0,
            'Stop': 0,
            'Year': 0,
            'Type': ''
        }
        query = ''

        # log(json.dumps(asset, indent=4))
        if 'title' in asset:
            new_asset['Name'] = asset['title']
        if 'thumbnail' in asset:
            new_asset['Thumbnail'] = asset['thumbnail']['url']
        if 'duration' in asset:
            new_asset['Duration'] = asset['duration']
        if 'id' in asset:
            new_asset['ID'] = int(asset['id'])
        if 'external_id' in asset:
            new_asset['GUID'] = asset['external_id']
        if 'thumbnail' in asset:
            new_asset['Poster'] = asset['thumbnail']['url']
        if 'release_year' in asset:
            new_asset['Year'] = asset['release_year']

        if 'program' in asset:
            ratings = ''
            for rating in asset['program']['ratings']:
                if rating.replace('_', ' ') not in ratings:
                    ratings = '%s, %s' % (ratings, rating.replace('_', ' ')) if len(ratings) > 0 else rating.replace('_', ' ')
            new_asset['Rating'] = ratings
            if 'thumbnail' in asset['program']:
                if asset['program']['thumbnail'] is not None:
                    new_asset['Thumbnail'] = asset['program']['thumbnail']['url']
            if 'background_image' in asset['program'] and new_asset['Poster'] == '':
                new_asset['Poster'] = asset['program']['background_image']['url']
            if 'name' in asset['program']:
                new_asset['Name'] = asset['program']['name']
            else:
                new_asset['Name'] = asset['title']
            if 'type' in asset['program']:
                new_asset['Type'] = asset['program']['type']
        if 'metadata' in asset:
            if 'ratings' in asset['metadata']:
                ratings = ''
                for rating in asset['metadata']['ratings']:
                    if rating.replace('_', ' ') not in ratings:
                        ratings = '%s, %s' % (ratings, rating.replace('_', ' ')) if len(ratings) > 0 else rating.replace('_', ' ')
                new_asset['Rating'] = ratings
            genres = ''
            if 'genre' in asset['metadata']:
                for genre in asset['metadata']['genre']:
                    if genre.replace('_', ' ') not in genres:
                        genres = '%s, %s' % (genres, genre.replace('_', ' ')) if len(genres) > 0 else genre.replace('_', ' ')
            new_asset['Genre'] = genres
            if new_asset['Type'] == 'episode':
                if 'episode_title' in asset['metadata'] and 'episode_season' in asset['metadata'] and \
                        'episode_number' in asset['metadata']:
                    new_asset['Name'] = 'S%iE%i - %s' % \
                                        (asset['metadata']['episode_season'], asset['metadata']['episode_number'],
                                         asset['metadata']['episode_title'])
                elif 'episode_season' in asset['metadata'] and 'episode_number' in asset['metadata'] and \
                        asset['metadata']['episode_season'] != '' and asset['metadata']['episode_number'] != '':
                    new_asset['Name'] = 'S%iE%i - %s' % \
                                        (asset['metadata']['episode_season'], asset['metadata']['episode_number'],
                                         new_asset['Name'])
            if 'description' in asset['metadata']:
                if 'episode_title' in asset['metadata']:
                    new_asset['Description'] = '%s\r\r%s' % (asset['title'], asset['metadata']['description'])
                else:
                    new_asset['Description'] = asset['metadata']['description']
        if 'entitlements' in asset:
            for entitlement in asset['entitlements']:
                start = timeStamp(stringToDate(entitlement['playback_start'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
                stop = timeStamp(stringToDate(entitlement['playback_stop'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
                if start <= timestamp <= stop:
                    if 'entitlement_type' in entitlement:
                        new_asset['Type'] = entitlement['entitlement_type']
                    new_asset['Start'] = start
                    new_asset['Stop'] = stop
                    new_asset['Playlist_URL'] = entitlement['qvt_url']
        elif 'schedules' in asset:
            for schedule in asset['schedules']:
                start = timeStamp(stringToDate(schedule['playback_start'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
                stop = timeStamp(stringToDate(schedule['playback_stop'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
                if start <= timestamp <= stop:
                    new_asset['Start'] = start
                    new_asset['Stop'] = stop
                    new_asset['Playlist_URL'] = schedule['playback_info']

        if new_asset['Playlist_URL'] != '':
            query += "REPLACE INTO VOD_Assets (GUID, ID, Name, Description, Thumbnail, Poster, Duration, Rating, " \
                     "Genre, Playlist_URL, Start, Stop, Release_Year, Type, Last_Update) " \
                     "VALUES ('%s', %i, '%s', '%s', '%s', '%s', %i, '%s', '%s', '%s', %i, %i, %i, '%s', %i); " % \
                     (new_asset['GUID'], new_asset['ID'], new_asset['Name'].replace("'", "''"),
                      new_asset['Description'].replace("'", "''"), new_asset['Thumbnail'], new_asset['Poster'],
                      new_asset['Duration'], new_asset['Rating'], new_asset['Genre'], new_asset['Playlist_URL'],
                      new_asset['Start'], new_asset['Stop'], new_asset['Year'], new_asset['Type'], timestamp)

        if query != "":
            cursor = self.DB.cursor()
            try:
                cursor.executescript(query)
                self.DB.commit()
            except sqlite3.Error as err:
                log('Failed to save VOD asset to DB, error => %s\r%s' % (err, query))
            except Exception as exc:
                log('Failed to save VOD asset to DB, exception => %s\r%s' % (exc, query))

        return self.getVODAsset(new_asset['GUID'])

    def getVODAsset(self, guid):
        log('Retrieving VOD Asset %s from DB' % guid)
        timestamp = int(time.time())

        found = False
        db_vod = None

        cursor = self.DB.cursor()
        query = "SELECT * FROM VOD_Assets WHERE GUID = '%s' and (Start <= %s and Stop >= %i)" % \
                (guid, timestamp, timestamp)
        cursor.execute(query)
        vod = cursor.fetchone()
        if vod is not None:
            db_vod = {
                'GUID': vod[0],
                'ID': vod[1],
                'Name': vod[2].replace("''", "'"),
                'Description': vod[3].replace("''", "'"),
                'Thumbnail': vod[4],
                'Poster': vod[5],
                'Duration': vod[6],
                'Rating': vod[7],
                'Genre': vod[8],
                'Playlist_URL': vod[9],
                'Start': vod[10],
                'Stop': vod[11],
                'Year': vod[12],
                'Type': vod[13],
                'infoLabels': {
                    'title': vod[2].replace("''", "'"),
                    'plot': vod[3].replace("''", "'"),
                    'genre': 'VOD',
                    'duration': vod[6],
                    'mediatype': 'Video',
                    'year': vod[12],
                    'mpaa': vod[7]
                },
                'infoArt': {
                    'thumb': vod[4],
                    'logo': vod[4],
                    'clearlogo': vod[4],
                    'poster': vod[4],
                    'fanart': vod[5]
                }
            }

            found = True
            debug = dict(urlParse.parse_qsl(DEBUG_CODE))
            bypass = False
            log('Debug Code: %s' % json.dumps(debug, indent=4))
            if 'rental' in debug:
                bypass = bool(debug['rental'])
            log('Bypass: %s' % str(bypass))
            if (db_vod['Type'] == 'rental' and db_vod['GUID'] not in USER_SUBS) and not bypass:
                return True, {}

        return found, db_vod
