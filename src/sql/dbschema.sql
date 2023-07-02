/*
######################################################################
# Project:    Sukajan Bot v0.1                                       #
# File Name:  dbschema.sql                                           #
# Author:     Sukajan One-Trick <tophuwo01@gmail.com>                #
# Description:                                                       #
#   a bot for for advanced custom moderation features                #
#                                                                    #
# (C) 2023 Sukajan One-Trick. All rights reserved.                   #
######################################################################
*/


-- Force UTF-8 encoding.
PRAGMA encoding = 'UTF-8';

-- Create 'guilds' table, holding general data regarding
-- guilds (servers).
CREATE TABLE guilds (
    id      VARCHAR (256) NOT NULL, -- guild id (pk)
    ownerid VARCHAR (256) NOT NULL, -- id of guild owner
    created INTEGER       NOT NULL, -- UNIX timestamp (epoch) of the date the guild was created
    joined  INTEGER       NOT NULL, -- UNIX timestamp of the time the bot joined the guild
    left    INTEGER,                -- UNIX timestamp of the time the bot (last) left the server

    PRIMARY KEY (
        id
    )
);

-- Create 'guildsettings' table, holding guild-specific
-- configuration such as command prefix, server alias, etc.
CREATE TABLE guildsettings (
    guildid     VARCHAR (256)  NOT NULL,    -- guild id (pk)
    alias       TEXT,                       -- guild-specific nickname
    logchan     VARCHAR (256),              -- channel (id) to send log and debug messages to
    welcomechan VARCHAR (256),              -- channel (id) to send welcome messages to
    goodbyechan VARCHAR (256),              -- channel (id) to send goodbye messages to
    sendwelcome INTEGER        DEFAULT (0), -- interpreted as boolean
    sendgoodbye INTEGER        DEFAULT (0), -- interpreted as boolean

    PRIMARY KEY (
        guildid
    )
);


