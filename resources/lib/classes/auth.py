from resources.lib.globals import *
from requests_oauthlib import OAuth1


class Auth(object):
    global BASE_API

    HASH = '441e030d03595a122a281d081b1608511804776b42634b444443456a466b1c444d5b4f431e7860760263404f67445c617c7b46167' \
           '96767691d5a1d595d786445451f411e59697e627f7a181b657b484f6f020202'
    OTL_URL = '%s/v5/sessions?client_application=ottweb&format=json&locale=en' % BASE_API
    OTK_URL = '%s/v5/users/access_from_jwt' % BASE_API
    ACCESS_TOKEN = ''
    ACCESS = SETTINGS.getSetting('access')
    OCK = ''
    OCS = ''
    OTL = ''
    OTK = ''
    OTS = ''

    def __init__(self):
        self.deviceID()
        if self.ACCESS == '':
            self.ACCESS_TOKEN = ''
            SETTINGS.setSetting('access_token', self.ACCESS_TOKEN)
            self.ACCESS = self.HASH
        self.getAccess()

    def deviceID(self):
        global DEVICE_ID
        if DEVICE_ID != '': return
        randomID = ""
        randomBag = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for x in range(0, 32):
            randomID += randomBag[random.randint(0, 61)]
            if x == 7 or x == 11 or x == 15 or x == 19:
                randomID += '-'
        SETTINGS.setSetting('device_id', randomID)
        DEVICE_ID = randomID

    def loggedIn(self):
        if ACCESS_TOKEN == '': return False, 'ACCESS_TOKEN is blank, not logged in.'
        token_array = ACCESS_TOKEN.split('.')
        if len(token_array) == 0: return False, 'ACCESS_TOKEN is corrupt, not logged in.'

        user_token = loadJSON(base64.b64decode(token_array[1] + '=='))
        if 'email' in user_token:
            if user_token['email'] == USER_EMAIL:
                return True, 'ACCESS_TOKEN email matches USER_EMAIL, logged in.'
            else:
                SETTINGS.setSetting('access_token', '')
                SETTINGS.setSetting('user_email', '')
                SETTINGS.setSetting('password', '')
                return False, 'ACCESS_TOKEN email does not match USER_EMAIL, not logged in.'
        else:
            SETTINGS.setSetting('access_token', '')
            return False, 'ACCESS_TOKEN corrupt, not logged in.'

    def getRegionInfo(self):
        global USER_DMA, USER_OFFSET, USER_ZIP
        if not self.loggedIn(): return False, 'Must be logged in to retrieve region info.'
        log('getRegionInfo, Subscriber ID = ' + SUBSCRIBER_ID + ' | Device ID = ' + DEVICE_ID)
        if SUBSCRIBER_ID == '': return False, 'SUBSCRIBER_ID and DEVICE_ID required ' + \
                                       'for getRegionInfo'
        if DEVICE_ID == '':
            self.deviceID()
        regionUrl = BASE_GEO.format(SUBSCRIBER_ID, DEVICE_ID)
        log('getRegionInfo, URL => ' + regionUrl)
        headers = {
            "Host": "p-geo.movetv.com",
            "Connection": "keep-alive",
            "Origin": "https://watch.sling.com",
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Referer": "https://watch.sling.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9"
        }
        response = requests.get(regionUrl, headers=headers, verify=VERIFY)
        log("getRegionInfo Response = > " + str(response.json()))
        if response.status_code == 200:
            response = response.json()
            USER_DMA = str(response.get('dma', {}) or '')
            USER_OFFSET = (response.get('time_zone_offset', {}) or '')
            USER_ZIP = str(response.get('zip_code', {}) or '')

            debug = dict(urlParse.parse_qsl(DEBUG_CODE))
            log('Debug Code: %s' % json.dumps(debug, indent=4))
            if 'dma' in debug:
                USER_DMA = debug['dma']
            if 'offset' in debug:
                USER_OFFSET = debug['offset']
            if 'zip' in debug:
                USER_ZIP = debug['zip']

            SETTINGS.setSetting('user_dma', USER_DMA)
            SETTINGS.setSetting('user_offset', USER_OFFSET)
            SETTINGS.setSetting('user_zip', USER_ZIP)
            return True, {"USER_DMA": USER_DMA, "USER_OFFSET": USER_OFFSET}
        else:
            return False, 'Failed to retrieve user region info.'

    def getUserSubscriptions(self, subURL):
        global SUBSCRIBER_ID
        log("getUserSubscriptions => URL: " + subURL)

        if not self.loggedIn(): return False, 'Must be logged in to retrieve subscriptions.'
        auth = OAuth1(self.OCK, self.OCS, self.OTK, self.OTS)
        response = requests.get(subURL, headers=HEADERS, auth=auth, verify=VERIFY)
        log("getUserSubscriptions Response = > " + str(response.json()))
        if response.status_code == 200:
            if SUBSCRIBER_ID == '':
                SUBSCRIBER_ID = response.json()['guid']
                SETTINGS.setSetting('subscriber_id', SUBSCRIBER_ID)

            subscriptions = response.json()['subscriptionpacks']
            sub_packs = ''
            legacy_subs = ''
            for subscription in subscriptions:
                if sub_packs != '':
                    sub_packs += "+"
                sub_packs += subscription['guid']
                if legacy_subs != '':
                    legacy_subs += "+"
                legacy_subs += str(subscription['id'])

            debug = dict(urlParse.parse_qsl(DEBUG_CODE))
            log('Debug Code: %s' % json.dumps(debug, indent=4))
            if 'user_subs' in debug:
                sub_packs = debug['user_subs']
            if 'legacy_subs' in debug:
                legacy_subs = debug['legacy_subs']

            SETTINGS.setSetting('user_subs', sub_packs)
            SETTINGS.setSetting('legacy_subs', legacy_subs)

            return True, sub_packs

    def getAuth(self):
        return OAuth1(self.OCK, self.OCS, self.OTK, self.OTS)

    def getOTK(self):
        if not self.loggedIn(): return False, 'Must be logged in to retrieve OTK.'
        self.deviceID();
        self.getAccess()

        if self.OTL == '':
            otl_payload = {
                "email": USER_EMAIL,
                "password": USER_PASSWORD
            }
            response = requests.post(self.OTL_URL, headers=HEADERS, data=json.dumps(otl_payload), \
                                     verify=VERIFY)
            log("getOTK Login Response => " + str(response) + "" + str(response.json()))
            if response.status_code == 200 and 'token' in response.json():
                self.OTL = response.json()['token']
                self.setAccess()
        if self.OTL != '':
            otk_payload = {
                "token": self.OTL,
                "device_guid": DEVICE_ID,
                "client_application": "Browser"
            }
            auth = OAuth1(self.OCK, self.OCS)
            headers = {
                "Host": "ums.p.sling.com",
                "Connection": "keep-alive",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Origin": "https://watch.sling.com",
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "*/*",
                "Referer": "https://watch.sling.com/",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9"
            }
            response = requests.post(self.OTK_URL, headers=headers, data=json.dumps(otk_payload), auth=auth,
                                     verify=VERIFY)
            log("getOTK Auth = > " + str(response) + str(response.json()))

            if response.status_code == 200 and 'access_token' in response.json():
                json_data = response.json()['access_token']
                self.OTK = json_data['token']
                self.OTS = json_data['secret']
                self.setAccess()
                return True, 'Successfully retrieved OTK.'
            else:
                return False, 'Failed to retrieve OTK.'
        else:
            return False, 'OTL required to retrieve signing token.'

    def getUserID(self):
        user_info = ACCESS_TOKEN[ACCESS_TOKEN.find('.') + 1: ACCESS_TOKEN.rfind('.')]
        json_string = json.loads(base64.b64decode(user_info + "==="))

        return json_string

    def logIn(self, loginURL, email=USER_EMAIL, password=USER_PASSWORD):
        global ACCESS_TOKEN, USER_EMAIL, USER_PASSWORD
        log("logIn => URL: " + loginURL + " email: " + email)
        status, message = self.loggedIn()
        if status: return status, 'Already logged in.'

        if email == '' or password == '':
            # firstrun wizard
            if yesNoDialog(LANGUAGE(30006), no=LANGUAGE(30004), yes=LANGUAGE(30005)):
                email = inputDialog(LANGUAGE(30002))
                password = inputDialog(LANGUAGE(30003), opt=xbmcgui.ALPHANUM_HIDE_INPUT)
                SETTINGS.setSetting('User_Email', email)
                SETTINGS.setSetting('User_Password', password)
                USER_EMAIL = email
                USER_PASSWORD = password
            else:
                return False, 'Login Aborted'

        payload = '{"username":"' + email + '","password":"' + password + '"}'
        response = requests.post(loginURL, headers=HEADERS, data=payload, verify=VERIFY)
        if response.status_code == 200 and 'access_token' in response.json():
            SETTINGS.setSetting('access_token', response.json()['access_token'])
            ACCESS_TOKEN = response.json()['access_token']
            if self.OTK == '':
                if self.getOTK():
                    return True, 'Successfully logged in.'
                else:
                    return False, "Failed to log in, no otk"
            else:
                return True, 'Successfully logged in.'
        else:
            return False, 'Failed to log in, status code ' + str(response.status_code)

    def logOut(self):
        SETTINGS.setSetting('access_token', '')
        SETTINGS.setSetting('User_Email', '')
        SETTINGS.setSetting('User_Password', '')
        SETTINGS.setSetting('subscriber_id', '')
        SETTINGS.setSetting('user_dma', '')
        SETTINGS.setSetting('user_subs', '')
        SETTINGS.setSetting('legacy_subs', '')

    def xor(self, data, key):
        return ''.join(chr(ord(s) ^ ord(c)) for s, c in zip(data, key * 100))

    def getAccess(self):
        global DEVICE_ID, ADDON_ID
        if self.ACCESS == self.HASH:
            key = ADDON_ID.ljust(164, '.')
        else:
            key = DEVICE_ID.ljust(164, '.')
        decoded_access = self.xor(binascii.unhexlify(self.ACCESS).decode(), key)
        access_array = decoded_access.split(',')
        if len(access_array) < 5:
            return False
        else:
            self.OCK = access_array[0]
            self.OCS = access_array[1]
            self.OTL = access_array[2]
            self.OTK = access_array[3]
            self.OTS = access_array[4]
            self.getRegionInfo()
            return True

    def setAccess(self):
        global DEVICE_ID, ADDON_ID
        if self.ACCESS == self.HASH:
            key = ADDON_ID.ljust(164, '.')
        else:
            key = DEVICE_ID.ljust(164, '.')
        payload = ('%s,%s,%s,%s,%s' % (self.OCK, self.OCS, self.OTL, self.OTK, self.OTS))
        new_access = binascii.hexlify(str.encode(self.xor(payload, key)))
        SETTINGS.setSetting('access', new_access)
        self.ACCESS = new_access

    def getAccessJWT(self, endPoints):
        global ACCESS_TOKEN_JWT
        if ACCESS_TOKEN_JWT == '':
            payload = {'device_guid': DEVICE_ID, 'platform': 'browser', 'product': 'sling'}
            response = requests.post('%s/cmw/v1/client/jwt' % endPoints['cmwnext_url'], headers=HEADERS,
                                     data=json.dumps(payload), auth=self.getAuth())
            if response is not None:
                response = response.json()
                if 'jwt' in response:
                    SETTINGS.setSetting('access_token_jwt', response['jwt'])
                    ACCESS_TOKEN_JWT = response['jwt']

    def getPlaylist(self, playlist_url, end_points):
        log('getPlaylist, url = ' + playlist_url)
        license_key = ''
        response = requests.get(playlist_url, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            video = response.json()

            if video is None or 'message' in video: return
            if 'playback_info' not in video: sys.exit()
            mpd_url = video['playback_info']['dash_manifest_url']
            qmx_url = video['playback_info']['clips'][0]['location']
            if 'UNKNOWN' not in mpd_url:
                response = requests.get(qmx_url, headers=HEADERS, verify=VERIFY)
                if response is not None and response.status_code == 200:
                    qmx = response.json()
                    if 'message' in qmx: return
                    lic_url = ''
                    if 'encryption' in qmx:
                        lic_url = qmx['encryption']['providers']['widevine']['proxy_url']
                        log('resolverURL, lic_url = ' + lic_url)

                    if 'channel_guid' in video:
                        channel_id = video['channel_guid']
                    if 'playback' in video and 'linear_info' in video['playback_info']:
                        channel_id = video['playback_info']['linear_info']['channel_guid']
                    elif 'playback' in video and 'asset' in video['playback_info']:
                        channel_id = video['playback_info']['asset']['guid']
                    elif 'playback_info' in video and 'vod_info' in video['playback_info']:
                        try:
                            channel_id = video['playback_info']['vod_info']['svod_channels'][0]
                        except:
                            channel_id = ''
                    else:
                        channel_id = ''

                    if lic_url != '':
                        license_key = '%s||{"env":"production","user_id":"%s","channel_id":"%s","message":[D{SSM}]}|' % (
                            lic_url, self.getUserID(), channel_id)

                    log('license_key = ' + license_key)
            else:
                if 'vod_info' in video['playback_info']:
                    fod_url = video['playback_info']['vod_info'].get('media_url', '')
                    response = requests.get(fod_url, headers=HEADERS, verify=VERIFY)
                    if response.status_code == 200:
                        mpd_url = response.json()['stream']
                    elif 'message' in response.json():
                        notificationDialog(response.json()['message'])
                elif 'linear_info' in video['playback_info'] \
                        and 'disney_stream_service_url' in video['playback_info']['linear_info']:
                    log('getPlaylist, Inside Disney/ABC')
                    utc_datetime = str(time.mktime(datetime.datetime.utcnow().timetuple())).split('.')[0]
                    sha1_user_id = hashlib.sha1(SUBSCRIBER_ID.encode()).hexdigest()
                    rsa_sign_url = '%s/cmw/v1/rsa/sign' % end_points['cmwnext_url']
                    stream_headers = HEADERS
                    stream_headers['Content-Type'] = 'application/x-www-form-urlencoded'
                    payload = 'document=%s_%s_' % (sha1_user_id, utc_datetime)
                    log('getPlaylist, RSA payload => %s' % payload)
                    response = requests.post(rsa_sign_url, headers=stream_headers, data=payload, verify=VERIFY)
                    if response.status_code == 200 and 'signature' in response.json():
                        signature = response.json()['signature']
                        log('getPlaylist, RSA Signature => %s' % signature)
                        disney_info = video['playback_info']['linear_info']
                        if 'abc' in disney_info['disney_network_code']:
                            brand = '003'
                        else:
                            brand = disney_info['disney_brand_code']
                        params = {
                            'ak': 'fveequ3ecb9n7abp66euyc48',
                            'brand': brand,
                            'device': '001_14',
                            'locale': disney_info.get('disney_locale', ''),
                            'token': '%s_%s_%s' % (sha1_user_id, utc_datetime, signature),
                            'token_type': 'offsite_dish_ott',
                            'user_id': sha1_user_id,
                            'video_type': 'live',
                            'zip_code': USER_ZIP
                        }
                        service_url = disney_info['disney_stream_service_url']
                        payload = ''
                        for key in params.keys():
                            payload += '%s=%s&' % (key, params[key])
                        payload = payload[:-1]
                        response = requests.post(service_url, headers=stream_headers, data=payload, verify=VERIFY)
                        log("Disney response code: %i" % response.status_code)
                        if response.status_code == 200:
                            log(str(response.text))
                            session_xml = xmltodict.parse(response.text)
                            service_stream = session_xml['playmanifest']['channel']['assets']['asset']['#text']
                            log('getPlaylist, XML Stream: ' + str(service_stream))
                            mpd_url = service_stream

            asset_id = ''
            if 'entitlement' in video and 'asset_id' in video['entitlement']:
                asset_id = video['entitlement']['asset_id']

            return mpd_url, license_key, asset_id