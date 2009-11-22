#include <clients>
#include <socket>
#include <sdktools_functions>
#include <sourcemod>
#include <tf2_stocks>

new allowExtend = 1;
new Handle:classTimer;
new extendTime = 30;
new Handle:extendTimer;
new disconnectedPlayers[32][2];
new lastGameOver = 0;
new lastExtendMessage = 0;
new lastExtension = 0;
new lastTournamentStateUpdate = 0;
new players[32][6];
new String:port[16];
new regularTime = 30;
new String:server[16] = "chicago"; 
new String:serverIP[64];
new String:socketData[192];

public Plugin:myinfo =
{
	name = "TF2PB",
	author = "Jean-Denis Caron",
	description = "Server side management for the PUG system.",
	version = SOURCEMOD_VERSION,
	url = "http://github.com/550/tf2pb/"
};

public Action:checkForOffClassPlayers(Handle:timer){
    new playerCount = GetClientCount();
    new teamAOffClassPlayers = 0;
    new teamBOffClassPlayers = 0;
    for(new i = 1; i <= playerCount; i++)
    {
        players[i][0] = i;
        players[i][2] = 0;
        players[i][5] = GetClientTeam(i);
        new classID = GetClassID(i);
        if(classID != 1 && classID != 3 && classID != 4 && classID != 5)
        {
            players[i][1] = players[i][1] + 10;
            players[i][2] = 1;
            if(players[i][5] == 2)
            {
                teamAOffClassPlayers = teamAOffClassPlayers + 1;
            }else if(players[i][5] == 3)
            {
                teamBOffClassPlayers = teamBOffClassPlayers + 1;
            }
        }
    }
    new teamWithOffClassPlayers = 0;
    if(teamAOffClassPlayers > 1)
    {
        teamWithOffClassPlayers = 2;
        if(teamBOffClassPlayers > 1)
        {
            teamWithOffClassPlayers = -1;
        }
    }else if(teamBOffClassPlayers > 1)
    {
        teamWithOffClassPlayers = 3;
    }
    for(new i = 1; i <= playerCount; i++)
    {
        if(players[i][1] > 0 && players[i][2] == 1 && (players[i][5] == teamWithOffClassPlayers || teamWithOffClassPlayers == -1))
        {
            if(players[i][4] == -1)
            {
                PrintToChat(i, "Warning! Somebody in your team is already playing offclass but only one is allowed. You or him must switch back to a standard competitive class (demo, medic, scout, soldier) within 5 minutes.");
                players[i][4] = 0;
            }else{
                if(players[i][1] >= 300)
                {
                    new availableTime = 60 - players[i][4];
                    if(players[i][4] < 60){
                        PrintToChat(i, "You or one of your teammate have %i seconds to switch back to a standard competitive class (demo, medic, scout, soldier).", availableTime);
                    }else{
                        PrintToChat(i, "Please switch back to a standard competitive class (demo, medic, scout, soldier).");
                        ForcePlayerSuicide(i);
                    }
                    players[i][4] = players[i][4] + 10;
                }
            }
        }
    }
}

public Action:checkToExtendTime(Handle:timer){
    new mapTimeLeft = 0;
    GetMapTimeLeft(mapTimeLeft);
    if(mapTimeLeft <= 180 && (GetTime() - lastExtendMessage) > 300)
    {
        extendTime = extendTime + 15;
        lastExtendMessage = GetTime();
        PrintToChatAll("Only 3 minutes are remaining to this match. Somebody has to type \"!extend\" in the chat to increase the time limit.");
    }
}

public Event_PlayerDisconnect(Handle:event, const String:name[], bool:dontBroadcast)
{
    new appendedValue = 0;
    new disconnectedCounter = 0;
    for(new i = 0; i < 32; i++)
    {
        if(GetTime() - disconnectedPlayers[i][1] <= 1 * 60)
        {
            disconnectedCounter++;
        }else
        {
            disconnectedPlayers[i][0] = -1;
            disconnectedPlayers[i][1] = 0;
        }

        if(!appendedValue && disconnectedPlayers[i][0] == -1)
        {
            disconnectedPlayers[i][0] = GetEventInt(event, "userid");
            disconnectedPlayers[i][1] = GetTime();
            disconnectedCounter++;
            appendedValue = 1;
        }
    }

    if(disconnectedCounter == 6)
    {
        gameOver();
    }
}

public Action:Event_PlayerSay(Handle:event, const String:name[], bool:dontBroadcast)
{
	decl String:userText[192];
    userText[0] = '\0';
	if (!GetEventString(event, "text", userText, 192))
	{
		return Plugin_Continue;
	}

    decl String:steamID[192];
    GetClientAuthString(GetClientOfUserId(GetEventInt(event, "userid")), steamID, 192);

    if(StrContains(userText, "!cancel") == 0)
    { 
        if((GetTime() - lastExtension) <= 300)
        {
            allowExtend = 0;
            ServerCommand("mp_timelimit %i", regularTime);
        }else if(lastExtension > 0){
            PrintToChatAll("You can't cancel the time extension after 5 minutes it got extended.");
        }
    }

    if(StrContains(userText, "!extend") == 0)
    { 
        if(allowExtend == 1)
        {
            lastExtension = GetTime();
            ServerCommand("mp_timelimit %i", extendTime);
            PrintToChatAll("Somebody extended this match for 15 more minutes. If you disagree with that decision type \"!cancel\" in the chat within the next 5 minutes.");
        }else{
            PrintToChatAll("Somebody cancelled the extension, this game can't be extended.");
        }
    }

    if(StrContains(userText, "!needsub") == 0)
    { 
        decl String:query[192];
        query = "";
        StripQuotes(userText);
        StrCat(query, 192, userText);
        StrCat(query, 192, " ");
        StrCat(query, 192, steamID);
        StrCat(query, 192, " ");
        StrCat(query, 192, serverIP);
        StrCat(query, 192, ":");
        StrCat(query, 192, port);
        sendDataToBot(query);
    }
	
	return Plugin_Continue;	
}

public Event_TeamplayGameOver(Handle:event, const String:name[], bool:dontBroadcast)
{
    gameOver();
}

public Event_TeamplayRestartRound(Handle:event, const String:name[], bool:dontBroadcast)
{
    if((GetTime() - lastTournamentStateUpdate) <= 10)
    {
        classTimer = CreateTimer(10.0, checkForOffClassPlayers, _, TIMER_REPEAT);
        extendTimer = CreateTimer(10.0, checkToExtendTime, _, TIMER_REPEAT);
        decl String:record[64] = "tv_record ";
        decl String:time[64];
        FormatTime(time, 64, "%Y-%m-%d-%Hh%Mm");
        StrCat(record, 64, time);
        StrCat(record, 64, "_");
        StrCat(record, 64, server);
        StrCat(record, 64, port);
        ServerCommand("tv_stoprecord");
        ServerCommand(record);
        PrintToChatAll("%s", record);
        PrintToChatAll("Live!");
    }
}

public Event_TeamplayRestartSeconds(Handle:event, const String:name[], bool:dontBroadcast)
{
    PrintToChatAll("Match.cfg");
    ServerCommand("exec match.cfg");
}

public Event_TournamentStateupdate(Handle:event, const String:name[], bool:dontBroadcast)
{
    if(GetEventInt(event, "readystate") == 0)
    {
        PrintToChatAll("DM");
        ServerCommand("exec tf2dm.cfg");
    }
    lastTournamentStateUpdate = GetTime();
}

public gameOver()
{
    if(GetTime() - lastGameOver >= 60)
    {
        CloseHandle(classTimer);
        CloseHandle(extendTimer);
        new String:blueScore[2];
        new String:redScore[2];
        IntToString(GetTeamScore(3), blueScore, 2);
        IntToString(GetTeamScore(2), redScore, 2);
        lastGameOver = GetTime();
        ServerCommand("tv_stoprecord");
        decl String:query[192];
        query = "";
        StrCat(query, 192, "!gameover");
        StrCat(query, 192, " ");
        StrCat(query, 192, blueScore);
        StrCat(query, 192, ":");
        StrCat(query, 192, redScore);
        StrCat(query, 192, " ");
        StrCat(query, 192, serverIP);
        StrCat(query, 192, ":");
        StrCat(query, 192, port);
        sendDataToBot(query);
        PrintToChatAll("%s", query);
        PrintToChatAll("TF2 Game Over");
        ServerCommand("exec tf2dm.cfg");
    }
}

GetClassID(client) {
    new class = _:TF2_GetPlayerClass(client);
    switch(class) {
        case 1: return 1; // Scout.
        case 2: return 2; // Sniper.
        case 3: return 3; // Soldier.
        case 4: return 4; // Demo.
        case 5: return 5; // Medic.
        case 6: return 6; // Heavy.
        case 7: return 7; // Pyro.
        case 8: return 8; // Spy.
        case 9: return 9; // Engie.
    }
    return -1;
}

public OnPluginStart()
{
    GetConVarString(FindConVar("ip"), serverIP, sizeof(serverIP));
    IntToString(GetConVarInt(FindConVar("hostport")), port, 10)
    lastTournamentStateUpdate = 0;

    for(new i = 32; i < 32; i++)
    {
        disconnectedPlayers[i][0] = -1;
        disconnectedPlayers[i][1] = 0;
        players[i][0] = -1; // Player ID.
        players[i][1] = 0; // Off class timer.
        players[i][2] = 0; // Actually playing off class.
        players[i][3] = 0; // Regular warning.
        players[i][4] = -1; // Dual off class warning.
        players[i][5] = 0; // Team.
    }

    HookEvent("player_disconnect", Event_PlayerDisconnect);
    HookEvent("player_say", Event_PlayerSay);
    HookEvent("teamplay_game_over", Event_TeamplayGameOver);
    HookEvent("teamplay_restart_round", Event_TeamplayRestartRound);
    HookEvent("teamplay_round_restart_seconds", Event_TeamplayRestartSeconds);
    HookEvent("tf_game_over", Event_TeamplayGameOver);
    HookEvent("tournament_stateupdate", Event_TournamentStateupdate);
}

public OnSocketConnected(Handle:socket, any:arg){
    SocketSend(socket, socketData);
}

public OnSocketDisconnected(Handle:socket, any:arg){
    CloseHandle(socket);
}

public OnSocketError(Handle:socket, const errorType, const errorNum, any:arg){
    CloseHandle(socket);
}

public OnSocketReceive(Handle:socket, String:receiveData[], const dataSize, any:arg){
    return 0;
}

public OnSocketSendqueueEmpty(Handle:socket, any:arg){
    SocketDisconnect(socket);
    CloseHandle(socket);
}

public sendDataToBot(String:query[])
{
    new Handle:socket = SocketCreate(SOCKET_TCP, OnSocketError);
    Format(socketData, sizeof(socketData), "%s", query);
    SocketConnect(socket, OnSocketConnected, OnSocketReceive, OnSocketDisconnected, "bot.tf2pug.org", 50007)
}
