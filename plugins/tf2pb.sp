#include <socket>
#include <sdktools_functions>
#include <sourcemod>

new String:serverIP[64];
new String:socketData[192];
new disconnectedPlayers[32][2];
new lastGameOver = 0;
new lastTournamentStateUpdate = 0;
new String:port[16];
new String:server[16] = "dallas"; 

public Plugin:myinfo =
{
	name = "TF2PB",
	author = "Jean-Denis Caron",
	description = "Server side management for the PUG system.",
	version = SOURCEMOD_VERSION,
	url = "http://github.com/550/tf2pb/"
};

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

public OnPluginStart()
{
    GetConVarString(FindConVar("ip"), serverIP, sizeof(serverIP));
    IntToString(GetConVarInt(FindConVar("hostport")), port, 10)
    lastTournamentStateUpdate = 0;

    for(new i = 32; i < 32; i++)
    {
        disconnectedPlayers[i][0] = -1;
        disconnectedPlayers[i][1] = 0;
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
    SocketConnect(socket, OnSocketConnected, OnSocketReceive, OnSocketDisconnected, "192.168.1.102", 50007)
}
