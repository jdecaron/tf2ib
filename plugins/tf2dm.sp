#pragma semicolon 1
#include <sourcemod>
#include <sdktools>
#include <tf2_stocks>
#include <dukehacks>
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
new Handle:g_hCrits = INVALID_HANDLE;
new bool:g_bCrits = false;
new Handle:g_hSpawn = INVALID_HANDLE;
new Float:g_fSpawn = 1.5;
new Handle:g_hSpawnRandom = INVALID_HANDLE;
new bool:g_bSpawnRandom = true;
new bool:g_bSpawnMap;
new Handle:g_hRedSpawns = INVALID_HANDLE;
new Handle:g_hBluSpawns = INVALID_HANDLE;
new Handle:g_hKritzDelay = INVALID_HANDLE;
new Float:g_fKritzDelay = 30.0;
new Handle:g_hKritzDuration = INVALID_HANDLE;
new g_iKritzDuration = 20;
new Handle:g_hKritzSpawn = INVALID_HANDLE;
new Float:g_fKritzSpawn = 90.0;
new bool:g_bKritz;
new bool:g_bKritzFirst;
new Float:g_vecKritz[3];
new g_iKritz;
new g_iKritzPlayer;
new Float:g_vecDown[3] = {90.0, 0.0, 0.0};
new g_iRounds;
new g_iMaxClips1[32] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
new g_iMaxClips2[32] = {-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1};
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
	g_hKritzDelay = CreateConVar("tf2dm_kritzdelay", "30", "How long after round starts before kritz spawns.", FCVAR_PLUGIN|FCVAR_NOTIFY);
	g_hKritzDuration = CreateConVar("tf2dm_kritzduration", "20", "How long kritz lasts.", FCVAR_PLUGIN|FCVAR_NOTIFY);
	g_hKritzSpawn = CreateConVar("tf2dm_kritzspawn", "90", "Time between kritz spawns.", FCVAR_PLUGIN|FCVAR_NOTIFY);
	g_hCrits = CreateConVar("tf2dm_crits", "0", "Enable random crits.", FCVAR_PLUGIN|FCVAR_NOTIFY);
	g_hSpawn = CreateConVar("tf2dm_spawn", "1.5", "Spawn timer.", FCVAR_PLUGIN|FCVAR_NOTIFY);
	g_hSpawnRandom = CreateConVar("tf2dm_spawnrandom", "1", "Enable random spawns.", FCVAR_PLUGIN|FCVAR_NOTIFY);
	HookConVarChange(g_hRegenEnable, Cvar_regenenable);
	HookConVarChange(g_hRegenHP, Cvar_regenhp);
	HookConVarChange(g_hRegenTick, Cvar_regentick);
	HookConVarChange(g_hRegenDelay, Cvar_regendelay);
	HookConVarChange(g_hRegenKill, Cvar_regenkill);
	HookConVarChange(g_hKritzDelay, Cvar_kritzdelay);
	HookConVarChange(g_hKritzDuration, Cvar_kritzduration);
	HookConVarChange(g_hKritzSpawn, Cvar_kritzspawn);
	HookConVarChange(g_hCrits, Cvar_crits);
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
			KvGetVector(g_hKv, "kritz", g_vecKritz);
			g_bKritz = g_vecKritz[0]!=0.0||g_vecKritz[1]!=0.0||g_vecKritz[2]!=0.0;
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
	g_fKritzDelay = GetConVarFloat(g_hKritzDelay);
	g_iKritzDuration = GetConVarInt(g_hKritzDuration);
	g_fKritzSpawn = GetConVarFloat(g_hKritzSpawn);
	g_bCrits = GetConVarBool(g_hCrits);
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
public Cvar_kritzdelay(Handle:convar, const String:oldValue[], const String:newValue[]) {
	g_fKritzDelay = GetConVarFloat(g_hKritzDelay);
}
public Cvar_kritzduration(Handle:convar, const String:oldValue[], const String:newValue[]) {
	g_iKritzDuration = GetConVarInt(g_hKritzDuration);
}
public Cvar_kritzspawn(Handle:convar, const String:oldValue[], const String:newValue[]) {
	g_fKritzSpawn = GetConVarFloat(g_hKritzSpawn);
}
public Cvar_crits(Handle:convar, const String:oldValue[], const String:newValue[]) {
	g_bCrits = GetConVarBool(g_hCrits);
}
public Cvar_spawn(Handle:convar, const String:oldValue[], const String:newValue[]) {
	g_fSpawn = GetConVarFloat(g_hSpawn);
}
public Cvar_spawnrandom(Handle:convar, const String:oldValue[], const String:newValue[]) {
	g_bSpawnRandom = GetConVarBool(g_hSpawnRandom);
}
public Action:ThinkHook(entity) {
	if(DistFromGround(entity)<10) {
		AcceptEntityInput(g_iKritz, "DisableMotion");
		dhUnHookEntity(entity, EHK_VPhysicsUpdate);
		return Plugin_Handled;
	}
	decl Float:vecAngles[3];
	GetEntPropVector(entity, Prop_Send, "m_angRotation", vecAngles);
	vecAngles[0] = 0.0;
	vecAngles[2] = 0.0;
	TeleportEntity(entity, NULL_VECTOR, vecAngles, NULL_VECTOR);
	return Plugin_Continue;
}
public Action:TouchHook(ent, other) {
	if(ent==g_iKritz && other<=MaxClients) {
		RemoveEdict(g_iKritz);
		g_iKritzPlayer = other;
		if(g_bKritzFirst) {
			KritzCount(INVALID_HANDLE, g_iKritzDuration);
			CreateTimer(g_fKritzSpawn, KritzSpawn, _, TIMER_FLAG_NO_MAPCHANGE);
			g_bKritzFirst = false;
		}
	}
	return Plugin_Continue;
}
public Action:TF2_CalcIsAttackCritical(client, weapon, String:weaponname[], &bool:result) {
	if(client==g_iKritzPlayer) {
		result = true;
		return Plugin_Changed;
	}
	if(g_bCrits)
		return Plugin_Continue;
	result = false;
	return Plugin_Changed;
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
public Action:KritzSpawn(Handle:timer) {
	CreateKritz();
	TeleportEntity(g_iKritz, g_vecKritz, NULL_VECTOR, NULL_VECTOR);
	AcceptEntityInput(g_iKritz, "DisableMotion");
	g_bKritzFirst = true;
}
public Action:KritzCount(Handle:timer, any:count) {
	if(count>0) {
		if(g_iKritzPlayer!=-1)
			PrintCenterText(g_iKritzPlayer, "%i", count);
		CreateTimer(1.0, KritzCount, --count);
	} else {
		if(g_iKritzPlayer==-1) {
			RemoveEdict(g_iKritz);
		} else {
			PrintCenterText(g_iKritzPlayer, "");
			g_iKritzPlayer = -1;
		}
	}
}
public Action:Event_player_death(Handle:event, const String:name[], bool:dontBroadcast) {
	new client = GetClientOfUserId(GetEventInt(event, "userid"));
	CreateTimer(g_fSpawn, Respawn, client);
    new attacker = GetClientOfUserId(GetEventInt(event, "attacker"));
    if(GetClassID(attacker) != 2 && GetClassID(attacker) != 7)
    {
        SetEntProp(GetPlayerWeaponSlot(attacker, 0), Prop_Send, "m_iClip1", g_iMaxClips1[attacker - 1]);
        SetEntProp(GetPlayerWeaponSlot(attacker, 0), Prop_Data, "m_iClip1", g_iMaxClips1[attacker - 1]);
        SetEntProp(GetPlayerWeaponSlot(attacker, 1), Prop_Send, "m_iClip1", g_iMaxClips2[attacker - 1]);
        SetEntProp(GetPlayerWeaponSlot(attacker, 1), Prop_Data, "m_iClip1", g_iMaxClips2[attacker - 1]);
        SetEntProp(attacker, Prop_Send, "m_iHealth", GetMaxHealth(attacker));
        SetEntProp(attacker, Prop_Data, "m_iHealth", GetMaxHealth(attacker));
    }
	if(g_bRegenKill) {
		if(attacker>0 && attacker!=client && !g_bRegen[attacker]){
			StartRegen(INVALID_HANDLE, attacker);
        }
	}
	if(client==g_iKritzPlayer) {
		PrintCenterText(client, "");
		decl Float:vecOrigin[3], Float:vecVelocity[3];
		GetClientAbsOrigin(client, vecOrigin);
		vecOrigin[2] += 40.0;
		GetEntPropVector(client, Prop_Data, "m_vecVelocity", vecVelocity);
		vecVelocity[2] = 300.0;
		CreateKritz();
		dhHookEntity(g_iKritz, EHK_VPhysicsUpdate, ThinkHook);
		TeleportEntity(g_iKritz, vecOrigin, NULL_VECTOR, vecVelocity);
		g_iKritzPlayer = -1;
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

    g_iMaxClips1[client - 1] = GetEntProp(GetPlayerWeaponSlot(client, 0), Prop_Data, "m_iClip1");
    g_iMaxClips2[client - 1] = GetEntProp(GetPlayerWeaponSlot(client, 1), Prop_Data, "m_iClip1");

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
	if(g_bKritz && g_iRounds++!=0) {
		if(g_fKritzDelay==0.0) {
			KritzSpawn(INVALID_HANDLE);
		} else {
			CreateTimer(g_fKritzDelay, KritzSpawn, _, TIMER_FLAG_NO_MAPCHANGE);
		}
	}
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
CreateKritz() {
	g_iKritz = CreateEntityByName("prop_physics_override");
	SetEntityModel(g_iKritz, "models/tf2dm/tf2logo1.mdl");
	SetEntityMoveType(g_iKritz, MOVETYPE_VPHYSICS);
	SetEntProp(g_iKritz, Prop_Data, "m_CollisionGroup", 0);
	SetEntProp(g_iKritz, Prop_Data, "m_usSolidFlags", 28);
	SetEntProp(g_iKritz, Prop_Data, "m_nSolidType", 6);
	DispatchSpawn(g_iKritz);
	dhHookEntity(g_iKritz, EHK_Touch, TouchHook);
}
