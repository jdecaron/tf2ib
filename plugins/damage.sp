#include <sourcemod>

new live = 0;

public Plugin:myinfo =
{
	name = "TF2DMG",
	author = "Jean-Denis Caron",
	description = "Damage stats for TF2.",
	version = SOURCEMOD_VERSION,
	url = "http://github.com/550/"
};

public OnPluginStart()
{
    live = 0;
    HookEvent("player_hurt", Event_PlayerHurt);
    HookEvent("teamplay_restart_round", Event_RoundStart);
    HookEvent("teamplay_win_panel", Event_WinPanel);
}

public Event_PlayerHurt(Handle:event, const String:name[], bool:dontBroadcast)
{
    if(live == 1)
    {
        PrintToChatAll("Live!");
        decl String:clientname[32];
        decl String:steamid[64];
        decl String:team[64];

        new client = GetClientOfUserId(GetEventInt(event, "userid"));
        new attacker = GetClientOfUserId(GetEventInt(event, "attacker"));
        new damage = GetEventInt(event, "damageamount");
        if(client != attacker && attacker != 0)
        {
            GetClientAuthString(client, steamid, sizeof(steamid));
            GetClientName(client, clientname, sizeof(clientname));
            new teamindex = GetClientTeam(client);
            if(teamindex == 2)
            {
                team = "Red"
            }
            else if(teamindex == 3)
            {
                team = "Blue"
            }
            else
            {
                team = "undefined"
            }
            PrintToChatAll("\"%s<%d><%s><%s>\" triggered \"damage_stats\" %d",
                clientname,
                client,
                steamid,
                team,
                damage);
        }
        new health = GetEventInt(event, "health");
        PrintToChatAll("Hurt! c%d, a%d, h%d, d%d", client, attacker, health, damage);
    }
}

public Action:Event_RoundStart(Handle:event, const String:name[], bool:dontBroadcast)
{
    live = 1;
}

public Action:Event_WinPanel(Handle:event, const String:name[], bool:dontBroadcast)
{
    live = 0;
}
