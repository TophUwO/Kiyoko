/*
################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023 TophUwO All rights reserved.                        #
################################################################
*/


-- Force UTF-8 encoding.
PRAGMA encoding = 'UTF-8';

-- Create 'guilds' table, holding general data regarding
-- guilds (servers).
CREATE TABLE guilds (
    id      INTEGER  NOT NULL, -- guild id (pk)
    joined  INTEGER  NOT NULL, -- UNIX timestamp of the time the bot joined the guild
    left    INTEGER,           -- UNIX timestamp of the time the bot (last) left the server

    PRIMARY KEY (
        id
    )
);

-- Create 'guildsettings' table, holding guild-specific
-- configuration such as command prefix, server alias, etc.
CREATE TABLE guildsettings (
    guildid INTEGER NOT NULL,                -- guild id (pk)
    config  TEXT              DEFAULT('{}'), -- guild settings stored as JSON

    PRIMARY KEY (
        guildid
    )
);


