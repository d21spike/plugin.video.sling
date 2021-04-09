from resources.lib.globals import *
from resources.lib.classes.auth import Auth
from xml.sax.saxutils import escape

if sys.version_info.major == 2:
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import HTTPServer
else:
    from http.server import SimpleHTTPRequestHandler, HTTPServer

class httpHandler(SimpleHTTPRequestHandler):
    Parent = None

    @staticmethod
    def set_Parent(self, parent):
        self.Parent = parent
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/xml')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        path = self.path[1:]

        log('Guide Service: Request received => %s' % self.requestline)

        if path == 'channels.m3u':
            log('Guide Service: Building playlist...')
            self.send_header('Content-type', 'text/xml')
            self.end_headers()
            Guide.channels(self.Parent, self.wfile)
            log('Guide Service: Finished.')
        elif path == 'guide.xml':
            log('Guide Service: Building guide...')
            self.send_header('Content-type', 'text/xml')
            self.end_headers()
            Guide.guide(self.Parent, self.wfile)
            log('Guide Service: Finished.')
        elif path == 'stop':
            self.Parent.Abort = True

class Guide(object):

    Monitor = None
    DB = None

    PORT = 9999
    Handler = httpHandler
    Server = None
    Abort = False

    def __init__(self):
        global USER_SUBS, USER_DMA, USER_OFFSET
        log('Guide Service:  __init__')
        
        self.Monitor = xbmc.Monitor()
        if not xbmcvfs.exists(DB_PATH):
            self.createDB()
        self.DB = sqlite3.connect(DB_PATH)

        if self.DB is not None:
            log('Starting HTTP Server')
            self.Handler.set_Parent(self.Handler, self)
            self.Server = HTTPServer(("", self.PORT), self.Handler)
            self.main()
        else:
            self.close()

    def main(self):
        log('Guide Service: main()')
        
        while not self.Abort:
            if self.Monitor.abortRequested():
                self.Abort = True
            self.Server.handle_request()

        self.close()

    def getChannels(self):
        log('Guide Service: getChannels()')
        channels = []
        query = "SELECT DISTINCT Channels.Guid, Channels.name, Channels.thumbnail, Channels.qvt_url, Channels.genre " \
                "FROM Channels " \
                "INNER JOIN Guide on Channels.GUID = Guide.Channel_GUID " \
                "WHERE Channels.Name NOT LIKE '%Sling%' AND Channels.Hidden = 0 " \
                "ORDER BY Channels.Name asc, substr(Channels.Call_Sign, -2) = '-M' desc"
        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            db_channels = cursor.fetchall()
            channel_names = ''
            if db_channels is not None and len(db_channels):
                for row in db_channels:
                    id = str(row[0])
                    title = str(strip(row[1]).replace("''", "'"))
                    logo = str(row[2])
                    url = str(row[3])
                    genre = str(row[4])
                    if '"%s"' % title not in channel_names:
                        channel_names = '%s,"%s"' % (channel_names, title) if channel_names != '' else '"%s"' % title
                        channels.append([id, title, logo, url, genre])
        except sqlite3.Error as err:
            error = 'getChannels(): Failed to retrieve channels from DB, error => %s\rQuery => %s' % (err, query)
            log(error)
            self.Last_Error = error
        except Exception as exc:
            error = 'getChannels(): Failed to retrieve channels from DB, exception => %s\rQuery => %s' % (exc, query)
            log(error)
            self.Last_Error = error

        return channels

    def channels(self, html):
        log('Guide Service: channels()')

        html.write('#EXTM3U\n'.encode())
        channels = self.getChannels()
        for channel_id, title, logo, url, genre in channels:
            html.write('\n'.encode())
            channel_info = '#EXTINF:-1 tvg-id="%s" tvg-name="%s"' % (channel_id, title.replace(' ', '_'))
            if logo is not None:
                channel_info += ' tvg-logo="%s"' % logo
            channel_info += ' group-title="Sling TV; %s",%s' % (genre.replace(',', ';'), title)
            html.write(('%s\n' % channel_info).encode())
            url = 'plugin://plugin.video.sling/?mode=play&url=%s' % url
            html.write(('%s\n' % url).encode())
            if self.Monitor.abortRequested():
                break

    def guide(self, html):
        log('Guide Service: guide()')

        html.write('<?xml version="1.0" encoding="utf-8" ?>\n'.encode())
        html.write('<tv>\n'.encode())

        channels = self.getChannels()
        for channel_id, title, logo, url, genre in channels:
            channel = '<channel id="%s">\n' % channel_id
            channel += '    <display-name lang="en">%s</display-name>\n' % escape(title)
            channel += '</channel>\n'
            html.write(channel.encode())
            
            if self.Monitor.abortRequested():
                break

        query = "SELECT strftime('%Y%m%d%H%M%S',datetime(Guide.Start, 'unixepoch')) as start, " \
                "strftime('%Y%m%d%H%M%S',datetime(Guide.Stop, 'unixepoch')) as stop, " \
                "Channels.Guid, Guide.Name, '' AS sub_title, Guide.Description, Guide.Thumbnail, Guide.Genre " \
                "FROM Guide " \
                "INNER JOIN Channels ON Channels.GUID = Guide.Channel_GUID WHERE Channels.Name NOT LIKE '%Sling%' " \
                "AND Channels.Hidden = 0 ORDER BY Channels.Call_Sign ASC"
        try:
            cursor = self.DB.cursor()
            cursor.execute(query)
            schedule = cursor.fetchall()

            for row in schedule:
                start_time = str(row[0])
                stop_time = str(row[1])
                channel_id = str(row[2])
                title = strip(row[3]).replace("''", "'")
                sub_title = strip(row[4]).replace("''", "'")
                desc = strip(row[5]).replace("''", "'")
                icon = str(row[6])
                genres = row[7]
                genres = genres.split(',')

                prg = ''
                prg += '<programme start="%s" stop="%s" channel="%s">\n' % (start_time, stop_time, channel_id)
                prg += '    <title lang="en">%s</title>\n' % escape(title)
                prg += '    <sub-title lang="en">%s</sub-title>\n' % escape(sub_title)
                prg += '    <desc lang="en">%s</desc>\n' % escape(desc)
                for genre in genres:
                    prg += '    <category lang="en">%s</category>\n' % escape(str(strip(genre)).strip().capitalize())
                prg += '    <icon src="%s"/>\n' % icon
                prg += '</programme>\n'

                html.write(prg.encode())
                if self.Monitor.abortRequested():
                    break
        except sqlite3.Error as err:
            error = 'guide(): Failed to retrieve guide data from DB, error => %s\rQuery => %s' % (err, query)
            log(error)
            self.Last_Error = error
        except Exception as exc:
            error = 'guide(): Failed to retrieve retrieve guide data from DB, exception => %s\rQuery => %s' % (exc, query)
            log(error)
            self.Last_Error = error

        html.write('</tv>'.encode())

    def createDB(self):
        log('Guide Service: createDB()')
        sql_file = xbmcvfs.File(SQL_PATH)
        sql = sql_file.read()
        sql_file.close()

        db = sqlite3.connect(DB_PATH)
        cursor = db.cursor()
        if sql != "":
            try:
                cursor.executescript(sql)
                db.commit()
            except sqlite3.Error as err:
                error = 'createDB(): Failed to create DB tables, error => %s' % err
                log(error)
                self.Last_Error = error
            except Exception as exc:
                error = 'createDB(): Failed to create DB tables, exception => %s' % exc
                log(error)
                self.Last_Error = error
        db.close()

    def close(self):
        log('Guide Service: close()')
        
        self.Server.server_close()
        self.DB.close()
        del self.Monitor
