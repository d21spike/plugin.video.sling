from resources.lib.globals import *

# ==================================================================================================================
#
# My TV Menu
#
# ==================================================================================================================

# ======================== New headers in Sling require JWT Access token ========================
TVOD_HEADERS = {
    'Origin': 'https://watch.sling.com',
    'User-Agent': USER_AGENT,
    'Accept': '*/*',
    'Referer': 'https://watch.sling.com/browse/my-tv',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'Authorization': 'Bearer %s' % ACCESS_TOKEN_JWT,
    'Sling-Interaction-ID': DEVICE_ID
}

# ======================== Main Menu ========================
def myTV(self):
    log('myTV(): Building Menu')
    
    # ======================== Menu Item Info Properties ========================
    infoLabels = {'title': '', 'plot': '', 'genre': '', 'duration': '', 'mediatype': 'Video', 'mpaa': ''}
    infoArt = {'thumb': ICON, 'logo': ICON, 'clearlogo': ICON, 'poster': ICON, 'fanart': FANART}

    # ======================== Check for debug codes ========================
    debug = dict(urlParse.parse_qsl(DEBUG_CODE))
    log('Debug Code: %s' % json.dumps(debug, indent=4))
    allow = False
    if 'rental' in debug:
        if debug['rental'] == 'True':
            allow = True
    
    # ======================== Retrieve My TV Data ========================
    mytv_url = '%s/pg/v1/my_tv_tvod?dma=%s&timezone=%s' % (self.endPoints['cmwnext_url'], USER_DMA, USER_OFFSET)
    log('myTV(): URL => %s' % mytv_url)
    response = requests.get(mytv_url, headers=TVOD_HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'ribbons' in response:
            for ribbon in response['ribbons']:
                try:
                    log('My TV On Demand Ribbon: %s with %i tiles' % (ribbon['title'], int(ribbon['total_tiles'])))
                    if int(ribbon['total_tiles']) > 0 and ('Rentals' not in ribbon['title'] or allow):
                        if ribbon['title'] != 'Add Premium Channels & More':
                            infoLabels['title'] = ribbon['title']
                            addDir(ribbon['title'], self.handleID, ribbon['href'], 'my_tv', infoLabels, infoArt)
                except:
                    log('Failed to load ribbon:\n %s' % json.dumps(ribbon, indent=4))

# ======================== My TV Ribbon Menu ========================
def myTVRibbon(self):
    name = self.params['name']
    url = self.params['url']
    log('myTVRibbon(): Processing Ribbon %s URL: %s' % (name, url))

    # ======================== Retrieve Ribbon JSON ========================
    response = requests.get(url, headers=TVOD_HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        # log(json.dumps(response, indent=4))

        # ======================== Process Ribbon Tiles ========================
        if 'tiles' in response:
            if len(response['tiles']) > 0:
                session = createResilientSession()
                for tile in response['tiles']:
                    action = tile['primary_action']
                    if action is None:
                        if len(tile['actions']) > 0:
                            action == tile['actions'][0]

                    log('Tile %s action %s' % (tile['title'], str(action)))
                    if action == 'CHANNEL_GUIDE_VIEW':
                        myTVChannel(self, tile)
                    elif action == 'PLAY_CONTENT' and 'channel_name' in tile:
                        myTVChannel(self, tile)
                    elif action == 'ASSET_IVIEW':
                        myTVProgram(self, tile, session)
                    elif action == 'FRANCHISE_IVIEW':
                        myTVShow(self, tile)
                    elif action == 'ASSET_RECORDING_IVIEW':
                        myTVRecording(self, tile, session)
                    elif action == 'FRANCHISE_RECORDING_IVIEW':
                        myShowRecording(self, tile, session)
                session.close()

# ======================== My TV Channel (Uses Class) ========================
def myTVChannel(self, tile):
    log('myTVChannel: Adding Channel')

    asset = initAsset(self, None)
    asset = myTVJSON(self, tile, asset)
    log(json.dumps(asset, indent=4))

    timestamp = int(time.time())
    
    # ======================== Make sure an Asset was returned ========================
    if asset['GUID'] != '':

        # ======================== Init Channel ========================
        channel = Channel(asset['GUID'], self.endPoints, self.DB)

        # ======================== Check On Now and update Art ========================
        if len(channel.On_Now) == 0 or channel.On_Now['Stop'] < timestamp:
            result, on_now = channel.onNow()
            if result:
                channel.On_Now = on_now
        infoArt = channel.infoArt()
        if channel.On_Now != {} and channel.On_Now['Stop'] >= timestamp:
            infoArt['thumb'] = channel.On_Now['Thumbnail']
            infoArt['poster'] = channel.On_Now['Poster']

        # ======================== Check if ONLY On Demand Channel ========================
        if channel.infoLabels()['duration'] > 0 and 'OFF-AIR' not in channel.infoLabels()['plot']:
            # ======================== Live Channel ========================
            context_items = [('Hide Channel', 'RunPlugin(plugin://plugin.video.sling/?'
                              'mode=setting&name=%s&value=%s)' % ('hide_channel', channel.GUID))]
            if channel.On_Demand:
                context_items.append(('View On Demand', 'Container.Update(%s?mode=demand&guid=%s&name=%s)' %
                                      (ADDON_URL, channel.GUID, channel.Name)))
                context_items.sort(reverse=True)
            addLink(channel.Name, self.handleID, channel.Qvt_Url, 'play',
                    channel.infoLabels(), infoArt, channel.ID, context_items)
        elif channel.infoLabels()['duration'] == 0:
            # ======================== On Demand Channel ========================
            context_items = [
                ('Update On Demand Content', 'RunPlugin(plugin://plugin.video.sling/?mode=demand&guid=%s&'
                 'action=update)' % channel.GUID)
            ]
            addDir(channel.Name, self.handleID, '', 'demand&guid=%s' % channel.GUID,
                   channel.infoLabels(), channel.infoArt(), context_items)

# ======================== My TV Program/Episode/Sport/Etc ========================
def myTVProgram(self, tile, session):
    log('myTVProgram(): Adding Program')

    asset = initAsset(self, None)
    asset = myTVJSON(self, tile, asset)

    # ======================== Check if an Asset was returned ========================
    if asset['GUID'] != '' and asset['URL'] != '':

        # ======================== Get Asset JSON ========================
        response = session.get(asset['URL'], headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            response = response.json()
            asset = assetJSON(self, response, asset)
            asset = assetInfo(self, asset)
            log(json.dumps(asset, indent=4))

            context_items = []
            if asset['Show_GUID'] != '' and (asset['Name'] != asset['Show_Name']) and \
                    (asset['Episode'] != '' and asset['Season'] != ''):
                context_items = [
                    ('View Show', 'Container.Update(plugin://plugin.video.sling/?mode=show&guid=%s&name=%s)' %
                     (asset['Show_GUID'], asset['Show_Name']))
                ]
            if 'Upcomming' in asset['infoLabels']['title'] or 'Live' in asset['infoLabels']['title']:
                log (json.dumps(asset, indent=4))
                context_items.append(('Set to Record', 'RunPlugin(%s?mode=record&guid=%s&asset_url=%s)' %
                                      (ADDON_URL, asset['GUID'], asset['URL'])))
            if asset['Playlist_URL'] != '':
                if asset['Playlist_URL'].split('/')[-2] == 'scheduleqvt' and asset['Channel_GUID'] != '':
                    asset['Playlist_URL'] += '?channel=%s' % asset['Channel_GUID']
            addLink(asset['Name'], self.handleID, asset['Playlist_URL'], asset['Mode'],
                    asset['infoLabels'], asset['infoArt'], 1, context_items)

# ======================== My TV Show (Uses Class) ========================
def myTVShow(self, tile):
    log('myTVShow(): Adding Show')
    
    asset = initAsset(self, None)
    asset = myTVJSON(self, tile, asset)
    log(json.dumps(asset, indent=4))

    # ======================== Check if an Asset was returned ========================
    if asset['GUID'] != '':
        show = Show(asset['GUID'], self.endPoints, self.DB)
        if show.Name != "":
            context_items = [
                ('Add to Favorite Shows', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&action=favorite)' % show.GUID),
                ('Update Show', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&action=update)' % show.GUID)
            ]
            context_items.append(('Record All', 'RunPlugin(%s?mode=record_show&type=all&guid=%s)' %
                                      (ADDON_URL, show.GUID)))
            context_items.append(('Record New', 'RunPlugin(%s?mode=record_show&type=new&guid=%s)' %
                                    (ADDON_URL, show.GUID)))
            addDir(show.Name, self.handleID, '', 'show&guid=%s' % show.GUID, show.infoLabels(), show.infoArt(), context_items)

# ======================== My TV Program DVR ========================
def myTVRecording(self, tile, session):
    log('myTVRecording(): Adding asset')

    asset = initAsset(self, None)
    asset = myTVJSON(self, tile, asset)

    # ======================== Check if an Asset was returned ========================
    if asset['URL'] != '':
        response = session.get(asset['URL'], headers=HEADERS, verify=VERIFY)
        if response.status_code == 200:
            response = response.json()
            asset = assetJSON(self, response, asset)
            asset = assetInfo(self, asset)
            log(json.dumps(asset, indent=4))

            properties = {}
            if asset['Duration'] != 0:
                properties['totaltime'] = asset['Duration']
            if asset['Resume'] != 0:
                properties['resumetime'] = asset['Resume']
            log('Recording Properties: %s' % json.dumps(properties, indent=4))

            context_items = []
            if asset['Show_GUID'] != '':
                context_items.append(('View Show', 'Container.Update(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                   'name=%s)' % (asset['Show_GUID'], asset['Show_Name'])))
            context_items.append(('Delete Recording', 'RunPlugin(%s?mode=del_record&guid=%s&asset_url=%s)' %
                                  (ADDON_URL, asset['GUID'], asset['URL'])))
            if asset['Channel_GUID'] != '':
                asset['Playlist_URL'] += '?channel=%s' % asset['Channel_GUID']
            addLink(asset['Name'], self.handleID, asset['Playlist_URL'], asset['Mode'],
                    asset['infoLabels'], asset['infoArt'], 1, context_items, properties)

# ======================== My TV Show DVR ========================
def myShowRecording(self, tile, session):
    log('myShowRecording(): Adding asset')

    asset = initAsset(self, None)
    asset = myTVJSON(self, tile, asset)
    rec_show = Show(asset['GUID'], self.endPoints, self.DB)
        
    # ======================== Check if an Asset was returned ========================
    if asset['URL'] != '':
        payload = {
            "franchise": asset['GUID'],
            "filter": "all",
            "product": "sling",
            "platform": "browser"
        }
        response = session.post(asset['URL'], headers=HEADERS, data=json.dumps(payload), auth=self.auth.getAuth(), verify=VERIFY)
        if response.status_code == 200:
            response = response.json()
            if 'seasons' in response:
                for season in response['seasons']:
                    if 'episodes' in season:
                        for episode in season['episodes']:
                            if 'qvt' in episode:
                                rec_episode = {
                                    'GUID': '',
                                    'Show_GUID': rec_show.GUID,
                                    'Rec_GUID': '',
                                    'Channel_GUID': '',
                                    'Name': '',
                                    'Show_Name': rec_show.Name,
                                    'Season': 0,
                                    'Number': 0,
                                    'Description': '',
                                    'Thumbnail': rec_show.Thumbnail,
                                    'Poster': rec_show.Poster,
                                    'Genre': '',
                                    'Rating':'',
                                    'Start': 0,
                                    'Stop': 0,
                                    'Duration': 0,
                                    'Asset_URL': '',
                                    'Playlist_URL': episode['qvt'],
                                    'Mode': 'info',
                                    'infoLabels': {},
                                    'infoArt': {}
                                }
                                
                                if '_href' in episode:
                                    rec_episode['Asset_URL'] = episode['_href']
                                if 'ratings' in episode:
                                    ratings = ''
                                    for rating in episode['ratings']:
                                        ratings = '%s, %s' % (ratings, rating) if ratings != '' else rating
                                    rec_episode['Rating'] = ratings
                                if 'title' in episode:
                                    rec_episode['Show_Name'] = episode['title']
                                if 'program_guid' in episode:
                                    rec_episode['GUID'] = episode['program_guid']
                                if 'thumbnail' in episode:
                                    if 'url' in episode['thumbnail']:
                                        rec_episode['Thumbnail'] = episode['thumbnail']['url']
                                if 'recording_info' in episode:
                                    info = episode['recording_info']
                                    if 'channel_guid' in info:
                                        rec_episode['Channel_GUID'] = info['channel_guid']
                                    if 'episode_season' in info:
                                        rec_episode['Season'] = info['episode_season']
                                    if 'episode_number' in info:
                                        rec_episode['Number'] = info['episode_number']
                                    if 'episode_title' in info:
                                        rec_episode['Name'] = info['episode_title']
                                    if 'guid' in info:
                                        rec_episode['Rec_GUID'] = info['guid']
                                    if 'recstart' in info:
                                        rec_episode['Start'] = timeStamp(stringToDate(info['recstart'].replace('T', ' ').replace('Z', '').replace('0001', '2019'), '%Y-%m-%d %H:%M:%S'))
                                    if 'recend' in info:
                                        rec_episode['Stop'] = timeStamp(stringToDate(info['recend'].replace('T', ' ').replace('Z', '').replace('0001', '2096'), '%Y-%m-%d %H:%M:%S'))
                                    if 'recstart' in info and 'recend' in info:
                                        rec_episode['Duration'] = rec_episode['Stop'] - rec_episode['Start']
                                    if 'playable' in info:
                                        if info['playable'] == True:
                                            rec_episode['Mode'] = 'play'

                                            response = requests.get(rec_episode['Asset_URL'], headers=HEADERS, verify=VERIFY)
                                            if response.status_code == 200:
                                                response = response.json()
                                                if 'metadata' in response:
                                                    if 'description' in response['metadata']:
                                                        rec_episode['Description'] = response['metadata']['description']
                                                    if 'genre' in response['metadata']:
                                                        genres = ''
                                                    for genre in response['metadata']['genre']:
                                                        genres = '%s, %s' % (genres, genre) if len(genres) > 0 else genre
                                                    rec_episode['Genre'] = genres
                                rec_episode['infoLabels'] = {
                                    'title': 'S%sE%s - %s' % (str(rec_episode['Season']).zfill(2), str(rec_episode['Number']).zfill(2), rec_episode['Name']),
                                    'plot': '[B]%s[/B][CR][CR]%s' % (rec_episode['Show_Name'], rec_episode['Description']),
                                    'genre': rec_episode['Genre'],
                                    'duration': rec_episode['Duration'],
                                    'mediatype': 'Video',
                                    'mpaa': rec_episode['Rating'],
                                }
                                rec_episode['infoArt'] = {
                                    'thumb': rec_episode['Thumbnail'],
                                    'logo': rec_episode['Thumbnail'],
                                    'clearlogo': rec_episode['Thumbnail'],
                                    'poster': rec_episode['Poster'],
                                    'fanart': rec_episode['Poster']
                                }
                                if rec_episode['Mode'] == 'play':
                                    log(json.dumps(rec_episode, indent=4))
                                    properties = {}
                                    if rec_episode['Duration'] != 0:
                                        properties['totaltime'] = rec_episode['Duration']
                                    context_items = []
                                    if rec_episode['Show_GUID'] != '':
                                        context_items.append(('View Show', 'Container.Update(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                            'name=%s)' % (rec_episode['Show_GUID'], rec_episode['Show_Name'])))
                                    context_items.append(('Delete Recording', 'RunPlugin(%s?mode=del_record&guid=%s&asset_url=%s)' %
                                                        (ADDON_URL, rec_episode['Rec_GUID'], rec_episode['Asset_URL'])))
                                    if rec_episode['Channel_GUID'] != '':
                                        rec_episode['Playlist_URL'] += '?channel=%s' % rec_episode['Channel_GUID']
                                    addLink(rec_episode['Name'], self.handleID, rec_episode['Playlist_URL'], rec_episode['Mode'],
                                            rec_episode['infoLabels'], rec_episode['infoArt'], 1, context_items, properties)


# ======================== My TV Asset Initialization ========================
def initAsset(self, asset):
    log('initAsset(): Initializing asset object')
    timestamp = int(time.time())

    asset = {
        'Name': '',
        'GUID': '',
        'Channel_GUID': '',
        'Channel_Name': '',
        'Show_GUID': '',
        'Show_Name': '',
        'Episode': '',
        'Season': '',
        'Thumbnail': ICON,
        'Poster': ICON,
        'Description': '',
        'Genre': '',
        'Rating': '',
        'Duration': 0,
        'Year': '',
        'Start': timestamp,
        'Stop': timestamp,
        'Resume': 0,
        'Resume_Percent': 0,
        'URL': '',
        'Playlist_URL': '',
        'Type': '',
        'Mode': 'info',
        'infoLabels': {
            'title': '',
            'plot': '',
            'genre': '',
            'duration': '',
            'mpaa': '',
            'year': '',
            'mediatype': 'Video'
        },
        'infoArt': {
            'thumb': ICON,
            'logo': ICON,
            'clearlogo': ICON,
            'poster': ICON,
            'fanart': ICON
        }
    }

    return asset

# ======================== My TV JSON Scraper ========================
def myTVJSON(self, mytv, asset):
    log('myTVJSON(): Processing My TV JSON')

    if 'actions' in mytv:
        if 'ASSET_IVIEW' in mytv['actions']:
            if 'url' in mytv['actions']['ASSET_IVIEW']:
                asset['URL'] = mytv['actions']['ASSET_IVIEW']['url']
                #http://cbd46b77.cms.movetv.com/cms/publish3/asset/info/74ba545e1ffa4ad1bba356f90de9fb70.json
                asset['GUID'] = asset['URL'].split('/')[len(asset['URL'].split('/')) - 1].split('.')[0]
                asset['Type'] = 'Asset'
        if 'CHANNEL_GUIDE_VIEW' in mytv['actions']:
            if 'id' in mytv['actions']['CHANNEL_GUIDE_VIEW']:
                asset['GUID'] = mytv['actions']['CHANNEL_GUIDE_VIEW']['id']
                asset['URL'] = "%s/cms/publish3/channel/schedule/%s.json" % (self.endPoints['cms_url'], asset['GUID'])
                asset['Type'] = 'Channel'
        if 'FRANCHISE_IVIEW' in mytv['actions']:
            if 'url' in mytv['actions']['FRANCHISE_IVIEW']:
                asset['URL'] = mytv['actions']['FRANCHISE_IVIEW']['url']
                #http://cbd46b77.cms.movetv.com/cms/api/franchises/314d78966a93419ab51e4b953047c933/expand=true;playable=false
                asset['GUID'] = asset['URL'].split('/')[len(asset['URL'].split('/')) - 2]
                asset['Type'] = 'Show'
        if 'FRANCHISE_RECORDING_IVIEW' in mytv['actions']:
            if 'url' in mytv['actions']['FRANCHISE_RECORDING_IVIEW']:
                franchise = mytv['actions']['FRANCHISE_RECORDING_IVIEW']
                asset['URL'] = franchise['url']
                #https://p-cmwnext.movetv.com/rec/v4/user-franchise-recordings
                if 'payload' in franchise:
                    asset['GUID'] = franchise['payload']['franchise']
                asset['Type'] = 'Show'
        if 'ASSET_RECORDING_IVIEW' in mytv['actions']:
            if 'url' in mytv['actions']['ASSET_RECORDING_IVIEW']:
                asset['URL'] = mytv['actions']['ASSET_RECORDING_IVIEW']['url']
                asset['GUID'] = asset['URL'].split('/')[len(asset['URL'].split('/')) - 1].split('.')[0]
                asset['Type'] = 'Recording'
        if 'PLAY_CONTENT' in mytv['actions']:
            action = mytv['actions']['PLAY_CONTENT']
            if 'playback_info' in action:
                playback_info = action['playback_info']
                if 'channel_guid' in playback_info:
                    asset['Channel_GUID'] = playback_info['channel_guid']
                if 'playback_bindles' in playback_info:
                    for bindle in playback_info['playback_bindles']:
                        if bindle['display_value'] == 'RESUME':
                            asset['Resume'] = bindle['position']
                if 'url' in playback_info:
                    asset['Playlist_URL'] = playback_info['url']
                    asset['Mode'] = 'play'
    if 'attributes' in mytv:
        for attribute in mytv['attributes']:
            if 'type' in attribute:
                if attribute['type'] == 'DURATION':
                    asset['Duration'] = attribute['dur_value']
    if 'channel_name' in mytv:
        asset['Channel_Name'] = mytv['channel_name']
    if 'image' in mytv:
        if 'url' in mytv['image']:
            asset['Thumbnail'] = mytv['image']['url']
    if 'title' in mytv:
        asset['Name'] = mytv['title']
    if 'bar' in mytv:
        if 'start_percent' in mytv['bar']:
            asset['Resume_Percent'] = mytv['bar']['start_percent']
        if 'scheduled_start_time' in mytv['bar']:
            asset['Start'] = mytv['bar']['scheduled_start_time']
        if 'scheduled_stop_time' in mytv['bar']:
            asset['Stop'] = mytv['bar']['scheduled_stop_time']
    
    return asset

# ======================== Asset JSON File Scraper ========================
def assetJSON(self, myjson, asset):
    log('assetJSON():  Processing Asset JSON')

    timestamp = int(time.time())
    if asset['Duration'] == 0 and 'duration' in myjson:
        asset['Duration'] = myjson['duration']
    if 'schedules' in myjson:
        for schedule in myjson['schedules']:
            if 'schedule_guid' in schedule:
                if schedule['schedule_guid'] == asset['GUID'] or ('channel_guid' in schedule and schedule['channel_guid'] == asset['Channel_GUID']) or \
                        ('channel_title' in schedule and schedule['channel_title'].upper() == asset['Channel_Name'].upper()) or \
                        len(myjson['schedules']) == 1 or subscribedChannel(self, schedule['channel_guid']):
                    if 'playback_info' in schedule:
                        if asset['Playlist_URL'] == '' and schedule['playback_info'] != '':
                            asset['Playlist_URL'] = schedule['playback_info']
                            asset['Mode'] = 'play'
                    if 'schedule_start' in schedule and 'schedule_end' in schedule:
                        asset['Start'] = timeStamp(stringToDate(schedule['schedule_start'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                                                '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))
                        asset['Stop'] = timeStamp(stringToDate(schedule['schedule_end'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                                               '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))
    if 'program' in myjson:
        program = myjson['program']
        if 'franchise_guid' in program:
            asset['Show_GUID'] = program['franchise_guid']
            if 'title' in myjson:
                asset['Show_Name'] = myjson['title']
        if asset['Type'] == 'Asset' and asset['Show_GUID'] != '' and 'guid' in program:
            asset['GUID'] = program['guid']
        if 'background_image' in program:
            if 'url' in program['background_image']:
                if asset['Poster'] == ICON and program['background_image']['url'] is not None:
                    asset['Poster'] = program['background_image']['url']
        if 'description' in program:
            if program['description'] != '':
                asset['Description'] = program['description']
        if 'episode_season' in program:
            asset['Season'] = program['episode_season']
            if 'episode_number' in program:
                asset['Episode'] = program['episode_number']
            elif 'guid' in program:
                asset['Episode'] = program['guid']
        if 'genre' in program:
            genres = ''
            for genre in program['genre']:
                genres = '%s, %s' % (genres, genre.capitalize(
                )) if genres != '' else genre.capitalize()
            asset['Genre'] = genres
        if 'ratings' in program:
            ratings = ''
            for rating in program['ratings']:
                ratings = '%s, %s' % (ratings, rating.replace(
                    '_', ' ')) if ratings != '' else rating.replace('_', ' ')
            asset['Rating'] = ratings
    if 'metadata' in myjson:
        metadata = myjson['metadata']
        if 'description' in metadata:
            if metadata['description'] != '':
                asset['Description'] = metadata['description']
        if 'release_year' in metadata:
            asset['Year'] = metadata['release_year']
        if 'genre' in metadata:
            genres = ''
            if metadata['genre'] is not None:
                for genre in metadata['genre']:
                    genres = '%s, %s' % (genres, genre.capitalize()) if genres != '' else genre.capitalize()
            asset['Genre'] = genres
        if 'ratings' in metadata:
            ratings = ''
            if metadata['ratings'] is not None:
                for rating in metadata['ratings']:
                    ratings = '%s, %s' % (ratings, rating.replace('_', ' ')) if ratings != '' else rating.replace('_', ' ')
            asset['Rating'] = ratings
    if 'entitlements' in myjson and asset['Playlist_URL'] == '':
        for entitlement in myjson['entitlements']:
            if 'playback_start' in entitlement:
                if asset['Start'] == asset['Stop']:
                    start = timeStamp(stringToDate(entitlement['playback_start'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                                            '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))
                    stop = timeStamp(stringToDate(entitlement['playback_stop'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                                           '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))    
                    if start <= timestamp <= stop:
                        if 'qvt_url' in entitlement:
                            asset['Start'] = start
                            asset['Stop'] = stop
                            asset['Playlist_URL'] = entitlement['qvt_url']
                            asset['Mode'] = 'play'
                            break
                        
    if asset['Type'] == 'Asset' or asset['Type'] == 'Channel':
        if asset['Start'] != asset['Stop']:
            asset['Description'] += '[CR][CR]Start: %s[CR]Stop: %s' % \
                (datetime.datetime.fromtimestamp(asset['Start']).strftime('%m/%d/%Y %H:%M:%S'),
                datetime.datetime.fromtimestamp(asset['Stop']).strftime('%m/%d/%Y %H:%M:%S'))
        
        if asset['Stop'] < asset['Start'] + asset['Duration'] + 3600:
            if asset['Start'] > timestamp:
                name = '[COLOR=yellow]Upcomming[/COLOR] %s' % asset['Name']
                asset['Mode'] = 'info'
            elif asset['Start'] <= timestamp <= asset['Stop'] and (asset['Start'] != asset['Stop']):
                name = '[COLOR=green]Live[/COLOR] %s' % asset['Name']
            else:
                name = '[COLOR=gray]Replay[/COLOR] %s' % asset['Name']
            
            asset['infoLabels']['title'] = name

    return asset

# ======================== Asset Info Updater ========================
def assetInfo(self, asset):
    log('assetInfo(): Setting asset infoLabels/infoArt')

    if asset['infoLabels']['title'] == '':
        asset['infoLabels']['title'] = asset['Name']
    asset['infoLabels']['plot'] = asset['Description']
    asset['infoLabels']['genre'] = asset['Genre']
    asset['infoLabels']['duration'] = asset['Duration']
    asset['infoLabels']['mpaa'] = asset['Rating']
    asset['infoLabels']['year'] = asset['Year']
    asset['infoLabels']['mediatype'] = 'Video'
    
    
    asset['infoArt']['thumb'] = asset['Thumbnail']
    asset['infoArt']['logo'] = asset['Thumbnail']
    asset['infoArt']['clearlogo'] = asset['Thumbnail']
    asset['infoArt']['poster'] = asset['Thumbnail']
    asset['infoArt']['fanart'] = asset['Poster']

    return asset
