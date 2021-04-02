from resources.lib.globals import *

# ==================================================================================================================
#
# Search Menu
#
# ==================================================================================================================


def search(self):

    query = inputDialog('Shows, Movies, etc ...')

    if query is not None:
        xbmc.executebuiltin('Container.Update(plugin://plugin.video.sling/?mode=search&query=%s)' % query)
    else:
        notificationDialog(LANGUAGE(30107))
        xbmc.executebuiltin('Action(Back)')


def executeSearch(self, query):
    log('Performing a search for %s' % query)
    gotResults = False
    if ACCESS_TOKEN_JWT != '':
        timestamp = int(time.time())
        search_url = '%s/pg/v1/search?timezone=%s&dma=%s&product=sling&platform=browser&search_term=%s' % \
                     (self.endPoints['cmwnext_url'], USER_OFFSET, USER_DMA, urlLib.quote_plus(query))
        log('Search URL => %s' % search_url)
        headers = {
            'Origin': 'https://watch.sling.com',
            'User-Agent': USER_AGENT,
            'Accept': '*/*',
            'Referer': 'https://watch.sling.com/search?query=%s' % query,
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Authorization': 'Bearer %s' % ACCESS_TOKEN_JWT,
            'Sling-Interaction-ID': DEVICE_ID
        }
        # log(json.dumps(headers, indent=4))
        response = requests.get(search_url, headers=headers, verify=VERIFY)
        log('%i - %s' % (response.status_code, response.text))
        if response is not None and response.status_code == 200:
            response = response.json()
            if 'ribbons' in response:
                ribbons = response['ribbons']
                for ribbon in ribbons:
                    if "SHOWS" in ribbon['title']:
                        for sling_show in ribbon['tiles']:
                            guid = sling_show['invalidation_keys'][0]
                            show = Show(guid, self.endPoints, self.DB)
                            if show.Name != '':
                                context_items = [
                                    ('Add to Favorite Shows', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                              'action=favorite)' % show.GUID),
                                    ('Update Show', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                    'action=update)' % show.GUID)
                                ]
                                addDir(show.Name, self.handleID, '', 'show&guid=%s' % guid, show.infoLabels(),
                                       show.infoArt(), context_items)
                                gotResults = True
                    elif "MOVIES" in ribbon['title']:
                        session = createResilientSession()
                        for sling_movie in ribbon['tiles']:
                            if 'actions' in sling_movie:
                                if 'PLAY_CONTENT' in sling_movie['actions']:
                                    playback_info = sling_movie['actions']['PLAY_CONTENT']['playback_info']
                                    if 'channel_guid' in playback_info:
                                        channel = Channel(playback_info['channel_guid'], self.endPoints, self.DB)
                                        movie_response = session.get(sling_movie['actions']['ASSET_IVIEW']['url'],
                                                                      headers=HEADERS, verify=VERIFY)
                                        if movie_response is not None:
                                            movie_json = movie_response.json()
                                            found, movie = channel.processVODAsset(movie_json)
                                            if found:
                                                if movie['Start'] <= timestamp <= movie['Stop']:
                                                    name = movie['Name']
                                                    infoLabels = movie['infoLabels']
                                                    if movie['Type'] == 'movie':
                                                        name = '%s (%i)' % (name, movie['Year'])
                                                        infoLabels['title'] = name
                                                    addLink(name, self.handleID, '%s?channel=%s' % (movie['Playlist_URL'], channel.GUID), 'play',
                                                            infoLabels, movie['infoArt'])
                                                    gotResults = True
                        session.close()
        if not gotResults:
            notificationDialog(LANGUAGE(30108))
            xbmc.executebuiltin('Action(Back)')
    else:
        notificationDialog(LANGUAGE(30109))
        xbmc.executebuiltin('Action(Back)')
