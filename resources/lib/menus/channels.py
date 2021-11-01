from resources.lib.globals import *

# ==================================================================================================================
#
# Channels Menu
#
# ==================================================================================================================


def getChannels(self):
    success, region = self.auth.getRegionInfo()
    if not success:
        notificationDialog(LANGUAGE(30016))
        return

    USER_DMA = region['USER_DMA']
    USER_OFFSET = region['USER_OFFSET']
    subs = binascii.b2a_base64(str.encode(LEGACY_SUBS.replace('+', ','))).decode().strip()
    channels_url = '%s/cms/publish3/domain/channels/v4/%s/%s/%s/1.json' % \
                   (self.endPoints['cms_url'], USER_OFFSET, USER_DMA, subs)
    log('\r%s' % channels_url)
    response = requests.get(channels_url, headers=HEADERS, verify=VERIFY)
    if response is not None and response.status_code == 200:
        response = response.json()
        if 'subscriptionpacks' in response:
            sub_packs = response['subscriptionpacks']
            for sub_pack in sub_packs:
                if 'channels' in sub_pack:
                    channel_names = ''
                    for channel in sub_pack['channels']:
                        if channel['network_affiliate_name'] is not None:
                            if 'Sling' not in channel['network_affiliate_name']:
                                if channel['channel_guid'] != '' and '"%s"' % channel['network_affiliate_name'] not in channel_names:
                                    if channel['network_affiliate_name'] not in ('FOX', 'ABC', 'NBC', 'CBS'):
                                        channel_names = '%s,"%s"' % (channel_names, channel['network_affiliate_name']) if channel_names != '' else '"%s"' %channel['network_affiliate_name']
                                    temp_channel = Channel(channel['channel_guid'], self.endPoints, self.DB)
                                    if temp_channel.GUID != '':
                                        self.Channels[channel['channel_guid']] = temp_channel
                    
                    query = "SELECT GUID FROM Channels WHERE Protected = 1"
                    try:
                        cursor = self.DB.cursor()
                        cursor.execute(query)
                        protected = cursor.fetchall()
                        for record in protected:
                            if record[0] not in self.Channels:
                                self.Channels[record[0]] = Channel(record[0], self.endPoints, self.DB)
                    except sqlite3.Error as err:
                        log('setSetting(): Failed retrieve protected records from DB, error => %s' % err)
                    except Exception as exc:
                        log('setSetting(): Failed retrieve protected records from DB, exception => %s' % exc)


def myChannels(self):
    log('My Channels Menu')
    timestamp = int(time.time())
    if len(self.Channels) == 0: getChannels(self)
    session = createResilientSession()
    for guid in self.Channels:
        if not self.Channels[guid].Hidden:
            if len(self.Channels[guid].On_Now) == 0 or self.Channels[guid].On_Now['Stop'] < timestamp:
                result, on_now = self.Channels[guid].onNow(session=session)
                if result: self.Channels[guid].On_Now = on_now
            infoArt = self.Channels[guid].infoArt()
            if self.Channels[guid].On_Now != {} and self.Channels[guid].On_Now['Stop'] >= timestamp:
                infoArt['thumb'] = self.Channels[guid].On_Now['Thumbnail']
                infoArt['poster'] = self.Channels[guid].On_Now['Poster']

            if self.Channels[guid].infoLabels()['duration'] > 0 and ('OFF-AIR' not in \
                    self.Channels[guid].infoLabels()['plot'] or SHOW_OFF_AIR):
                if self.Channels[guid].On_Demand:
                    url = ('%s?mode=demand&guid=%s' % (ADDON_URL, guid))

                context_items = [('Hide Channel', 'RunPlugin(plugin://plugin.video.sling/?'
                                'mode=setting&name=%s&value=%s)' % ('hide_channel', guid))]
                if self.Channels[guid].On_Demand:
                    context_items.append(('View On Demand', 'Container.Update(plugin://plugin.video.sling/?'
                                        'mode=demand&guid=%s&name=%s)' % (guid, self.Channels[guid].Name)))
                    context_items.sort(reverse=True)
                addLink(self.Channels[guid].Name, self.handleID, self.Channels[guid].Qvt_Url, 'play',
                        self.Channels[guid].infoLabels(), infoArt, self.Channels[guid].ID, context_items)
            elif self.Channels[guid].infoLabels()['duration'] == 0:
                context_items = [
                    ('Update On Demand Content', 'RunPlugin(plugin://plugin.video.sling/?mode=demand&guid=%s&'
                                                'action=update)' % guid),
                    ('Hide Channel', 'RunPlugin(plugin://plugin.video.sling/?'
                     'mode=setting&name=%s&value=%s)' % ('hide_channel', guid))
                ]
                addDir(self.Channels[guid].Name, self.handleID, '', 'demand&guid=%s' % guid,
                    self.Channels[guid].infoLabels(), self.Channels[guid].infoArt(), context_items)

    session.close()