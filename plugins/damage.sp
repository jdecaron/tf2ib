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

public OnMapStart()
{
    live = -1;
}

public OnPluginStart()
{
    HookEvent("player_hurt", Event_PlayerHurt);
    HookEvent("teamplay_round_start", Event_RoundStart);
    HookEvent("teamplay_win_panel", Event_WinPanel);
}

public Event_PlayerHurt(Handle:event, const String:name[], bool:dontBroadcast)
{
    if(live == 1)
    {
        decl String:clientname[32];
        decl String:steamid[64];
        decl String:team[64];

        new userid = GetClientOfUserId(GetEventInt(event, "userid"));
        new attackerid = GetEventInt(event, "attacker");
        new attacker = GetClientOfUserId(attackerid);
        new damage = GetEventInt(event, "damageamount");
        if(userid != attacker && attacker != 0)
        {
            GetClientAuthString(attacker, steamid, sizeof(steamid));
            GetClientName(attacker, clientname, sizeof(clientname));
            new teamindex = GetClientTeam(attacker);
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
            LogToGame("\"%s<%d><%s><%s>\" triggered \"damage\" %d",
                clientname,
                attackerid,
                steamid,
                team,
                damage);
        }
    }
}

public Action:Event_RoundStart(Handle:event, const String:name[], bool:dontBroadcast)
{
    if(live == -1)
    {
        live = 0
    }
    else
    {
        live = 1;
    }
}

public Action:Event_WinPanel(Handle:event, const String:name[], bool:dontBroadcast)
{
    live = 0;
}
