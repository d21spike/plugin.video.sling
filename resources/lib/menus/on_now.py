from resources.lib.globals import *

# ==================================================================================================================
#
# On Now Menu
#
# ==================================================================================================================


def onNow(self):
    log('On Now Menu')
    context = "on_now"
    on_now_url = "https://p-mgcs.movetv.com/rubens-online/rest/v1/dma/%s/offset/%s/domain/1/product/sling/" \
                 "platform/browser/context/%s/ribbons?sub_pack_ids=%s" % \
                 (USER_DMA, USER_OFFSET, context, USER_SUBS)
    log('On Now URL => %s' % on_now_url)
    response = requests.get(on_now_url, headers=HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'ribbons' in response:
            session = createResilientSession()
            for ribbon in response['ribbons']:
                if ribbon['total_tiles'] > 0:
                    infoLabels = {
                        'title': ribbon['title'], 'plot': '', 'genre': 'On Now', 'duration': 0, 'mediatype': 'Video', 'mpaa': ''
                    }
                    infoArt = {
                        'thumb': ICON, 'logo': ICON, 'clearlogo': ICON, 'poster': ICON, 'fanart': FANART
                    }
                    ribbon_url = ribbon['_href']
                    response = session.get(ribbon_url, headers=HEADERS, verify=VERIFY)
                    if response.status_code == 200:
                        response = response.json()
                        if 'tiles' in response:
                            if response['tiles'] is not None:
                                if len(response['tiles']) > 0:
                                    addDir(ribbon['title'], self.handleID, ribbon['_href'], 'on_now', infoLabels,
                                           infoArt)
            session.close()


def onNowRibbon(self):
    log('On Now Ribbon Menu')
    timestamp = int(time.time())
    ribbon_url = self.params['url']
    log('On Now Ribbon URL => %s' % ribbon_url)
    response = requests.get(ribbon_url, headers=HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'tiles' in response:
            for tile in response['tiles']:
                if 'channel' in tile:
                    channel = Channel(tile['channel']['guid'], self.endPoints, self.DB)
                    if len(channel.On_Now) == 0 or channel.On_Now['Stop'] < timestamp:
                        result, on_now = channel.onNow()
                        if result: channel.On_Now = on_now
                    infoArt = channel.infoArt()
                    if channel.On_Now != {} and channel.On_Now['Stop'] >= timestamp:
                        infoArt['thumb'] = channel.On_Now['Thumbnail']
                        infoArt['poster'] = channel.On_Now['Poster']
                    if channel.infoLabels()['duration'] > 0 and 'OFF-AIR' not in \
                            channel.infoLabels()['plot']:
                        context_items = []
                        if channel.On_Demand:
                            context_items = [
                                ('View On Demand', 'Container.Update(plugin://plugin.video.sling/?'
                                                   'mode=demand&guid=%s&name=%s)' % (channel.GUID, channel.Name))
                            ]
                        addLink(channel.Name, self.handleID, channel.Qvt_Url, 'play',
                                channel.infoLabels(), infoArt, channel.ID, context_items)
                    elif channel.infoLabels()['duration'] == 0:
                        context_items = [
                            ('Update On Demand Content', 'RunPlugin(plugin://plugin.video.sling/?mode=demand&guid=%s&'
                                                         'action=update)' % channel.GUID)
                        ]
                        addDir(channel.Name, self.handleID, '', 'demand&guid=%s' % channel.GUID,
                               channel.infoLabels(), channel.infoArt(), context_items)
