from resources.lib.globals import *

# ==================================================================================================================
#
# TV On Demand Menu
#
# ==================================================================================================================


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
    headers = {
        'Origin': 'https://watch.sling.com',
        'User-Agent': USER_AGENT,
        'Accept': '*/*',
        'Referer': 'https://watch.sling.com/browse/my-tv',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Authorization': 'Bearer %s' % ACCESS_TOKEN_JWT,
        'Sling-Interaction-ID': DEVICE_ID
    }
    response = requests.get(tvod_url, headers=headers, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        # log(json.dumps(response, indent=4))
        if 'ribbons' in response:
            for ribbon in response['ribbons']:
                log('My TV On Demand Ribbon: %s with %i tiles' % (ribbon['title'], int(ribbon['total_tiles'])))
                if int(ribbon['total_tiles']) > 0:
                    infoLabels['title'] = ribbon['title']
                    addDir(ribbon['title'], self.handleID, ribbon['href'], 'tvod', infoLabels, infoArt)
        
