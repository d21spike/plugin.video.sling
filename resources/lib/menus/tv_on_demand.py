from resources.lib.globals import *

# ==================================================================================================================
#
# TV On Demand Menu
#
# ==================================================================================================================

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


def tvOnDemand(self):
    log('TV On Demand Menu')
    infoLabels = {'title': '', 'plot': '', 'genre': '',
                  'duration': '', 'mediatype': 'Video', 'mpaa': ''}
    infoArt = {'thumb': ICON, 'logo': ICON,
               'clearlogo': ICON, 'poster': ICON, 'fanart': FANART}

    context = 'my_tv_tvod'
    debug = dict(urlParse.parse_qsl(DEBUG_CODE))
    log('Debug Code: %s' % json.dumps(debug, indent=4))
    if 'rental' in debug:
        if debug['rental'] == 'True':
            context = 'my_tv_tvod'

    tvod_url = '%s/pg/v1/%s?dma=%s&timezone=%s' % (self.endPoints['cmwnext_url'], context, USER_DMA, USER_OFFSET)
    log('TV On Demand URL: %s' % tvod_url)
    response = requests.get(tvod_url, headers=TVOD_HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        # log(json.dumps(response, indent=4))
        if 'ribbons' in response:
            for ribbon in response['ribbons']:
                log('My TV On Demand Ribbon: %s with %i tiles' % (ribbon['title'], int(ribbon['total_tiles'])))
                if int(ribbon['total_tiles']) > 0:
                    infoLabels['title'] = ribbon['title']
                    addDir(ribbon['title'], self.handleID, ribbon['href'], 'tvod', infoLabels, infoArt)


def tvodRibbon(self):
    log('TV On Demand Ribbon')

    name = self.params['name']
    if name == 'My Channels':
        tvodMyChannels(self)
    elif name == 'Recordings':
        tvodRecordings(self)
    elif name == 'Continue Watching':
        tvodContinueWatching(self)
    elif name == 'Favorites':
        tvodFavorites(self)
    else:
        log('TBD')


def tvodMyChannels(self):
    log('TV On Demand My Channels')

    response = requests.get(self.params['url'], headers=TVOD_HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'tiles' in response:
            for tile in response['tiles']:
                channel_guid = ''
                if 'analytics' in tile:
                    if 'item_id' in tile['analytics']:
                        channel_guid = tile['analytics']['item_id']
                else:
                    if 'invalidation_keys' in tile:
                        if len(tile['invalidation_keys']) > 0:
                            channel_guid = tile['invalidation_keys'][0]
                if channel_guid != '':
                    tvod_channel = Channel(channel_guid, self.endPoints, self.db)


def tvodRecordings(self):
    log('TV On Demand Recordings')
    tvod_url = '%s/pg/v1/%s?dma=%s&timezone=%s' % (self.endPoints['cmwnext_url'], 'my_tv_tvod', USER_DMA, USER_OFFSET)
    log('TV On Demand URL: %s' % tvod_url)
    response = requests.get(tvod_url, headers=TVOD_HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'ribbons' in response:
            for ribbon in response['ribbons']:
                if 'title' in ribbon and ribbon['title'] == 'Recordings':
                    for tile in ribbon['tiles']:
                        if 'primary_action' in tile and tile['primary_action'] == 'ASSET_RECORDING_IVIEW':
                            airing_url = tile['actions']['ASSET_RECORDING_IVIEW']['url']
                            response = requests.get(airing_url, headers=HEADERS, verify=VERIFY)
                            if response is not None and response.status_code == 200:
                                response = response.json()
                                if 'program' in response:
                                    show_guid = response['program']['franchise_guid']
                                    show = Show(show_guid, self.endPoints, self.db)
                                    show.getSeasons()

                                    if 'start_time' in tile:
                                        start = timeStamp(stringToDate(
                                            tile['start_time'].replace('T', ' ').replace('Z', '').replace('0001',
                                                                                                          '2019'),
                                            '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))
                                        stop = timeStamp(stringToDate(
                                            tile['stop_time'].replace('T', ' ').replace('Z', '').replace('0001',
                                                                                                         '2019'),
                                            '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))
                                    elif len(show.Seasons) == 1:
                                        start = show.Seasons[0]['Episodes'][response['program']['guid']]['Start']
                                        stop = show.Seasons[0]['Episodes'][response['program']['guid']]['Stop']
                                    elif len(show.Seasons) > 1:
                                        if 'season_number' not in tile:
                                            tile['season_number'] = 0
                                        if 'episode_number' not in tile:
                                            tile['episode_number'] = response['program']['guid']

                                        episode = show.Seasons[tile['season_number']]['Episodes'][
                                            tile['episode_number']]
                                        start = episode['Start']
                                        stop = episode['Stop']
                                    asset = {
                                        'Name': tile['title'],
                                        'Thumbnail': tile['image']['url'] or show.Thumbnail,
                                        'Poster': response['program']['background_image']['url'] or show.Poster,
                                        'Description': response['program']['description'] if 'description' in response[
                                            'program'] else show.Description,
                                        'Rating': tile['ratings'][0].replace('_', ' ') if 'ratings' in tile else '',
                                        'Year': tile['release_year'] if 'release_year' in tile else '',
                                        'Start': start,
                                        'Stop': stop,
                                        'Playlist_URL': tile['actions']['PLAY_CONTENT']['playback_info']['url'],
                                        'Mode': 'play'
                                    }
                                    asset['Description'] += '[CR][CR]Start: %s[CR]Stop: %s' % \
                                                            (datetime.datetime.fromtimestamp(start).strftime(
                                                                '%m/%d/%Y %H:%M:%S'),
                                                             datetime.datetime.fromtimestamp(stop).strftime(
                                                                 '%m/%d/%Y %H:%M:%S'))
                                    for attribute in tile['attributes']:
                                        if attribute['type'] == 'DURATION':
                                            asset['Duration'] = str(attribute['dur_value'])
                                            break
                                    # if tile['availability_type'] != 'svod':
                                    #     if start > timestamp:
                                    #         asset['Mode'] = 'info'
                                    #         name = '[COLOR=yellow]Upcomming[/COLOR] %s' % asset['Name']
                                    #
                                    #     elif start <= timestamp <= stop:
                                    #         name = '[COLOR=green]Live[/COLOR] %s' % asset['Name']
                                    #     else:
                                    #         name = '[COLOR=gray]Replay[/COLOR] %s' % asset['Name']
                                    # else:
                                    #     if asset['Year'] != '':
                                    #         name = '%s (%i)' % (asset['Name'], asset['Year'])
                                    #     else:
                                    #         name = asset['Name']
                                    name = asset['Name']
                                    asset['infoLabels'] = {
                                        'title': name,
                                        'plot': asset['Description'],
                                        'genre': 'Program',
                                        'duration': asset['Duration'],
                                        'mpaa': asset['Rating'],
                                        'year': asset['Year'],
                                        'mediatype': 'Video'
                                    }
                                    asset['infoArt'] = {
                                        'thumb': asset['Thumbnail'],
                                        'logo': asset['Thumbnail'],
                                        'clearlogo': asset['Thumbnail'],
                                        'poster': asset['Thumbnail'],
                                        'fanart': asset['Poster']
                                    }

                                    properties = None
                                    if tile['actions']['PLAY_CONTENT']['playback_info']['playback_bindles'] > 1:
                                        resume_time = None
                                        for playback in tile['actions']['PLAY_CONTENT']['playback_info'][
                                            'playback_bindles']:
                                            log('Playback: %s' % str(playback))
                                            if playback['display_value'] == 'RESUME':
                                                resume_time = str(playback['position'])
                                                break
                                        log('Resume Time: %s' % resume_time)
                                        properties = {
                                            'totaltime': asset['Duration'],
                                            'resumetime': resume_time
                                        }

                                    context_items = []
                                    if show.GUID != '':
                                        context_items = [
                                            ('View Show', 'Container.Update(plugin://plugin.video.sling/?'
                                                          'mode=show&guid=%s&name=%s)' % (show.GUID, show.Name))
                                        ]
                                    addLink(name, self.handleID, asset['Playlist_URL'], asset['Mode'],
                                            asset['infoLabels'], asset['infoArt'], 1, context_items, properties)


def tvodContinueWatching(self):
    log('TV On Demand Continue Watching')


def tvodFavorites(self):
    log('TV On Demand Favorites')

    response = requests.get(
        self.params['url'], headers=TVOD_HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'tiles' in response:
            for tile in response['tiles']:
                show_guid = ''
                if 'analytics' in tile:
                    if 'item_id' in tile['analytics']:
                        show_guid = tile['analytics']['item_id']
                else:
                    if 'invalidation_keys' in tile:
                        if len(tile['invalidation_keys']) > 0:
                            show_guid = tile['invalidation_keys'][0]
                if show_guid != '':
                    tvod_show = Show(show_guid, self.endPoints, self.db)
                    addDir(tvod_show.Name, self.handleID, '', 'show&guid=%s' % tvod_show.GUID, tvod_show.infoLabels(),
                           tvod_show.infoArt())
