CREATE TABLE IF NOT EXISTS Channels (
    GUID TEXT UNIQUE,
    ID INTEGER,
    Name TEXT,
    Call_Sign TEXT,
    Language TEXT,
    Genre TEXT,
    Thumbnail TEXT,
    Poster TEXT,
    Offered	INTEGER,
    Qvt_Url	TEXT,
    On_Demand INTEGER DEFAULT -1,
    Last_Update INTEGER DEFAULT -1,
    Hidden INTEGER DEFAULT 0,
    Protected INTEGER DEFAULT 0,
    PRIMARY KEY(GUID)
);
CREATE TABLE IF NOT EXISTS Guide (
    Channel_GUID TEXT,
    Start INTEGER,
    Stop INTEGER,
    Name TEXT,
    Description	TEXT,
    Thumbnail TEXT,
    Poster TEXT,
    Genre TEXT,
    Rating TEXT,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(Channel_GUID,Start,Stop)
);
CREATE TABLE IF NOT EXISTS On_Demand_Folders (
    Channel_GUID TEXT,
    Name TEXT,
    Pages INTEGER,
    Expiration INTEGER,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(Channel_GUID,Name)
);
CREATE TABLE IF NOT EXISTS On_Demand_Assets (
    Channel_GUID TEXT,
    Category TEXT,
    Asset_GUID TEXT,
    Type TEXT,
    Name TEXT,
    Description	TEXT,
    Thumbnail TEXT,
    Poster TEXT,
    Rating TEXT,
    Duration INTEGER,
    Release_Year INTEGER DEFAULT 0,
    Start INTEGER,
    Stop INTEGER,
    Playlist_URL TEXT,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(Channel_GUID,Category,Asset_GUID)
);
CREATE TABLE IF NOT EXISTS VOD_Assets (
    GUID TEXT,
    ID INTEGER,
    Name TEXT,
    Description	TEXT,
    Thumbnail TEXT,
    Poster TEXT,
    Duration INTEGER,
    Rating TEXT,
    Genre TEXT,
    Playlist_URL TEXT,
    Start INTEGER,
    Stop INTEGER,
    Release_Year INTEGER DEFAULT 0,
    Type TEXT,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(GUID)
);
CREATE TABLE IF NOT EXISTS Shows (
    GUID TEXT,
    Name TEXT,
    Description	TEXT,
    Thumbnail TEXT,
    Poster TEXT,
    Show_URL TEXT,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(GUID)
);
CREATE TABLE IF NOT EXISTS Favorite_Shows (
    Show_GUID TEXT,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(Show_GUID)
);
CREATE TABLE IF NOT EXISTS Seasons (
    GUID TEXT,
    Show_GUID TEXT,
    ID INTEGER,
    Name TEXT,
    Number INTEGER,
    Description	TEXT,
    Thumbnail TEXT,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(GUID,Show_GUID)
);
CREATE TABLE IF NOT EXISTS Episodes (
    GUID TEXT,
    ID INTEGER,
    Show_GUID TEXT,
    Season_GUID	TEXT,
    Name TEXT,
    Number TEXT,
    Description	TEXT,
    Thumbnail TEXT,
    Poster TEXT,
    Rating TEXT,
    Start INTEGER,
    Stop INTEGER,
    Duration INTEGER,
    Playlist_URL TEXT,
    Last_Update INTEGER DEFAULT -1,
    PRIMARY KEY(GUID,Show_GUID,Season_GUID)
);

