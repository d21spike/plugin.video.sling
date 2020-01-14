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
                    addDir(tvod_show.Name, self.handleID, '', 'show&guid=%s' % tvod_show.GUID, tvod_show.infoLabels(), tvod_show.infoArt())
