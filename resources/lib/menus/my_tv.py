from resources.lib.globals import *

# ==================================================================================================================
#
# On Now Menu
#
# ==================================================================================================================


def myTV(self):
    log('My TV Menu')
    infoLabels = {'title': '', 'plot': '', 'genre': '', 'duration': '', 'mediatype': 'Video', 'mpaa': ''}
    infoArt = {'thumb': ICON, 'logo': ICON, 'clearlogo': ICON, 'poster': ICON, 'fanart': FANART}

    context = 'my_tv'
    debug = dict(urlParse.parse_qsl(DEBUG_CODE))
    log('Debug Code: %s' % json.dumps(debug, indent=4))
    if 'rental' in debug:
        if debug['rental'] == 'True':
            context = 'my_tv_tvod'



    for ribbon_id in range(1, 17):
        ribbon_url = 'https://p-mgcs.movetv.com/rubens-online/rest/v1/dma/%s/offset/%s/domain/1/product/sling/' \
                     'platform/browser/context/%s/ribbons/AR%i?sub_pack_ids=%s' % \
                     (USER_DMA, USER_OFFSET, context, ribbon_id, USER_SUBS)
        log('Ribbon URL: %s' % ribbon_url)
        response = requests.get(ribbon_url, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            response = response.json()
            if 'tiles' in response:
                if response['total_tiles'] > 0:
                    infoLabels['title'] = response['title']
                    addDir(response['title'], self.handleID, ribbon_url, 'my_tv', infoLabels, infoArt)
    

def myTVRibbon(self):
    log('My TV Ribbon Menu')
    timestamp = int(time.time())

    response = requests.get(self.params['url'], headers=HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'tiles' in response:
            if response['total_tiles'] > 0:
                for tile in response['tiles']:
                    added = False
                    if tile['type'] == 'show' or tile['type'] == 'series':
                        airing_url = tile['_href']
                        response = requests.get(airing_url, headers=HEADERS, verify=VERIFY)
                        if response is not None and response.status_code == 200:
                            response = response.json()
                            if 'program' in response:
                                show_guid = response['program']['franchise_guid']
                                show = Show(show_guid, self.endPoints, self.db)
                                show.getSeasons()

                                if 'start_time' in tile:
                                    start = timeStamp(stringToDate(tile['start_time'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                                                   '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))
                                    stop = timeStamp(stringToDate(tile['stop_time'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                                                   '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone('UTC')))
                                elif len(show.Seasons) == 1:
                                    start = show.Seasons[0]['Episodes'][response['program']['guid']]['Start']
                                    stop = show.Seasons[0]['Episodes'][response['program']['guid']]['Stop']
                                elif len(show.Seasons) > 1:
                                    # log(json.dumps(response, indent=4))
                                    # log(json.dumps(tile, indent=4))
                                    if 'season_number' not in tile:
                                        tile['season_number'] = 0
                                    if 'episode_number' not in tile:
                                        tile['episode_number'] = response['program']['guid']
                                    
                                    episode = show.Seasons[tile['season_number']]['Episodes'][tile['episode_number']]
                                    start = episode['Start']
                                    stop = episode['Stop']
                                asset = {
                                    'Name': tile['title'],
                                    'Thumbnail': tile['thumbnail']['url'] or show.Thumbnail,
                                    'Poster': response['program']['background_image']['url'] or show.Poster,
                                    'Description': response['program']['description'] if 'description' in response['program'] else show.Description,
                                    'Rating': tile['ratings'][0].replace('_', ' ') if 'ratings' in tile else '',
                                    'Duration': tile['duration'],
                                    'Year': tile['release_year'] if 'release_year' in tile else '',
                                    'Start': start,
                                    'Stop': stop,
                                    'Playlist_URL': tile['qvt'],
                                    'Mode': 'play'
                                }
                                asset['Description'] += '\n\nStart: %s\nStop: %s' % \
                                                        (datetime.datetime.fromtimestamp(start).strftime('%m/%d/%Y %H:%M:%S'),
                                                         datetime.datetime.fromtimestamp(stop).strftime('%m/%d/%Y %H:%M:%S'))
                                if tile['availability_type'] != 'svod':
                                    if start > timestamp:
                                        asset['Mode'] = 'info'
                                        name = '[COLOR=yellow]Upcomming[/COLOR] %s' % asset['Name']

                                    elif start <= timestamp <= stop:
                                        name = '[COLOR=green]Live[/COLOR] %s' % asset['Name']
                                    else:
                                        name = '[COLOR=gray]Replay[/COLOR] %s' % asset['Name']
                                else:
                                    if asset['Year'] != '':
                                        name = '%s (%i)' % (asset['Name'], asset['Year'])
                                    else:
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

                                context_items = []
                                if show.GUID != '':
                                    context_items = [
                                        ('View Show', 'Container.Update(plugin://plugin.video.sling/?'
                                                           'mode=show&guid=%s&name=%s)' % (show.GUID, show.Name))
                                    ]
                                addLink(name, self.handleID, asset['Playlist_URL'], asset['Mode'],
                                        asset['infoLabels'], asset['infoArt'], 1, context_items)
                                added = True
                            elif 'seasons' in response:
                                show_guid = response['guid']
                                show = Show(show_guid, self.endPoints, self.db)
                                # show.getSeasons()
                                if show.Name != "":
                                    context_items = [
                                        ('Add to Favorite Shows', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                                  'action=favorite)' % show.GUID),
                                        ('Update Show', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                        'action=update)' % show.GUID)
                                    ]
                                    addDir(show.Name, self.handleID, '', 'show&guid=%s' % show.GUID, show.infoLabels(),
                                           show.infoArt(), context_items)
                                    added = True
                    elif tile['type'] == 'movie' or tile['type'] == 'episode':
                        log(json.dumps(tile, indent=4))
                        asset_url = tile['_href']
                        response = requests.get(asset_url, headers=HEADERS, verify=VERIFY)
                        if response is not None and response.status_code == 200:
                            response = response.json()
                            if 'channel' in tile:
                                guid = tile['channel']['guid']
                            else:
                                guid = tile['external_id']
                            channel = Channel(guid, self.endPoints, self.db)
                            found, asset = channel.getVODAsset(response['external_id'])
                            if not found:
                                found, asset = channel.processVODAsset(response)
                            if found:
                                if len(asset):
                                    if asset['Start'] <= timestamp <= asset['Stop']:
                                        name = asset['Name']
                                        infoLabels = asset['infoLabels']
                                        if asset['Type'] == 'movie' or asset['Type'] == 'rental' or asset['Type'] == 'fod':
                                            name = '%s (%i)' % (name, asset['Year'])
                                            infoLabels['title'] = name
                                        addLink(name, self.handleID, asset['Playlist_URL'], 'play',
                                                infoLabels, asset['infoArt'])
                                added = True
                    if not added and tile['type'] != 'series':
                        start = 0
                        stop = 0
                        if 'start_time' in tile:
                            start = timeStamp(stringToDate(tile['start_time'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
                            stop = timeStamp(stringToDate(tile['stop_time'].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S'))
                        genre = ''
                        if 'genre' in tile:
                            for new_genre in tile['genre']:
                                genre += '%s, %s' % (genre, new_genre) if len(genre) > 0 else new_genre
                        thumbnail = ''
                        if 'thumbnail' in tile:
                            thumbnail = tile['thumbnail']['url']
                        duration = 0
                        if 'duration' in tile:
                            duration = tile['duration']
                        channel_logo = ''
                        if 'channel' in tile:
                            if 'image' in tile['channel']:
                                channel_logo = tile['channel']['image']['url']
                        playlist = ''
                        if 'qvt' in tile:
                            playlist = tile['qvt']
                        infoLabels = {'title': tile['title'], 'duration': duration, 'genre': genre}
                        infoArt = {'thumb': thumbnail, 'logo': thumbnail, 'clearlogo': thumbnail,
                                   'poster': thumbnail, 'fanart': channel_logo}
                        if start <= timestamp <= stop or start == stop:
                            addLink(tile['title'], self.handleID, playlist, 'play',
                                    infoLabels, infoArt)
