# plugin.video.sling
Sling TV Add-On for Kodi

![](https://github.com/d21spike/plugin.video.sling/blob/master/resources/images/icon.png?raw=true)

![Build Status](https://img.shields.io/badge/build-beta-orange)
![License](https://img.shields.io/badge/license-GPL--2.0--only-success.svg)
![Kodi Version](https://img.shields.io/badge/Kodi-Leia%2B-brightgreen)
![Contributors](https://img.shields.io/badge/Contributors-d21spike%2C%20eracknaphobia-darkgray)

## Links

* [Sling TV](https://www.sling.com/)
* [Support Thread](#Not Yet Available)
* [Wiki](https://github.com/d21spike/plugin.video.sling/wiki)
* [Kodi Wiki](https://kodi.wiki/view/Main_Page)

## Important Information

* **Must** have a valid SlingTV account
* **Must** reside in the USA. VPN access is possible but not supported.
* This add-on will create a database file and cache meta-information on your device. Video content is **not** stored.
* Should database corruption occur resulting in errors, it is acceptable to delete the database file located in the userdata folder. The database will be recreated next attempt to read/write.
  * There is "Delete database" option under "Expert." This leaves the database file/structure intact and simply purges the data.
* The Slinger service is experimental and a work-in-progress, as such it also optional.

## Basic add-on functionality

* This add-on mimics the SlingTV login process, on initial launch you will be asked to enter your credentials. Failure to do so and/or incorrect credentials will result in a non-functional add-on. 
  ![Login Prompt](https://github.com/d21spike/plugin.video.sling/blob/master/resources/images/signin_prompt.png?raw=true)
  * If you entered incorrect credentials and are no longer receiving a prompt, you can open the add-on settings to either modify them or to reset the add-on settings to default.
  ![Add-on Settings](https://github.com/d21spike/plugin.video.sling/blob/master/resources/images/settings.png?raw=true)
* Once Signed-In, you will now be greeted by the main menu (similar layout to SlingTV.)
  ![Main Menu](https://github.com/d21spike/plugin.video.sling/blob/master/resources/images/main_menu.png?raw=true)
* Each menu exectes calls to both the local (auto-generated) database and SlingTV servers.
  * In order to provide the most accurate content, each menu navigation checks the geo location of the device. This largely affect market area channels such as locals.
  * If content is not found locally then an attempt will be made to fetch it externally.
  * This is done in an effort to both speed up execution time as well as reduce the amount of calls made to SlingTV servers.
* This add-on employs a class structure for SlingTV content.
  * Channel Class
    * The guide is included here
      * Guide data is retrieved whenever a channel(s) are displayed (ie. Channel's Menu)
        * A single call for guide data is made for each channel and retrieves 24 hours of content (midnight to midnight.)
    * VOD content is typically tied to a channel, as such it also is included here.
    * On Demand assets are also processed here since they are channel driven. On ingress these assets can become categorized as shows and are added to the shows table.
      * On Demand content is retrieved on an as-needed basis or via the slinger service. Once this is gathered, execution time is significantly reduced.
      * There are strictly "On Demand" channels, toggling them from the channels menu will redirect the user to the respective channel's On Demand menu.
  * Show Class
    * This breaks each individual show in into it's respective seasons and episodes.
    * This also handles "programs" such as sporting events and live programming.
      * These typically receive a season number of 0 and an incremental episode value. Assets with a season of 0 are treated as a special case.
    * Episodes will be classified by their availability:
      * _"No Label"_ are Playable episode.
      * _Future_ are Episodes that will soon become playable.
      * _Unavailable_ are episodes that are no longer playable but information is kept for completeness and when/if they become available again.
    * Due to the overwhelming number of shows and for ease of access, a **Favorites** system is also employed.
      * On any given show the user can toggle options to Favorite a show and/or update a shows episodes.
      * Once there is at least one _"Favorite"_ show, a new menu "Favorites" appears under shows.
        * When browsing a show through favorites, a user can toggle options to Unfavorite or Update a show
* Favorites will display favorited content through SlingTV
  * There are plans to incorporate functional Favorite/Unfavorite functionality 
* On Now and My TV menus are now stored due to their ever-changing structure.
  * Their content (assets) are cataloged in the local database to decrease execution time.
* Search functionality is brought over from sling.
  * The results are the same as you would get on SlingTV minus rental content.
  * There are future plans to search local database content for results as well.
  
## Slinger Service **WIP**

* The goal with this Service is to utilize the intervals defined in the add-on settings and fetch content before it is requested resulting in decreased execution time. Another goal is to provide _optional_ IPTV Simple integration as a functional channel guide.
  * The service will fetch the specified number of guide days and store it in the database.
    * This data is used for displaying On Now information as well as the playlist files for the channel guide (if used.)
    * Data older than a day old is also purged to eliminate wasted space.
  * The service will fetch show episode information/new episodes based on the specified interval and the last updated timestamp stored in the local database.
  * The service will fetch On Demand information such as menus and content resulting in faster loads when that menu is selected.
  * The service can/will update IPTV Simple settings to point to the generated guide playlist files and attempt to reload the client so the guide is updated.
