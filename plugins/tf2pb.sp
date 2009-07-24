#include <socket>
#include <sourcemod>

new tournamentState = 0;

public Plugin:myinfo =
{
	name = "TF2PB",
	author = "Jean-Denis Caron",
	description = "Server side management for the PUG system.",
	version = SOURCEMOD_VERSION,
	url = "http://github.com/550/tf2pb/"
};

public Action:Command_Say(client, args)
{
	decl String:userText[192];
    userText[0] = '\0';
	if (!GetCmdArgString(userText, sizeof(userText)))
	{
		return Plugin_Continue;
	}

    if(StrContains(userText, "\"!needsub") == 0)
    { 
        decl String:ip[64];
        decl String:port[10];
        decl String:query[192];
        query = "";
        StripQuotes(userText);
        GetConVarString(FindConVar("ip"), ip, sizeof(ip));
        IntToString(GetConVarInt(FindConVar("hostport")), port, 10)
        StrCat(query, 192, userText);
        StrCat(query, 192, " ");
        StrCat(query, 192, ip);
        StrCat(query, 192, ":");
        StrCat(query, 192, port);
        sendDataToBot(query);
    }
	
	return Plugin_Continue;	
}

public Event_TeamplayGameOver(Handle:event, const String:name[], bool:dontBroadcast)
{
    tournamentState = 0;
    decl String:ip[64];
    decl String:port[10];
    decl String:query[192];
    query = "";
    GetConVarString(FindConVar("ip"), ip, sizeof(ip));
    IntToString(GetConVarInt(FindConVar("hostport")), port, 10)
    StrCat(query, 192, "!gameover");
    StrCat(query, 192, " ");
    StrCat(query, 192, ip);
    StrCat(query, 192, ":");
    StrCat(query, 192, port);
    sendDataToBot(query);
    PrintToChatAll("Game Over");
    ServerCommand("exec tf2dm.cfg");
}

public Event_TeamplayRestartRound(Handle:event, const String:name[], bool:dontBroadcast)
{
    PrintToChatAll("Round Restarted");
    tournamentState = 0;
}

public Event_TournamentStateupdate(Handle:event, const String:name[], bool:dontBroadcast)
{
    if(GetEventBool(event, "namechange") == false)
    {
        if(GetEventInt(event, "readystate") == 1)
        {
            tournamentState = tournamentState + 1;
            if(tournamentState >= 2)
            {
                PrintToChatAll("Match.cfg");
                ServerCommand("exec match.cfg");
            }
        }else{
            tournamentState = tournamentState - 1;
            PrintToChatAll("TF2DM.cfg");
            ServerCommand("exec tf2dm.cfg");
        }
        decl String:tournamentStateString[10];
        decl String:tournamentReadyState[10];
        IntToString(tournamentState, tournamentStateString, 10)
        IntToString(GetEventInt(event, "readystate"), tournamentReadyState, 10)
        PrintToChatAll("Event state : %s, Tournament state : %s", tournamentReadyState, tournamentStateString);
    }
}

public OnPluginStart()
{
    HookEvent("teamplay_game_over", Event_TeamplayGameOver);
    HookEvent("teamplay_restart_round", Event_TeamplayRestartRound);
    HookEvent("tournament_stateupdate", Event_TournamentStateupdate);
    RegConsoleCmd("say", Command_Say);
}

public OnSocketConnected(Handle:socket, any:data){
    decl String:query[192];
    GetArrayString(data, 0, query, 192);
    SocketSend(socket, query);
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
    new Handle:data = CreateArray(192);
    PushArrayString(data, query);
    SocketSetArg(socket, data);
    SocketSetSendqueueEmptyCallback(socket, OnSocketSendqueueEmpty);
    SocketConnect(socket, OnSocketConnected, OnSocketReceive, OnSocketDisconnected, "bot.tf2pug.org", 50007)
}
