#pragma semicolon 1
#include <sourcemod>
#include <sdktools>
#include <tf2_stocks>
#define PL_VERSION "1.5"
new Handle:g_hKv = INVALID_HANDLE;
new bool:g_bRegen[MAXPLAYERS+1];
new Handle:g_hRegenTimer[MAXPLAYERS+1];
new Handle:g_hRegenEnable = INVALID_HANDLE;
new bool:g_bRegenEnable = true;
new Handle:g_hRegenHP = INVALID_HANDLE;
new g_iRegenHP = 1;
new Handle:g_hRegenTick = INVALID_HANDLE;
new Float:g_fRegenTick = 0.1;
new Handle:g_hRegenDelay = INVALID_HANDLE;
new Float:g_fRegenDelay = 4.0;
new Handle:g_hRegenKill = INVALID_HANDLE;
new bool:g_bRegenKill = true;
new Handle:g_hSpawn = INVALID_HANDLE;
new Float:g_fSpawn = 1.5;
new Handle:g_hSpawnRandom = INVALID_HANDLE;
new bool:g_bSpawnRandom = true;
new bool:g_bSpawnMap;
new Handle:g_hRedSpawns = INVALID_HANDLE;
new Handle:g_hBluSpawns = INVALID_HANDLE;
new Float:g_vecDown[3] = {90.0, 0.0, 0.0};
public Plugin:myinfo =
{
    name = "TF2 Deathmatch",
    author = "MikeJS",
    description = "I wonder",
    version = PL_VERSION,
    url = "http://www.mikejsavage.com/"
};
public OnPluginStart() {
    CreateConVar("tf2dm", PL_VERSION, "TF2 Deathmatch version.", FCVAR_PLUGIN|FCVAR_SPONLY|FCVAR_REPLICATED|FCVAR_NOTIFY);
    g_hRegenEnable = CreateConVar("tf2dm_regen", "1", "Enable health regeneration.", FCVAR_PLUGIN|FCVAR_NOTIFY);
    g_hRegenHP = CreateConVar("tf2dm_regenhp", "1", "Health added per regeneration tick.", FCVAR_PLUGIN|FCVAR_NOTIFY);
    g_hRegenTick = CreateConVar("tf2dm_regentick", "0.1", "Delay between regeration ticks.", FCVAR_PLUGIN|FCVAR_NOTIFY);
    g_hRegenDelay = CreateConVar("tf2dm_regendelay", "4.0", "Seconds after damage before regeneration.", FCVAR_PLUGIN|FCVAR_NOTIFY);
    g_hRegenKill = CreateConVar("tf2dm_regenkill", "1", "Enable instaregen after a kill.", FCVAR_PLUGIN|FCVAR_NOTIFY);
    g_hSpawn = CreateConVar("tf2dm_spawn", "1.5", "Spawn timer.", FCVAR_PLUGIN|FCVAR_NOTIFY);
    g_hSpawnRandom = CreateConVar("tf2dm_spawnrandom", "1", "Enable random spawns.", FCVAR_PLUGIN|FCVAR_NOTIFY);
    HookConVarChange(g_hRegenEnable, Cvar_regenenable);
    HookConVarChange(g_hRegenHP, Cvar_regenhp);
    HookConVarChange(g_hRegenTick, Cvar_regentick);
    HookConVarChange(g_hRegenDelay, Cvar_regendelay);
    HookConVarChange(g_hRegenKill, Cvar_regenkill);
    HookConVarChange(g_hSpawn, Cvar_spawn);
    HookConVarChange(g_hSpawnRandom, Cvar_spawnrandom);
    HookEvent("player_death", Event_player_death);
    HookEvent("player_hurt", Event_player_hurt);
    HookEvent("player_say", Event_PlayerSay);
    HookEvent("player_spawn", Event_player_spawn);
    HookEvent("teamplay_round_start", Event_round_start);
    HookEvent("teamplay_restart_round", Event_round_start);
    g_hRedSpawns = CreateArray();
    g_hBluSpawns = CreateArray();
}
public OnMapStart() {
    ClearArray(g_hRedSpawns);
    ClearArray(g_hBluSpawns);
    for(new i=0;i<MAXPLAYERS;i++) {
        PushArrayCell(g_hRedSpawns, CreateArray(6));
        PushArrayCell(g_hBluSpawns, CreateArray(6));
    }
    g_bSpawnMap = false;
    if(g_hKv!=INVALID_HANDLE)
        CloseHandle(g_hKv);
    g_hKv = CreateKeyValues("Spawns");
    decl String:path[256];
    BuildPath(Path_SM, path, sizeof(path), "configs/tf2dm.cfg");
    if(FileExists(path)) {
        FileToKeyValues(g_hKv, path);
        decl String:map[64];
        GetCurrentMap(map, sizeof(map));
        if(KvJumpToKey(g_hKv, map)) {
            g_bSpawnMap = true;
            KvGotoFirstSubKey(g_hKv);
            decl String:players[4], Float:vectors[6], Float:origin[3], Float:angles[3];
            new iplayers;
            do {
                KvGetSectionName(g_hKv, players, sizeof(players));
                iplayers = StringToInt(players);
                if(KvJumpToKey(g_hKv, "red")) {
                    KvGotoFirstSubKey(g_hKv);
                    do {
                        KvGetVector(g_hKv, "origin", origin);
                        KvGetVector(g_hKv, "angles", angles);
                        vectors[0] = origin[0];
                        vectors[1] = origin[1];
                        vectors[2] = origin[2];
                        vectors[3] = angles[0];
                        vectors[4] = angles[1];
                        vectors[5] = angles[2];
                        for(new i=iplayers;i<MAXPLAYERS;i++)
                            PushArrayArray(GetArrayCell(g_hRedSpawns, i), vectors);
                    } while(KvGotoNextKey(g_hKv));
                    KvGoBack(g_hKv);
                    KvGoBack(g_hKv);
                } else {
                    SetFailState("Red spawns missing. Map: %s  Players: %i", map, iplayers);
                }
                if(KvJumpToKey(g_hKv, "blue")) {
                    KvGotoFirstSubKey(g_hKv);
                    do {
                        KvGetVector(g_hKv, "origin", origin);
                        KvGetVector(g_hKv, "angles", angles);
                        vectors[0] = origin[0];
                        vectors[1] = origin[1];
                        vectors[2] = origin[2];
                        vectors[3] = angles[0];
                        vectors[4] = angles[1];
                        vectors[5] = angles[2];
                        for(new i=iplayers;i<MAXPLAYERS;i++)
                            PushArrayArray(GetArrayCell(g_hBluSpawns, i), vectors);
                    } while(KvGotoNextKey(g_hKv));
                } else {
                    SetFailState("Blue spawns missing. Map: %s  Players: %i", map, iplayers);
                }
            } while(KvGotoNextKey(g_hKv));
        }
    } else {
        LogError("File Not Found: %s", path);
    }
    //PrecacheModel("models/tf2dm/tf2logo1.mdl", true);
    PrecacheSound("items/spawn_item.wav", true);
}
public OnConfigsExecuted() {
    g_bRegenEnable = GetConVarBool(g_hRegenEnable);
    g_iRegenHP = GetConVarInt(g_hRegenHP);
    g_fRegenTick = GetConVarFloat(g_hRegenTick);
    g_fRegenDelay = GetConVarFloat(g_hRegenDelay);
    g_bRegenKill = GetConVarBool(g_hRegenKill);
    g_fSpawn = GetConVarFloat(g_hSpawn);
    g_bSpawnRandom = GetConVarBool(g_hSpawnRandom);
}
public Cvar_regenenable(Handle:convar, const String:oldValue[], const String:newValue[]) {
    g_bRegenEnable = GetConVarBool(g_hRegenEnable);
}
public Cvar_regenhp(Handle:convar, const String:oldValue[], const String:newValue[]) {
    g_iRegenHP = GetConVarInt(g_hRegenHP);
}
public Cvar_regentick(Handle:convar, const String:oldValue[], const String:newValue[]) {
    g_fRegenTick = GetConVarFloat(g_hRegenTick);
}
public Cvar_regendelay(Handle:convar, const String:oldValue[], const String:newValue[]) {
    g_fRegenDelay = GetConVarFloat(g_hRegenDelay);
}
public Cvar_regenkill(Handle:convar, const String:oldValue[], const String:newValue[]) {
    g_bRegenKill = GetConVarBool(g_hRegenKill);
}
public Cvar_spawn(Handle:convar, const String:oldValue[], const String:newValue[]) {
    g_fSpawn = GetConVarFloat(g_hSpawn);
}
public Cvar_spawnrandom(Handle:convar, const String:oldValue[], const String:newValue[]) {
    g_bSpawnRandom = GetConVarBool(g_hSpawnRandom);
}
public Action:Event_PlayerSay(Handle:event, const String:name[], bool:dontBroadcast)
{
    decl String:userText[192];
    userText[0] = '\0';
    if (!GetEventString(event, "text", userText, 192))
    {
        return Plugin_Continue;
    }

    if(StrContains(userText, "!position") == 0)
    {
        new Float:clientAngles[3];
        new Float:clientPosition[3];
        GetClientAbsOrigin(GetClientOfUserId(GetEventInt(event, "userid")), clientPosition);
        GetClientAbsAngles(GetClientOfUserId(GetEventInt(event, "userid")), clientAngles);

        PrintToChatAll("Position : %f %f %f", clientPosition[0], clientPosition[1], clientPosition[2]);
        PrintToChatAll("Angles : %f %f %f", clientAngles[0], clientAngles[1], clientAngles[2]);
    }

    return Plugin_Continue;
}
public Action:RandomSpawn(Handle:timer, any:client) {
    if(IsClientInGame(client) && IsPlayerAlive(client)) {
        new team = GetClientTeam(client), Handle:array, size, Handle:spawns = CreateArray(), count = GetClientCount();
        decl Float:vectors[6], Float:origin[3], Float:angles[3];
        if(team==2) {
            for(new i=0;i<=count;i++) {
                array = GetArrayCell(g_hRedSpawns, i);
                if(GetArraySize(array)!=0)
                    size = PushArrayCell(spawns, array);
            }
        } else {
            for(new i=0;i<=count;i++) {
                array = GetArrayCell(g_hBluSpawns, i);
                if(GetArraySize(array)!=0)
                    size = PushArrayCell(spawns, array);
            }
        }
        array = GetArrayCell(spawns, GetRandomInt(0, GetArraySize(spawns)-1));
        size = GetArraySize(array);
        GetArrayArray(array, GetRandomInt(0, size-1), vectors);
        CloseHandle(spawns);
        origin[0] = vectors[0];
        origin[1] = vectors[1];
        origin[2] = vectors[2];
        angles[0] = vectors[3];
        angles[1] = vectors[4];
        angles[2] = vectors[5];
        TeleportEntity(client, origin, angles, NULL_VECTOR);
        EmitAmbientSound("items/spawn_item.wav", origin);
    }
}
public Action:StartRegen(Handle:timer, any:client) {
    g_bRegen[client] = true;
    Regen(INVALID_HANDLE, client);
}
public Action:Regen(Handle:timer, any:client) {
    if(g_bRegen[client] && IsClientInGame(client) && IsPlayerAlive(client)) {
        new health = GetClientHealth(client)+g_iRegenHP;
        if(health>GetMaxHealth(client))
            health = GetMaxHealth(client);
        SetEntProp(client, Prop_Send, "m_iHealth", health, 1);
        SetEntProp(client, Prop_Data, "m_iHealth", health, 1);
        g_hRegenTimer[client] = CreateTimer(g_fRegenTick, Regen, client);
    } else {
        g_hRegenTimer[client] = INVALID_HANDLE;
    }
}
public Action:Respawn(Handle:timer, any:client) {
    if(IsClientInGame(client) && IsClientOnTeam(client))
        TF2_RespawnPlayer(client);
}
public Action:Event_player_death(Handle:event, const String:name[], bool:dontBroadcast) {
    new client = GetClientOfUserId(GetEventInt(event, "userid"));
    CreateTimer(g_fSpawn, Respawn, client);
    new attacker = GetClientOfUserId(GetEventInt(event, "attacker"));
    if(GetClassID(attacker) != 2 && GetClassID(attacker) != 7)
    {
        SetEntProp(attacker, Prop_Send, "m_iHealth", GetMaxHealth(attacker));
        SetEntProp(attacker, Prop_Data, "m_iHealth", GetMaxHealth(attacker));
    }
    if(g_bRegenKill) {
        if(attacker>0 && attacker!=client && !g_bRegen[attacker]){
            StartRegen(INVALID_HANDLE, attacker);
        }
    }
}
public Action:Event_player_hurt(Handle:event, const String:name[], bool:dontBroadcast) {
    if(g_bRegenEnable) {
        new client = GetClientOfUserId(GetEventInt(event, "userid"));
        new attacker = GetClientOfUserId(GetEventInt(event, "attacker"));
        if(client!=attacker && attacker!=0) {
            g_bRegen[client] = false;
            if(g_hRegenTimer[client]!=INVALID_HANDLE) {
                KillTimer(g_hRegenTimer[client]);
                g_hRegenTimer[client] = INVALID_HANDLE;
            }
            g_hRegenTimer[client] = CreateTimer(g_fRegenDelay, StartRegen, client);
        }
    }
}
public Action:Event_player_spawn(Handle:event, const String:name[], bool:dontBroadcast) {
    new client = GetClientOfUserId(GetEventInt(event, "userid"));
    g_hRegenTimer[client] = CreateTimer(0.01, StartRegen, client);
    if(g_bSpawnRandom && g_bSpawnMap) {
        CreateTimer(0.01, RandomSpawn, client);
    } else {
        decl Float:vecOrigin[3];
        GetClientEyePosition(client, vecOrigin);
        EmitAmbientSound("items/spawn_item.wav", vecOrigin);
    }
}
public Action:Event_round_start(Handle:event, const String:name[], bool:dontBroadcast) {
    new ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "team_round_timer"))!=-1)
        AcceptEntityInput(ent, "Disable");
    ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "func_regenerate"))!=-1)
        AcceptEntityInput(ent, "Disable");
    ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "team_control_point_master"))!=-1)
        AcceptEntityInput(ent, "Disable");
    ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "team_control_point"))!=-1)
        AcceptEntityInput(ent, "Disable");
    ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "trigger_capture_area"))!=-1)
        AcceptEntityInput(ent, "Disable");
    /*ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "tf_logic_arena"))!=-1)
        RemoveEdict(ent);
    ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "item_medkit_small"))!=-1)
        AcceptEntityInput(ent, "Disable");
    ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "item_medkit_medium"))!=-1)
        AcceptEntityInput(ent, "Disable");
    ent = MaxClients+1;
    while((ent = FindEntityByClassname(ent, "item_medkit_large"))!=-1)
        AcceptEntityInput(ent, "Disable");*/
    for(new i=0;i<=MaxClients;i++)
        if(g_hRegenTimer[i]!=INVALID_HANDLE)
            KillTimer(g_hRegenTimer[i]);
}
GetClassID(client) {
    new class = _:TF2_GetPlayerClass(client);
    switch(class) {
        case 1: return 1;
        case 2: return 2;
        case 3: return 3;
        case 4: return 4;
        case 5: return 5;
        case 6: return 6;
        case 7: return 7;
        case 8: return 8;
        case 9: return 9;
    }
    return -1;
}
GetMaxHealth(client) {
    new class = _:TF2_GetPlayerClass(client);
    switch(class) {
        case 1: return 125;
        case 2: return 125;
        case 3: return 200;
        case 4: return 175;
        case 5: return 150;
        case 6: return 300;
        case 7: return 175;
        case 8: return 125;
        case 9: return 125;
    }
    return -1;
}
IsClientOnTeam(client) {
    new team = GetClientTeam(client);
    return team==2||team==3;
}
Float:DistFromGround(ent) {
    decl Float:vecOrigin[3], Float:vecPos[3], Float:dist; 
    GetEntPropVector(ent, Prop_Send, "m_vecOrigin", vecOrigin);
    new Handle:trace = TR_TraceRayFilterEx(vecOrigin, g_vecDown, CONTENTS_SOLID|CONTENTS_MOVEABLE, RayType_Infinite, TraceEntityFilterPlayers, ent); 
    if(TR_DidHit(trace)) { 
        TR_GetEndPosition(vecPos, trace);
        dist = vecOrigin[2]-vecPos[2];
    } else {
        dist = -1.0;
    }
    CloseHandle(trace);
    return dist;
}
public bool:TraceEntityFilterPlayers(entity, contentsMask, any:ent) {
    return entity>MaxClients;
}
