from resources.lib.globals import *

# ==================================================================================================================
#
# Shows Menu
#
# ==================================================================================================================


def myShows(self):
    global HANDLE_ID

    log('My shows Menu')
    if 'subset' not in self.params:
        subset = 'AG'
        infoLabels = {
            'title': 'Shows A - G', 'plot': '', 'genre': 'Shows', 'duration': 0, 'mediatype': 'Video', 'mpaa': ''
        }
        infoArt = {
            'thumb': ICON, 'logo': ICON, 'clearlogo': ICON, 'poster': ICON, 'fanart': FANART
        }
        addDir(infoLabels['title'], self.handleID, '', 'show&subset=%s' % subset, infoLabels, infoArt)
        subset = 'HQ'
        infoLabels['title'] = 'Shows H - Q'
        addDir(infoLabels['title'], self.handleID, '', 'show&subset=%s' % subset, infoLabels, infoArt)
        subset = 'RZ'
        infoLabels['title'] = 'Shows R - Z'
        addDir(infoLabels['title'], self.handleID, '', 'show&subset=%s' % subset, infoLabels, infoArt)
        subset = '09'
        infoLabels['title'] = 'Shows 0 - 9'
        addDir(infoLabels['title'], self.handleID, '', 'show&subset=%s' % subset, infoLabels, infoArt)

        query = "SELECT COUNT(Show_GUID) AS Favorites FROM Favorite_Shows"
        cursor = self.DB.cursor()
        try:
            cursor.execute(query)
            count = cursor.fetchone()
            if count is not None:
                count = count[0]
                log('Favorite count => %i' % count)
                if count > 0:
                    subset = 'FV'
                    infoLabels['title'] = 'Favorite Shows'
                    addDir(infoLabels['title'], self.handleID, '', 'show&subset=%s' % subset, infoLabels, infoArt)
        except sqlite3.Error as err:
            log('Failed to retrieve favorite count from DB, error => %s\r%s' % (err, query))
        except Exception as exc:
            log('Failed to retrieve favorite count from DB, exception => %s\r%s' % (exc, query))
    else:
        begin = self.params['subset'][0]
        end = self.params['subset'][-1]
        cursor = self.DB.cursor()
        if self.params['subset'] == '09':
            query = "SELECT * FROM Shows WHERE ('A' > UPPER(SUBSTR(Name, 1, 1)) OR 'Z' < UPPER(SUBSTR(Name, 1, 1)" \
                    ")) AND ('a' > UPPER(SUBSTR(Name, 1, 1)) OR 'z' < UPPER(SUBSTR(Name, 1, 1))) ORDER BY NAME ASC"
        elif self.params['subset'] == 'FV':
            query = "SELECT * FROM Shows INNER JOIN Favorite_Shows ON Shows.GUID = Favorite_Shows.Show_GUID " \
                    "ORDER BY Shows.Name ASC"
        else:
            query = "SELECT * FROM Shows WHERE UPPER(SUBSTR(Name, 1, 1)) >= '%s' AND UPPER(SUBSTR(Name, 1, 1)) " \
                    "<= '%s' ORDER BY Name ASC" % (begin, end)
        try:
            cursor.execute(query)
            results = cursor.fetchall()
            for show in results:
                db_show = Show(show[0], self.endPoints, self.DB)
                self.Shows[db_show.GUID] = db_show
                if self.params['subset'] != 'FV':
                    context_items = [
                        ('Add to Favorite Shows', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                  'action=favorite)' % db_show.GUID),
                        ('Update Show', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                        'action=update)' % db_show.GUID)
                    ]
                else:
                    context_items = [
                        ('Update Show', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                        'action=update)' % db_show.GUID),
                        ('Remove from Favorite Shows', 'RunPlugin(plugin://plugin.video.sling/?mode=show&guid=%s&'
                                                       'action=unfavorite)' % db_show.GUID)
                    ]
                context_items.append(('Record All', 'RunPlugin(%s?mode=record_show&type=all&guid=%s)' %
                                      (ADDON_URL, db_show.GUID)))
                context_items.append(('Record New', 'RunPlugin(%s?mode=record_show&type=new&guid=%s)' %
                                      (ADDON_URL, db_show.GUID)))
                addDir(db_show.Name, self.handleID, '', 'show&guid=%s' % db_show.GUID, db_show.infoLabels(),
                       db_show.infoArt(), context_items)

        except sqlite3.Error as err:
            log('Failed to retrieve shows from DB, error => %s\r%s' % (err, query))
        except Exception as exc:
            log('Failed to retrieve shows from DB, exception => %s\r%s' % (exc, query))


def myShowsSeasons(self):
    log('My shows seasons Menu')
    show = Show(self.params['guid'], self.endPoints, self.DB)
    show.getSeasons()
    for season_num in show.Seasons:
        season = show.Seasons[season_num]
        if season['Mode'] == 'play':
            addDir(season['infoLabels']['title'], self.handleID, '', 'show&guid=%s&season=%i' %
                   (season['Show_GUID'], season['Number']), season['infoLabels'], season['infoArt'])
        else:
            addLink(season['infoLabels']['title'], self.handleID, '', season['Mode'], season['infoLabels'],
                    season['infoArt'])


def myShowsEpisodes(self):
    log('My shows episodes Menu')
    timestamp = int(time.time())
    show = Show(self.params['guid'], self.endPoints, self.DB)
    show.getSeasons()
    season = show.Seasons[int(self.params['season'])]
    for episode_number in season['Episodes']:
        episode = season['Episodes'][episode_number]
        addLink(episode['Name'], self.handleID, episode['Playlist_URL'], episode['Mode'], episode['infoLabels'],
                episode['infoArt'])


def myShowsSetFavorite(self):
    show = Show(self.params['guid'], self.endPoints, self.DB)
    if show.setFavorite():
        notificationDialog(LANGUAGE(30110))
    else:
        notificationDialog(LANGUAGE(30111))


def myShowsResetFavorite(self):
    show = Show(self.params['guid'], self.endPoints, self.DB)
    if show.resetFavorite():
        notificationDialog(LANGUAGE(30112))
    else:
        notificationDialog(LANGUAGE(30113))


def myShowsUpdate(self):
    show = Show(self.params['guid'], self.endPoints, self.DB)
    if show.getSeasons(True):
        notificationDialog(LANGUAGE(30114))
    else:
        notificationDialog(LANGUAGE(30115))
