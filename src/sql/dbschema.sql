/*
################################################################
# Kiyoko - a multi-purpose discord application for moderation, #
#          server automatization, and community engagement     #
#                                                              #
# (c) 2023-2025 TophUwO All rights reserved.                   #
################################################################
*/


-- Force UTF-8 encoding.
PRAGMA encoding     = 'UTF-8';
PRAGMA foreign_keys = OFF;
PRAGMA user_version = 2;


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


-- Create 'commandinfo' table, holding global command information
CREATE TABLE commandinfo (
    cmdname TEXT NOT NULL,             -- name of command (full qualified name)
    added   INTEGER,                   -- unix timestamp of when the command was registered
    enabled BOOLEAN,                   -- whether or not the command is currently globally enabled
    count   INTEGER        DEFAULT(0), -- global command usage count
    lastuse INTEGER,                   -- UNIX timestamp of when the command was invoked last 

    PRIMARY KEY (
        cmdname
    )
);


-- Create table 'strike_entr', holding strikes for all users per guild
CREATE TABLE strike_entr (
    guildid INTEGER NOT NULL, -- ID of the guild in which the strike was recorded
    uid     INTEGER NOT NULL, -- user who was striked
    sid     INTEGER NOT NULL, -- ID of the mod who striked the user identified by uid
    id      TEXT    NOT NULL, -- ID of the strike itself
    reason  TEXT    NOT NULL, -- reason for the strike
    pt      INTEGER NOT NULL, -- points added for this strike
    ts      INTEGER NOT NULL, -- timestamp of when the strike was added
    msgref  TEXT,             -- (optional) message reference for proof

    UNIQUE (guildid, uid, id)
);


-- Create table 'strike_cfg', holding the per-guild config for the strike system
CREATE TABLE strike_cfg (
    guildid INTEGER NOT NULL, -- ID of the guild for which this entry is valid
    key     TEXT    NOT NULL, -- name of the setting
    p1      TEXT,             -- first param, meaning defined by key
    p2      TEXT              -- second param, meaning defined by key
);


PRAGMA foreign_keys = ON;


