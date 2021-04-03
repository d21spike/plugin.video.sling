from resources.lib.globals import *

class Show(object):

    GUID = ''
    Name = ''
    Description = ''
    Seasons = {}
    Thumbnail = ICON
    Poster = FANART
    Show_Url = ''

    Endpoints = None
    DB = None

    def __init__(self, show_guid, endpoints=None, db=None, silent=False):
        # log('Show initialization')

        self.Endpoints = endpoints
        self.DB = db
        self.headers = {
            'Origin': 'https://watch.sling.com',
            'User-Agent': USER_AGENT,
            'Accept': '*/*',
            'Referer': 'https://watch.sling.com/browse/dynamic/on-now',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        found, db_show = self.getDBShow(show_guid)
        if found:
            # log(json.dumps(db_show, indent=4))
            self.GUID = db_show['GUID']
            self.Name = db_show['Name']
            self.Description = db_show['Description']
            self.Seasons = db_show['Seasons']
            self.Thumbnail = db_show['Thumbnail']
            self.Poster = db_show['Poster']
            self.Show_Url = db_show['Show_URL']
            # log('Added DB show => \r%s' % json.dumps(self.showInfo(), indent=4))
        else:
            process = False
            show_url = "%s/cms/api/franchises/%s" % (self.Endpoints['cms_url'], show_guid)
            show_json = ''
            log('Show %s not in DB, trying url => %s' % (show_guid, show_url))
            response = requests.get(show_url, headers=self.headers, verify=VERIFY)
            if response is not None:
                show_json = response.json()
                if show_json is not None:
                    if 'message'in show_json:
                        if show_json['message'] == "Bad Request":
                            show_url = '%s/expand=true;playable=false' % show_url
                            log('First show URL failed, trying alternate => %s' % show_url)
                            response = requests.get(show_url, headers=self.headers, verify=VERIFY)
                            if response is not None:
                                show_json = response.json()
                                if show_json is not None:
                                    if 'message' not in show_json:
                                        process = True
                                    else:
                                        log('Alternate show URL failed, message => %s' % show_json['message'])
                                        if not silent:
                                            notificationDialog('Sling failed to respond, retry later.',
                                                               'Failed', True)
                    else:
                        process = True
            if process:
                result, show = self.processJSON(show_json)
                if result:
                    self.GUID = show['GUID']
                    self.Name = show['Name']
                    self.Description = show['Description']
                    self.Seasons = show['Seasons']
                    self.Thumbnail = show['Thumbnail']
                    self.Poster = show['Poster']
                    self.Show_Url = show['Show_URL']
                    log('Added show => \r%s' % json.dumps(self.showInfo(), indent=4))
                else:
                    log('Failed to add show => \r%s' % json.dumps(show, indent=4))

    def processJSON(self, show_json):
        log('Processing show json')
        result = True
        timestamp = int(time.time())
        cursor = self.DB.cursor()

        new_show = {
            'GUID': show_json['guid'],
            'Name': show_json['title'],
            'Description': show_json['description'],
            'Seasons': {},
            'Thumbnail': '',
            'Poster': '',
            'Show_URL': show_json['_href']
        }
        if new_show['Description'] is None: new_show['Description'] = ''
        if 'image' in show_json:
            new_show['Thumbnail'] = show_json['image']['url']
        if 'background_image' in show_json:
            new_show['Poster'] = show_json['background_image']['url']

        show_query = "REPLACE INTO Shows (GUID, Name, Description, Thumbnail, Poster, Show_URL, Last_Update) VALUES " \
                     "('%s', '%s', '%s', '%s', '%s', '%s', %i)" % \
                     (new_show['GUID'], new_show['Name'].replace("'", "''"),
                      new_show['Description'].replace("'", "''"), new_show['Thumbnail'], new_show['Poster'],
                      new_show['Show_URL'], timestamp)
        try:
            cursor.execute(show_query)
            self.DB.commit()
        except sqlite3.Error as err:
            log('Failed to save  show %s to DB, error => %s\r%s' % (self.Name, err, show_query))
            result = False
        except Exception as exc:
            log('Failed to save  show %s to DB, exception => %s\r%s' % (self.Name, exc, show_query))
            result = False

        season_query = ""
        if 'seasons' in show_json:
            for season in show_json['seasons']:
                new_season, season_query = self.processSeason(season, new_show, season_query, cursor)
                new_show['Seasons'][new_season['Number']] = new_season
        if 'programs' in show_json:
            new_season, season_query = self.processSeason(show_json, new_show, season_query, cursor)
            new_show['Seasons'][new_season['Number']] = new_season

        if season_query != '':
            try:
                cursor.executescript(season_query)
                self.DB.commit()
            except sqlite3.Error as err:
                log('Failed to save  show %s seasons to DB, error => %s\r%s' % (self.Name, err, season_query))
                result = False
            except Exception as exc:
                log('Failed to save  show %s seasons to DB, exception => %s\r%s' % (self.Name, exc, season_query))
                result = False

        return result, new_show

    def processSeason(self, season, new_show, season_query, cursor):
        timestamp = int(time.time())

        new_season = {
            'GUID': season['guid'],
            'Show_GUID': new_show['GUID'],
            'ID': int(season['id']) if 'id' in season else '',
            'Name': season['title'] if 'title' in season else '',
            'Number': int(season['number']) if 'number' in season else 0,
            'Description': season['description'] if season['description'] is not None else '',
            'Thumbnail': new_show['Thumbnail'],
            'Episodes': {},
            'infoLabels': {},
            'infoArt': {}
        }
        if 'image' in season:
            if season['image'] is not None:
                if 'url' in season['image']:
                    new_season['Thumbnail'] = season['image']['url']
                else:
                    new_season['Thumbnail'] = season['image']

        episode_query = ""
        for episode in season['programs']:
            new_episode, episode_query = self.processEpisode(episode, new_season, new_show, episode_query)
            new_season['Episodes'][new_episode['Number']] = new_episode
        
        new_season['infoLabels'] = {
            'title': new_season['Name'],
            'plot': new_season['Description'],
            'genre': 'Season',
            'duration': 0,
            'mediatype': 'Video',
            'mpaa': ''
        }
        new_season['infoArt'] = {
            'thumb': new_season['Thumbnail'],
            'logo': new_season['Thumbnail'],
            'clearlogo': new_season['Thumbnail'],
            'poster': new_season['Thumbnail'],
            'fanart': new_show['Poster']
        }
        season_query += "REPLACE INTO Seasons (GUID, Show_GUID, ID, Name, Number, Description, Thumbnail, Last_Update) " \
                        "VALUES ('%s', '%s', %i, '%s', %i, '%s', '%s', %i); " % \
                        (new_season['GUID'], new_season['Show_GUID'], new_season['ID'],
                         new_season['Name'].replace("'", "''"), new_season['Number'],
                         new_season['Description'].replace("'", "''"), new_season['Thumbnail'], timestamp)

        if episode_query != '':
            try:
                cursor.executescript(episode_query)
                self.DB.commit()
            except sqlite3.Error as err:
                log('Failed to save show %s episodes to DB, error => %s\r%s' % (self.Name, err, episode_query))
                result = False
            except Exception as exc:
                log('Failed to save show %s episodes to DB, exception => %s\r%s' % (self.Name, exc, episode_query))
                result = False

        return new_season, season_query

    def processEpisode(self, episode, new_season, new_show, episode_query):
        timestamp = int(time.time())
        # log(json.dumps(episode, indent=4))
        new_episode = {
            'GUID': episode['guid'],
            'ID': int(episode['id']),
            'Show_GUID': new_show['GUID'],
            'Season_GUID': new_season['GUID'],
            'Name': episode['name'],
            'Number': int(episode['episode_number']) if 'episode_number' in episode else episode['guid'],
            'Description': '',
            'Thumbnail': new_season['Thumbnail'],
            'Poster': new_show['Poster'],
            'Rating': '',
            'Start': 0,
            'Stop': 0,
            'Duration': 0,
            'Playlist_URL': '',
            'infoLabels': {},
            'infoArt': {}
        }

        if 'description' in episode:
            if episode['description'] is not None:
                new_episode['Description'] = episode['description']
        if 'thumbnail' in episode:
            if episode['thumbnail'] is not None:
                if 'url' in episode['thumbnail']:
                    new_episode['Thumbnail'] = episode['thumbnail']['url']
                elif episode['thumbnail'] is not None:
                    new_episode['Thumbnail'] = episode['thumbnail']['href']
        if 'background_image' in episode:
            if episode['background_image'] is not None:
                if 'url' in episode['background_image']:
                    new_episode['Poster'] = episode['background_image']['url']
                else:
                    new_episode['Poster'] = episode['background_image']['href']

        for airing in episode['airings']:
            ratings = ""
            for rating in airing['ratings']:
                ratings = '%s, %s' % (ratings, rating) if ratings != '' else rating
            if ratings != '':
                new_episode['Rating'] = ratings.strip().replace('_', ' ')
            if 'duration' in airing:
                new_episode['Duration'] = int(airing['duration'])
            for slot in airing['availability']:
                start = timeStamp(stringToDate(slot['start'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                         '%Y-%m-%d %H:%M:%S'))
                if int(slot['stop'][0:4]) > 2099: slot['stop'] = slot['stop'].replace(slot['stop'][0:4], "2096")
                stop = timeStamp(stringToDate(slot['stop'].replace('T', ' ').replace('Z', '').replace('0001', '2096'),
                                        '%Y-%m-%d %H:%M:%S'))
                if 'channel_guid' in slot:
                    if subscribedChannel(self, slot['channel_guid']) and (start <= timestamp <= stop):
                        new_episode['Start'] = start
                        new_episode['Stop'] = stop
                        new_episode['Playlist_URL'] = '%s?channel=%s' % (slot['qvt'], slot['channel_guid'])
                        break
            if new_episode['Playlist_URL'] != '':
                break
        if new_episode['Playlist_URL'] == '':
            airing_index = len(episode['airings']) - 1
            if airing_index >= 0:
                airing = episode['airings'][airing_index]
                slot_index = len(airing['availability']) - 1
                if slot_index >= 0:
                    slot = airing['availability'][slot_index]
                    start = timeStamp(stringToDate(slot['start'].replace('T', ' ').replace('Z', '').replace('0001', '2019'),
                                             '%Y-%m-%d %H:%M:%S'))
                    if int(slot['stop'][0:4]) > 2099: slot['stop'] = slot['stop'].replace(slot['stop'][0:4], "2096")
                    stop = timeStamp(stringToDate(slot['stop'].replace('T', ' ').replace('Z', '').replace('0001', '2096'),
                                            '%Y-%m-%d %H:%M:%S'))
                    if 'channel_guid' in slot:
                        if subscribedChannel(self, slot['channel_guid']):
                            new_episode['Start'] = start
                            new_episode['Stop'] = stop
                            new_episode['Playlist_URL'] = '%s?channel=%s' % (slot['qvt'], slot['channel_guid'])
        new_episode['infoLabels'] = {
            'title': new_episode['Name'],
            'plot': new_episode['Description'],
            'genre': 'Episode',
            'duration': new_episode['Duration'],
            'mediatype': 'Video',
            'mpaa': new_episode['Rating'],
        }
        new_episode['infoArt'] = {
            'thumb': new_episode['Thumbnail'],
            'logo': new_episode['Thumbnail'],
            'clearlogo': new_episode['Thumbnail'],
            'poster': new_episode['Thumbnail'],
            'fanart': new_episode['Poster']
        }
        episode_query += "REPLACE INTO Episodes (GUID, ID, Show_GUID, Season_GUID, Name, Number, Description, " \
                         "Thumbnail, Poster, Rating, Start, Stop, Duration, Playlist_URL, Last_Update) VALUES " \
                         "('%s', %i, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %i, %i, %i, '%s', %i); " % \
                         (new_episode['GUID'], new_episode['ID'], new_episode['Show_GUID'],
                          new_episode['Season_GUID'], new_episode['Name'].replace("'", "''"),
                          new_episode['Number'], new_episode['Description'].replace("'", "''"),
                          new_episode['Thumbnail'], new_episode['Poster'], new_episode['Rating'],
                          new_episode['Start'], new_episode['Stop'], new_episode['Duration'],
                          new_episode['Playlist_URL'], timestamp)

        return new_episode, episode_query

    def getDBShow(self, guid):
        log('Retrieving show %s from DB' % guid)
        found = False
        db_show = None

        cursor = self.DB.cursor()
        try:
            show_query = "SELECT * FROM Shows WHERE GUID = '%s'" % guid
            cursor.execute(show_query)
        except sqlite3.Error as err:
            log('Failed to retrieve show %s from DB, error => %s' % (guid, err))
        except Exception as exc:
            log('Failed to retrieve show %s from DB, exception => %s' % (guid, exc))

        show = cursor.fetchone()
        if show is not None:
            db_show = {
                'GUID': show[0],
                'Name': show[1].replace("''", "'"),
                'Description': show[2].replace("''", "'"),
                'Seasons': {},
                'Thumbnail': show[3],
                'Poster': show[4],
                'Show_URL': show[5]
            }

            found = True
        log('Found => %s' % str(found))

        return found, db_show

    def getSeasons(self, update=False, silent=False):
        if self.GUID == '': return False
        cursor = self.DB.cursor()
        timestamp = int(time.time())

        season_query = "SELECT * FROM Seasons WHERE Show_GUID = '%s'" % self.GUID
        cursor.execute(season_query)
        seasons = cursor.fetchall()
        if len(seasons) == 0 or update:
            process = False
            show_url = "%s/cms/api/franchises/%s" % (self.Endpoints['cms_url'], self.GUID)
            log('Show %s not in DB, trying url => %s' % (self.GUID, show_url))
            response = requests.get(show_url, headers=self.headers, verify=VERIFY)
            if response is not None:
                show_json = response.json()
                if show_json is not None:
                    if 'message'in show_json:
                        if show_json['message'] == "Bad Request":
                            show_url = '%s/expand=true;playable=false' % show_url
                            log('First show URL failed, trying alternate => %s' % show_url)
                            response = requests.get(show_url, headers=self.headers, verify=VERIFY)
                            if response is not None:
                                show_json = response.json()
                                if show_json is not None:
                                    if 'message' not in show_json:
                                        process = True
                                    else:
                                        log('Alternate show URL failed, message => %s' % show_json['message'])
                                        if not silent:
                                            notificationDialog('Sling failed to respond, retry later.',
                                                               'Failed', True)
                    else:
                        process = True
            if process:
                result, show = self.processJSON(show_json)
                if result:
                    self.GUID = show['GUID']
                    self.Name = show['Name']
                    self.Description = show['Description']
                    self.Seasons = show['Seasons']
                    self.Thumbnail = show['Thumbnail']
                    self.Poster = show['Poster']
                    self.Show_Url = show['Show_URL']
                    log('Added show => \r%s' % json.dumps(self.showInfo(), indent=4))

                    cursor.execute(season_query)
                    seasons = cursor.fetchall()
                else:
                    log('Failed to add show => \r%s' % json.dumps(show, indent=4))

        for season in seasons:
            db_season = {
                'GUID': season[0],
                'Show_GUID': season[1],
                'ID': season[2],
                'Name': season[3],
                'Number': season[4],
                'Description': season[5],
                'Thumbnail': season[6],
                'Episodes': {},
                'Mode': 'play',
                'infoLabels': {
                    'title': season[3],
                    'plot': season[5],
                    'genre': 'Season',
                    'duration': 0,
                    'mediatype': 'Video',
                    'mpaa': ''
                },
                'infoArt': {
                    'thumb': season[6],
                    'logo': season[6],
                    'clearlogo': season[6],
                    'poster': season[6],
                    'fanart': self.Poster
                }
            }

            episode_query = "SELECT * FROM Episodes WHERE Show_GUID = '%s' AND Season_GUID = '%s'" % \
                            (self.GUID, db_season['GUID'])
            cursor.execute(episode_query)
            episodes = cursor.fetchall()
            for episode in episodes:
                db_episode = {
                    'GUID': episode[0],
                    'ID': episode[1],
                    'Show_GUID': episode[2],
                    'Season_GUID': episode[3],
                    'Name': episode[4],
                    'Number': episode[5],
                    'Description': episode[6],
                    'Thumbnail': episode[7],
                    'Poster': episode[8],
                    'Rating': episode[9],
                    'Start': episode[10],
                    'Stop': episode[11],
                    'Duration': episode[12],
                    'Playlist_URL': episode[13],
                    'Mode': 'play',
                    'infoLabels': {
                        'title': episode[4],
                        'plot': episode[6],
                        'genre': 'Episode',
                        'duration': episode[12],
                        'mediatype': 'Video',
                        'mpaa': episode[9],
                    },
                    'infoArt': {
                        'thumb': episode[7],
                        'logo': episode[7],
                        'clearlogo': episode[7],
                        'poster': episode[7],
                        'fanart': self.Poster
                    }
                }

                # ==========================================================================
                prefix = ''
                season_num = ''
                episode_num = ''
                timestamp = int(time.time())
                if db_episode['Stop'] < timestamp or db_episode['Playlist_URL'] == '':
                    db_episode['Mode'] = 'info'
                    prefix = '[COLOR=red]Unavailable[/COLOR]'
                    try:
                        db_episode['infoLabels']['plot'] += '[CR][CR]Start: %s[CR]Stop: %s' % \
                                                            (datetime.datetime.fromtimestamp(db_episode['Start']).strftime('%m/%d/%Y %H:%M:%S'),
                                                            datetime.datetime.fromtimestamp(db_episode['Stop']).strftime('%m/%d/%Y %H:%M:%S'))
                    except:
                        pass
                if db_episode['Start'] > timestamp:
                    db_episode['Mode'] = 'info'
                    prefix = '[COLOR=yellow]Future[/COLOR]'
                    log(str(db_episode['Start']))
                    try:
                        db_episode['infoLabels']['plot'] += '[CR][CR]Start: %s[CR]Stop: %s' % \
                                                            (datetime.datetime.fromtimestamp(db_episode['Start']).strftime('%m/%d/%Y %H:%M:%S'),
                                                            datetime.datetime.fromtimestamp(db_episode['Stop']).strftime('%m/%d/%Y %H:%M:%S'))
                    except:
                        pass
                if db_season['Number'] != 0:
                    season_num = 'S%i' % db_season['Number']
                if db_episode['Number'] != db_episode['GUID']:
                    episode_num = 'E%s' % db_episode['Number']
                title = '%s %s%s - %s' % (prefix, season_num, episode_num, db_episode['Name'])
                db_episode['infoLabels']['title'] = title
                # ==========================================================================

                db_season['Episodes'][db_episode['Number']] = db_episode

            # ==========================================================================

            if len(db_season['Episodes']) == 0:
                db_season['Mode'] = 'info'
                db_season['infoLabels']['title'] = title = '[COLOR=gray]Empty[/COLOR] %s' % \
                                                           db_season['infoLabels']['title']

            # ==========================================================================

            self.Seasons[db_season['Number']] = db_season

        return True

    def infoLabels(self):
        return {
            'title': self.Name,
            'plot': self.Description,
            'genre': 'Show',
            'duration': 0,
            'mediatype': 'Video',
            'mpaa': ''
        }

    def infoArt(self):
        return {
            'thumb': self.Thumbnail,
            'logo': self.Thumbnail,
            'clearlogo': self.Thumbnail,
            'poster': self.Thumbnail,
            'fanart': self.Poster
        }

    def showInfo(self):
        return {
            'GUID': self.GUID,
            'Name': self.Name,
            'Description': self.Description,
            'Seasons': len(self.Seasons),
            'Thumbnail': self.Thumbnail,
            'Poster': self.Poster,
            'Show_Url': self.Show_Url
        }

    def setFavorite(self):
        log('Setting show %s as a favorite' % self.Name)
        result = True

        query = "REPLACE INTO Favorite_Shows (Show_GUID) VALUES ('%s')" % self.GUID
        cursor = self.DB.cursor()
        try:
            cursor.execute(query)
            self.DB.commit()
        except sqlite3.Error as err:
            log('Failed to save show %s as favorite to DB, error => %s' % (self.Name, err))
            result = False
        except Exception as exc:
            log('Failed to save show %s as favorite to DB, exception => %s' % (self.Name, exc))
            result = False

        return result

    def resetFavorite(self):
        log('Removing show %s as a favorite' % self.Name)
        result = True

        query = "DELETE FROM Favorite_Shows WHERE Show_GUID = '%s'" % self.GUID
        cursor = self.DB.cursor()
        try:
            cursor.execute(query)
            self.DB.commit()
        except sqlite3.Error as err:
            log('Failed to delete show %s as favorite to DB, error => %s' % (self.Name, err))
            result = False
        except Exception as exc:
            log('Failed to delete show %s as favorite to DB, exception => %s' % (self.Name, exc))
            result = False

        return result
