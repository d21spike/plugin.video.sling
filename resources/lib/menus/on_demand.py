from resources.lib.globals import *
from resources.lib.menus.channels import *

# ==================================================================================================================
#
# On Demand Menu
#
# ==================================================================================================================


def onDemand(self):
    log('On Demand Menu')
    if len(self.Channels) == 0:
        getChannels(self)

    for guid in self.Channels:
        if self.Channels[guid].On_Demand and not self.Channels[guid].Hidden:
            infoLabels = self.Channels[guid].infoLabels()
            infoLabels['plot'] = ''
            infoLabels['genre'] = ''
            infoLabels['duration'] = 0
            infoLabels['mpaa'] = ''
            context_items = [
                ('Update On Demand Content', 'RunPlugin(plugin://plugin.video.sling/?mode=demand&guid=%s&'
                                             'action=update)' % guid)
            ]
            addDir(self.Channels[guid].Name, self.handleID, '', 'demand&guid=%s' % guid, infoLabels,
                   self.Channels[guid].infoArt(), context_items)
    

def onDemandChannel(self):
    if len(self.Channels) == 0:
        getChannels(self)

    if self.params['guid'] not in self.Channels:
        new_channel = Channel(self.params['guid'], self.endPoints, self.DB)
        self.Channels[self.params['guid']] = new_channel

    log('On Demand Channel %s Menu' % self.name)
    channel = self.Channels[self.params['guid']]
    infoLabels = channel.infoLabels()
    infoLabels['plot'] = ''
    infoLabels['genre'] = ''
    infoLabels['duration'] = 0
    infoLabels['mpaa'] = ''
    categories = channel.onDemandCategories()
    for category in categories:
        infoLabels['title'] = category['Name']
        addDir(category['Name'], self.handleID, '', 'demand&guid=%s&category=%s' %
               (self.params['guid'], binascii.hexlify(strip(category['Name']).encode()).decode()), infoLabels, channel.infoArt())
    

def onDemandChannelCategory(self):
    if len(self.Channels) == 0:
        getChannels(self)

    if self.params['guid'] not in self.Channels:
        new_channel = Channel(self.params['guid'], self.endPoints, self.DB)
        self.Channels[self.params['guid']] = new_channel

    channel = self.Channels[self.params['guid']]
    log('On Demand Channel %s, Category %s Menu' % (channel.Name, self.params['category']))
    assets = channel.getOnDemandAssets(self.params['category'])
    log(str(assets))
    timestamp = int(time.time())
    for asset in assets:
        title = ''
        mode = 'play'
        if asset['Type'] == 'svod' or asset['Type'] == 'vod' or asset['Type'] == 'live_event':
            if asset['Start'] <= timestamp <= asset['Start'] + asset['Duration']:
                title = '[COLOR=green]Live[/COLOR] - %s ' % asset['Name']
                mode = 'play'
            elif asset['Start'] > timestamp:
                title = '[COLOR=yellow]Upcoming[/COLOR] - %s' % asset['Name']
                mode = 'info'
            else:
                if asset['Stop'] > timestamp:
                    title = asset['Name']
                    mode = 'play'
                else:
                    title = '[COLOR=red]Ended[/COLOR] - %s' % asset['Name']
                    mode = 'info'
        elif asset['Type'] == 'linear':
            asset['Description'] += '[CR][CR]Start: %s[CR]Stop: %s' % \
                                    (datetime.datetime.fromtimestamp(asset['Start']).strftime('%m/%d/%Y %H:%M:%S'),
                                     datetime.datetime.fromtimestamp(asset['Stop']).strftime('%m/%d/%Y %H:%M:%S'))
            if asset['Start'] <= timestamp <= asset['Start'] + asset['Duration']:
                title = '[COLOR=green]Live[/COLOR] - %s' % asset['Name']
                mode = 'play'
            elif asset['Start'] > timestamp:
                title = '[COLOR=yellow]Upcoming[/COLOR] - %s' % asset['Name']
                mode = 'info'
            else:
                title = '[COLOR=gray]Replay[/COLOR] - %s' % asset['Name']
                mode = 'play'
        elif asset['Type'] == 'series':
            mode = 'show'
            title = asset['Name']

        infoLabels = {
            'title': title,
            'plot': asset['Description'],
            'genre': '',
            'duration': asset['Duration'],
            'mediatype': 'Video',
            'mpaa': asset['Rating']
        }
        infoArt = {
            'thumb': asset['Thumbnail'],
            'logo': asset['Thumbnail'],
            'clearlogo': asset['Thumbnail'],
            'poster': asset['Thumbnail'],
            'fanart': channel.Poster
        }
        if asset['Type'] == 'svod' or asset['Type'] == 'vod' or asset['Type'] == 'live_event':
            if asset['Release_Year'] > 0:
                infoLabels['genre'] = 'Movie'
                infoLabels['title'] += ' (%i)' % asset['Release_Year']
            else:
                infoLabels['genre'] = 'Live Program'
                stamp = datetime.datetime.fromtimestamp(asset['Start']).strftime('%m/%d/%Y')
                infoLabels['title'] = '%s - %s' % (stamp, infoLabels['title'])
            addLink(title, self.handleID, '%s?channel=%s' % (asset['Playlist_URL'], channel.GUID), mode, infoLabels, infoArt)
        elif asset['Type'] == 'linear':
            if asset['Release_Year'] > 0:
                infoLabels['genre'] = 'Movie'
                infoLabels['title'] += ' (%i)' % asset['Release_Year']
            else:
                infoLabels['genre'] = 'Live Program'
            addLink(title, self.handleID, '%s?channel=%s' % (asset['Playlist_URL'], channel.GUID), mode, infoLabels, infoArt)
        elif asset['Type'] == 'series':
            infoLabels['genre'] = 'Show'
            context_items = [
                ('Add to Favorite Shows', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                          'action=favorite)' % asset['Asset_GUID']),
                ('Update Show', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                'action=update)' % asset['Asset_GUID'])
            ]
            addDir(title, self.handleID, '', 'show&guid=%s' % asset['Asset_GUID'], infoLabels, infoArt, context_items)


def onDemandUpdate(self):
    updated = False
    channel = Channel(self.params['guid'], self.endPoints, self.DB)
    categories = channel.getOnDemandCategories()
    for category in categories:
        category_name = category['Name']
        assets = channel.getOnDemandAssets(category_name, True)
        if len(assets):
            updated = True
    if updated:
        notificationDialog('%s %s' % (LANGUAGE(30116), channel.Name))
    else:
        notificationDialog('%s %s' % (LANGUAGE(30117), channel.Name))
