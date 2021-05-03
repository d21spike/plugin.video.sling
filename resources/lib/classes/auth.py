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
        log('auth::init()')
        self.deviceID()
        if self.ACCESS == '':
            self.ACCESS = self.HASH
        self.getAccess()

    def deviceID(self):
        global DEVICE_ID
        log('auth::deviceID()')
        if DEVICE_ID != '': return
        randomID = ""
        randomBag = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for x in range(0, 32):
            randomID += randomBag[random.randint(0, 61)]
            if x == 7 or x == 11 or x == 15 or x == 19:
                randomID += '-'
        SETTINGS.setSetting('device_id', randomID)
        DEVICE_ID = randomID
        log('auth::deviceID() New ID %s' % DEVICE_ID)

    def loggedIn(self):
        log('auth:loggedIn()')
        if self.OTK == '' or self.OTS == '':
            log('auth:loggedIn() No auth token')
            return False, 'OAuth access is blank, not logged in.', {}

        auth = OAuth1(self.OCK, self.OCS, self.OTK, self.OTS)
        user_headers = HEADERS
        try:
            user_headers.pop('Content-Type')
        except:
            pass
        response = requests.get(USER_INFO_URL, headers=user_headers, auth=auth, verify=VERIFY)
        if response.status_code == 200:
            response_json = response.json()
            if 'email' in response_json:
                if response_json['email'] == USER_EMAIL:
                    log('auth::loggedIn() Account Active')
                    return True, 'Account email matches USER_EMAIL, logged in.', response_json
                else:
                    log('auth::loggedIn() Account Mismatch')
                    SETTINGS.setSetting('access', '')
                    SETTINGS.setSetting('user_email', '')
                    SETTINGS.setSetting('password', '')
                    return False, 'Account email does not match USER_EMAIL, not logged in.', {}
            else:
                log('auth::loggedIn() Account info not retrieved')
                SETTINGS.setSetting('access', '')
                SETTINGS.setSetting('user_email', '')
                SETTINGS.setSetting('password', '')
                return False, 'Account info corrupt, not logged in.', {}
        else:
            log('auth::loggedIn() Access Denied')
            SETTINGS.setSetting('access', '')
            return False, 'Account info access denied', {}

    def getRegionInfo(self):
        global USER_DMA, USER_OFFSET, USER_ZIP
        log('auth::getRegionInfo()')
        if not self.loggedIn(): return False, 'Must be logged in to retrieve region info.'
        log('auth::getRegionInfo()  Subscriber ID: %s  | Device ID: %s' % (SUBSCRIBER_ID, DEVICE_ID))
        if SUBSCRIBER_ID == '': return False, 'SUBSCRIBER_ID and DEVICE_ID required for getRegionInfo()'
        if DEVICE_ID == '':
            self.deviceID()
        regionUrl = BASE_GEO.format(SUBSCRIBER_ID, DEVICE_ID)
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
        temp_response = response.json()
        if response is not None:
            if 'lookup_address' in temp_response:
                temp_response['lookup_address'] = '***REDACTED***'
            if 'city' in temp_response:
                temp_response['city'] = '***REDACTED***'
            if 'state' in temp_response:
                temp_response['state'] = '***REDACTED***'
            if 'zip_code' in temp_response:
                temp_response['zip_code'] = '***REDACTED***'
            if 'country' in temp_response:
                temp_response['country'] = '***REDACTED***'
            if 'latitude' in temp_response:
                temp_response['latitude'] = '***REDACTED***'
            if 'longitude' in temp_response:
                temp_response['longitude'] = '***REDACTED***'
            
            log("auth::getRegionInfo() Response => %s" % json.dumps(temp_response, indent=4))
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

    def getUserSubscriptions(self):
        global SUBSCRIBER_ID
        log('auth::getUserSubscriptions()')
        loggedIn, message, json_data = self.loggedIn()
        if not loggedIn: return False, 'Must be logged in to retrieve subscriptions.'
        
        if json_data is not None:
            if 'postal_code' in json_data:
                json_data['postal_code'] = '***REDACTED***'
            if 'billing_zipcode' in json_data:
                json_data['billing_zipcode'] = '***REDACTED***'
            if 'email' in json_data:
                json_data['email'] = '***REDACTED***'
            if 'billing_method' in json_data:
                json_data['billing_method'] = '***REDACTED***'
            if 'name' in json_data:
                json_data['name'] = '***REDACTED***'

            log("auth::getUserSubscriptions() Response = > " + json.dumps(json_data, indent=4))
        
            subscriptions = json_data['subscriptionpacks']
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
                sub_packs = debug['user_subs'].replace(',', '+')
            if 'legacy_subs' in debug:
                legacy_subs = debug['legacy_subs']

            SETTINGS.setSetting('user_subs', sub_packs)
            SETTINGS.setSetting('legacy_subs', legacy_subs)

            return True, sub_packs

    def getAuth(self):
        return OAuth1(self.OCK, self.OCS, self.OTK, self.OTS)

    def getOTK(self, endPoints):
        log('auth::getOTK()')
        self.deviceID()
        self.getAccess()

        # Validate account
        payload = "email=%s&password=%s&device_guid=%s" % (requests.utils.quote(
            USER_EMAIL), requests.utils.quote(USER_PASSWORD), requests.utils.quote(DEVICE_ID))
        account_headers = HEADERS
        account_headers['Content-Type'] = 'application/x-www-form-urlencoded'
        auth = OAuth1(self.OCK, self.OCS)
        response = requests.put('%s/v3/xauth/access_token.json' %
                                endPoints['ums_url'], headers=account_headers, data=payload, auth=auth, verify=VERIFY)
        response_json = response.json()

        if response.status_code == 200 and 'oauth_token' in response_json:
            self.OTK = response_json['oauth_token']
            self.OTS = response_json['oauth_token_secret']
            self.OTL = 'NO-LONGER-IN-USE'
            log('auth::getOTK() Got OAuth tokens')

            self.setAccess()
            return True, 'Successfully retrieved user OAuth token. \r%s | %s' % (self.OTK, self.OTS)
        else:
            log('auth::getOTK() Failed to retrieve OAuth token')
            return False, 'Failed to retrieve user OAuth token %i' % response.status_code

    def logIn(self, endPoints, email=USER_EMAIL, password=USER_PASSWORD):
        global USER_EMAIL, USER_PASSWORD
        log('auth::logIn() Email: %s' % email[:5])
        
        # Check if already logged in
        status, message, json_data = self.loggedIn()
        log("auth::logIn() => Already loggedIn() %r, %s" % (status, message))
        if status: return status, 'Already logged in.'

        # First launch, credentials empty
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

        # Check if account exists
        payload = {
            'request_context': {
                'application_name': 'Browser',
                'interaction_id': 'Browser:%s' % DEVICE_ID[:7],
                'partner_name': 'Browser',
                'request_id': str(random.randint(0, 999)),
                'timestamp': str(time.mktime(datetime.datetime.utcnow().timetuple())).split('.')[0]
            },
            'request': {
                'email': USER_EMAIL
            }
        }
        auth = OAuth1(self.OCK, self.OCS)
        response = requests.post('%s/user/lookup' % endPoints['extauth_url'], headers=HEADERS, data=json.dumps(payload), auth=auth, verify=VERIFY)
        response_json = response.json()
        
        if response.status_code == 200:
            log('auth::logIn() =>\r%s' % json.dumps(response_json['response_context'], indent=4))
            if 'response' in response_json:
                account = response_json['response']
                if account['account_status'] == 'active':
                    SUBSCRIBER_ID = account['guid']
                    SETTINGS.setSetting('subscriber_id', SUBSCRIBER_ID)

                    if self.OTK == '':
                        gotOTK, message = self.getOTK(endPoints)
                        if gotOTK:
                            return True, 'Successfully logged in.'
                        else:
                            self.logOut()
                            return False, "Failed to log in, check credentials"
                    else:
                        return True, 'Successfully logged in.'
                else:
                    self.logOut()
                    return False, 'Account is not active'
            else:
                self.logOut()
                return False, 'Failed to validate account'
        else:
            self.logOut()
            return False, 'Unable to validate account'

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
        log('auth::getPlaylist() URL: %s' % playlist_url)
        license_key = ''
        response = requests.get(playlist_url, headers=HEADERS, verify=VERIFY)
        if response is not None and response.status_code == 200:
            video = response.json()

            if video is None or 'message' in video: return
            if 'playback_info' not in video: sys.exit()
            mpd_url = video['playback_info']['dash_manifest_url']
            for clip in video['playback_info']['clips']:
                if clip['location'] != '':
                    qmx_url = clip['location']
                    break
            if 'UNKNOWN' not in mpd_url:
                response = requests.get(qmx_url, headers=HEADERS, verify=VERIFY)
                if response is not None:
                    # START: CDN Server error temporary fix
                    message = 'Sorry, our service is currently not available in your region'
                    if message in response.text:
                        qmx_url = re.sub(r"p-cdn\d", "p-cdn1", qmx_url)
                        response = requests.get(qmx_url, headers=HEADERS, verify=VERIFY)

                        mpd_url = re.sub(r"p-cdn\d", "p-cdn1", mpd_url)
                    # END: CDN Server error temporary fix

                    qmx = response.json()
                    if 'message' in qmx: return
                    lic_url = ''
                    if 'encryption' in qmx:
                        lic_url = qmx['encryption']['providers']['widevine']['proxy_url']
                        log('resolverURL, lic_url = ' + lic_url)

                    if 'playback_info' in playlist_url:
                        channel_id = playlist_url.split('/')[-4]
                    else:
                        channel_id = playlist_url.split('/')[-2]
                        if 'channel=' in playlist_url:
                            channel_id = playlist_url.split('?')[-1].split('=')[-1]                        

                    debug = dict(urlParse.parse_qsl(DEBUG_CODE))
                    if 'channel' in debug:
                        channel_id = debug['channel']
                    if lic_url != '':
                        license_key = '%s|User-Agent=%s|{"env":"production","user_id":"%s","channel_id":"%s","message":[D{SSM}]}|' % (
                            lic_url, ANDROID_USER_AGENT, SUBSCRIBER_ID, channel_id)

                    log('auth::getPlaylist() license_key: %s' % license_key)
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
                    log('auth::getPlaylist() Inside Disney/ABC')
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
                        log('auth::getPlaylist() RSA Signature: %s' % signature)
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
                        log("auth::getPlaylist() Disney response code: %i" % response.status_code)
                        if response.status_code == 200:
                            log(str(response.text))
                            session_xml = xmltodict.parse(response.text)
                            service_stream = session_xml['playmanifest']['channel']['assets']['asset']['#text']
                            log('auth::getPlaylist() XML Stream: %s' % str(service_stream))
                            mpd_url = service_stream

            asset_id = ''
            if 'entitlement' in video and 'asset_id' in video['entitlement']:
                asset_id = video['entitlement']['asset_id']
            elif 'playback_info' in video and 'asset' in video['playback_info'] and 'guid' in \
                    video['playback_info']['asset']:
                asset_id = video['playback_info']['asset']['guid']

            return mpd_url, license_key, asset_id
