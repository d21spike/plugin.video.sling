from resources.lib.globals import *

# ==================================================================================================================
#
# My Favorites Menu
#
# ==================================================================================================================


def getFavorites(self):
    log(json.dumps(self.endPoints, indent=4))
    favorites_url = '%s/watchlists/v4/watches?product=sling&platform=browser' % self.endPoints['cmwnext_url']
    response = requests.get(favorites_url, headers=HEADERS, verify=VERIFY, auth=self.auth.getAuth())
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'favorites' in response:
            response = response['favorites']
            for favorite in response:
                if favorite['cmw_info']['type'] == 'channel':
                    self.Favorites[favorite['guid']] = Channel(favorite['guid'], self.endPoints, self.DB)


def myFavorites(self):
    log('My Favorites Menu')
    timestamp = int(time.time())
    if len(self.Favorites) == 0: getFavorites(self)

    for guid in self.Favorites:
        if len(self.Favorites[guid].On_Now) == 0 or self.Favorites[guid].On_Now['Stop'] < timestamp:
            result, on_now = self.Favorites[guid].onNow()
            if result: self.Favorites[guid].On_Now = on_now
        infoArt = self.Favorites[guid].infoArt()
        if len(self.Favorites[guid].On_Now) != 0 and self.Favorites[guid].On_Now['Stop'] >= timestamp:
            infoArt['thumb'] = self.Favorites[guid].On_Now['Thumbnail']
            infoArt['poster'] = self.Favorites[guid].On_Now['Poster']

        if self.Favorites[guid].infoLabels()['duration'] > 0 and 'OFF-AIR' not in \
                self.Favorites[guid].infoLabels()['plot'] and 'Channel Unavailable' not in \
                self.Favorites[guid].infoLabels()['plot']:
            context_items = []
            if self.Favorites[guid].On_Demand:
                context_items = [
                    ('View On Demand', 'Container.Update(plugin://plugin.video.sling/?'
                                       'mode=demand&guid=%s&name=%s)' % (guid, self.Favorites[guid].Name))
                ]
            addLink(self.Favorites[guid].Name, self.handleID, self.Favorites[guid].Qvt_Url, 'play',
                    self.Favorites[guid].infoLabels(), infoArt, self.Favorites[guid].ID, context_items)
        elif self.Favorites[guid].infoLabels()['duration'] == 0:
            context_items = [
                ('Update On Demand Content', 'RunPlugin(plugin://plugin.video.sling/?mode=demand&guid=%s&'
                                             'action=update)' % guid)
            ]
            addDir(self.Favorites[guid].Name, self.handleID, '', 'demand&guid=%s' % guid,
                   self.Favorites[guid].infoLabels(), self.Favorites[guid].infoArt(), context_items)

