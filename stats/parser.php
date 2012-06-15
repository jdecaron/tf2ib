<?php

// TF2 Log Parser
// file: parser.php
// author: rusty fausak
// date: dec 18 2007
// rev: v1.1 jan 2 2008
// desc: This file contains functions used in parsing TF2 server logs. The main
//       purpose of this file is to parse a log in a directory and output .html
//       files in that directory that contain formatted, informative output.
// v1.1: Valve changed several things about logs. They added 'position' for
//       attackers and victims, and also for some other events, like builtobj
//       and killedobj.

include_once 'page.php';

// This function accepts a directory and a ready word as input and looks for a
// log file in that directory. It parses that log and outputs the formatted
// .html files it creates in that directory.
// WARNING: SLOW! 300ms computation time on average!
function parse ($directory, $ready_word) {
    global $database;

	$log_file = '';

	// Get a list of the files in the directory
	$files = scandir($directory);

	// Find the .log file to parse (must be alphanumeric/underscores)
	foreach ($files as $file) {
		if (preg_match('/^\w+\.log$/',$file)) {
			$log_file = $file;
			break;
		}
	}

	// Make sure we found a log file
	if (!strcmp($log_file,'')) { return 0; }

	// Read the whole log into a variable
	$log = file($directory . "/" . $log_file);

	// p array contains most of the information to be extracted for each player
	$p = array();

	// c array contains the capture point information
	$c = array();

	// Ready word check and logic
	$ready = 0;
	$ready_red = 0;
	$ready_blue = 0;
	$clanbattle = 1;
	if (!strcmp($ready_word,'')) {
		$ready = 1;
		$clanbattle = 0;
	}

	// Team swap vars
	$swap = 0;
	$reversed = 0;

	// Find out if the ready word was said by both teams, if not, turn off clanbattle and set ready=1
	$check_ready['Red'] = 0;
	$check_ready['Blue'] = 0;
	foreach ($log as $num => $line) {
		if ($ready) { break; }
		if (preg_match("/<Blue>\" say \"{$ready_word}\"\s+$/",$line,$m)) { $check_ready['Blue'] = 1; }
		else if (preg_match("/<Red>\" say \"{$ready_word}\"\s+$/",$line,$m)) { $check_ready['Red'] = 1; }
	}
	if ((!$ready) && ((!$check_ready['Blue']) || (!$check_ready['Red']))) {
		$ready = 1;
		$clanbattle = 0;
	}

	// Beginning stamp
	$basestamp = 0;

	// Read file line by line
    $fileClosed = 0;
    $statsIndex = array();
    $tvFileName = '';
    $tvRecorded = 0;
	foreach ($log as $num => $line) {

		// Whole-line scoped variables
		$date = array();
		$event = '';

		// ready logic
		if ($ready_red && $ready_blue && (!$ready)) {
			$ready = 1;
			// Reset last_stamp for each player
			foreach ($p as $id => $arr) {
				$p[$id]['role']['last_stamp'] = $stamp;
			}
		}

		if (preg_match('/^L (\d{2})\/(\d{2})\/(\d{4}) - (\d{2}):(\d{2}):(\d{2}): tv_record/',$line,$m)) {
			$tvRecorded = 1;
            $tvFileName = explode(' ', $line);
            $tvFileName = $tvFileName[count($tvFileName) - 1];
		}

		if (preg_match('/^L (\d{2})\/(\d{2})\/(\d{4}) - (\d{2}):(\d{2}):(\d{2}): Log file closed$/',$line,$m)) {
			$fileClosed = 1;
		}

		// Check format of the left side of the line where the date and time is
		// example: 'L 12/18/2007 - 20:38:34: <logged event here>'
		if (preg_match('/^L (\d{2})\/(\d{2})\/(\d{4}) - (\d{2}):(\d{2}):(\d{2}): (.+?)$/',$line,$m)) {
			$date = $m;
		}
		else { continue; }

		$date_month = $date[1];
		$date_day = $date[2];
		$date_year = $date[3];
		$date_hour = $date[4];
		$date_minute = $date[5];
		$date_second = $date[6];
        if(!$fullDate)
            $fullDate = strtotime($date[1] . '/' . $date[2] . '/' . $date[3] . ' ' . $date[4] . ':' . $date[5] . ':' . $date[6]);
		$stamp = ($date_day * 24 * 60 * 60) + ($date_hour * 60 * 60) + ($date_minute * 60) + $date_second;
		$event = $date[7];

		if ($ready && (!$basestamp)) { $basestamp = $stamp; $c['list'][$basestamp . 'z'] = "===RESET==="; }

		// ---------------------------------------------------------------------
		// Player actions
		// example: "|RES|Born_In_Xixax<24><STEAM_0:1:99375><Blue>" changed role to "soldier"
		// ---------------------------------------------------------------------
		if (preg_match('/^"(.+?)<\d+><STEAM_(\d:\d:\d+)><(\w*)>" (.+?)$/',$event,$m)) {
			$alias = $m[1];
			$id = $m[2];
			$team = $m[3];
			$action = $m[4];

            if(!in_array($alias, $statsIndex)){
                $statsIndex[] = $alias;
            }
            if(!in_array($id, $statsIndex)){
                $statsIndex[] = $id;
            }

			// Ready logic
			if ($readyRed && $readyBlue && (!$ready)) { $ready = 1; }

			// Set the player's team if ready and not set before, otherwise add
			// the time played on a team to the total
			if ((!strcmp($team,'Red') || !strcmp($team,'Blue')) && $ready) {
				if (!isset($p[$id]['team']['initial'])) {
					$p[$id]['team']['initial'] = $team;
					$p[$id]['team']['last'] = $team;
					$p[$id]['team']['last_stamp'] = $stamp;
				}
				else {
					$p[$id]['team'][$p[$id]['team']['last']] += ($stamp - $p[$id]['team']['last_stamp']);
					// Reverse the team if reverse is on
					if ($reversed) {
						if (!strcmp($team,'Red')) { $team = 'Blue'; }
						else if (!strcmp($team,'Blue')) { $team = 'Red'; }
						else { $team = 'Unknown'; }
						$p[$id]['team']['last'] = $team;
						$p[$id]['team']['last_stamp'] = $stamp;
					}
					else {
						$p[$id]['team']['last'] = $team;
						$p[$id]['team']['last_stamp'] = $stamp;
					}
				}
			}

			// Increment this alias in the list of aliases a player has
			$p[$id]['aliases'][$alias]++;

			// Set the player's role if not set before
			if (!isset($p[$id]['role']['last'])) {
				$p[$id]['role']['last'] = 'unknown';
				$p[$id]['role']['last_stamp'] = $stamp;
			}

			// Add this role time to the total if ready
			if ($ready) {
				$p[$id]['role'][$p[$id]['role']['last']] += $stamp - $p[$id]['role']['last_stamp'];
				$p[$id]['role']['last_stamp'] = $stamp;
			}
			// Otherwise update the last stamp
			else {
				$p[$id]['role']['last_stamp'] = $stamp;
			}

			// -----------------------------------------------------------------
			// joined team
			// -----------------------------------------------------------------
			if (preg_match('/^joined team "(.+?)"\s+$/',$action,$m)) { $swap++; }
			else { $swap = 0; }

			// Swap logic
			if ($swap > max(2,(sizeof($p) / 2 + 1))) {
				$swap = 0;
				if ($reversed) { $reversed = 0; }
				else { $reversed = 1; }
				// Capture point resets
				if (!is_array($c['list'])) { $c['list'] = array(); }
				$char = 'a';
				while (array_key_exists($stamp . $char,$c['list'])) { $char++; }
				$c['list'][$stamp . $char] = "===RESET===";
			}

			// -----------------------------------------------------------------
			// say
			// -----------------------------------------------------------------
			if (preg_match('/^say "(.+)"\s*$/',$action,$m)) {

				// Ready word logic
				if ((!$ready) && (!strcmp($m[1],$ready_word))) {
					if (!strcmp($team,'Red')) { $ready_red = 1; }
					if (!strcmp($team,'Blue')) { $ready_blue = 1; }
				}

				// Player mm1 array
				if (!is_array($p[$id]['mm1'])) { $p[$id]['mm1'] = array(); }
				$char = 'a';
				while (array_key_exists($stamp . $char,$p[$id]['mm1'])) { $char++; }
				$p[$id]['mm1'][$stamp . $char] = $m[1];
			}

			// -----------------------------------------------------------------
			// say_team
			// -----------------------------------------------------------------
			else if (preg_match('/^say_team "(.+)"\s*$/',$action,$m)) {

				// Player mm2 array
				if (!is_array($p[$id]['mm2'])) { $p[$id]['mm2'] = array(); }
				$char = 'a';
				while (array_key_exists($stamp . $char,$p[$id]['mm2'])) { $char++; }
				$p[$id]['mm2'][$stamp . $char] = $m[1];
			}

			// -----------------------------------------------------------------
			// killed
			// L 01/03/2008 - 21:29:46:
			//  "|RES|spike<13><STEAM_0:1:303223><Blue>" killed "[CSTF]Quixotic<28><STEAM_0:1:869256><Red>"
			//  with "shotgun_soldier" (customkill "headshot") (attacker_position "1311 -481 -68") (victim_position "1497 -362 24")
			// -----------------------------------------------------------------
			else if (preg_match('/^killed ".+?<\d+><STEAM_(\d:\d:\d+)><\w+>" with "(.+?)"\s*(.*)$/',$action,$m)) {

				// Skip if not ready
				if (!$ready) { continue; }

				// Victim id
				$vid = $m[1];
				$weapon = $m[2];
				$custom = $m[3];

				// Find the current role and update role array
				$role = weapon_to_role($weapon);
				if ($role) { $p[$id]['role']['last'] = $role; }

				// Customkill logic
				if (strpos($custom,'backstab')) {
					$weapon = 'backstab';
					$p[$id]['roles'][$p[$id]['role']['last']]['backstabs']++;
					$p[$id]['roles']['all']['backstabs']++;
				}
				else if (strpos($custom,'headshot')) {
					$weapon = 'headshot';
					$p[$id]['roles'][$p[$id]['role']['last']]['headshots']++;
					$p[$id]['roles']['all']['headshots']++;
				}
				else { $custom = ''; }

				// Update kills arrays
				$p[$id]['roles'][$p[$id]['role']['last']]['kills']++;
				$p[$id]['roles']['all']['kills']++;
				$p[$id]['weapons'][$weapon]['kills']++;
				$p[$id]['weapons']['all']['kills']++;
				$p[$id]['enemies'][$vid]['weapons'][$weapon]['kills']++;
				$p[$id]['enemies'][$vid]['weapons']['all']['kills']++;

				// Update deaths in victim arrays
				$p[$vid]['roles'][$p[$vid]['role']['last']]['deaths']++;
				$p[$vid]['roles']['all']['deaths']++;
				$p[$vid]['weapons'][$weapon]['deaths']++;
				$p[$vid]['weapons']['all']['deaths']++;
				$p[$vid]['enemies'][$id]['weapons'][$weapon]['deaths']++;
				$p[$vid]['enemies'][$id]['weapons']['all']['deaths']++;
			}

			// -----------------------------------------------------------------
			// changed role
			// -----------------------------------------------------------------
			else if (preg_match('/^changed role to "(.+?)"\s*$/',$action,$m)) {
				$p[$id]['role']['last'] = $m[1];
			}

			// -----------------------------------------------------------------
			// committed suicide
			// -----------------------------------------------------------------
			else if (preg_match('/^committed suicide with "(.+?)"/',$action,$m)) {

				// Skip if not ready
				if (!$ready) { continue; }

				$weapon = $m[1];

				// Find the current role and update role array
				$role = weapon_to_role($weapon);
				if ($role) { $p[$id]['role']['last'] = $role; }

				// Update suicides arrays
				$p[$id]['roles'][$p[$id]['role']['last']]['suicides']++;
				$p[$id]['roles']['all']['suicides']++;
				$p[$id]['weapons'][$weapon]['suicides']++;
				$p[$id]['weapons']['all']['suicides']++;

				$p[$id]['roles'][$p[$id]['role']['last']]['deaths']++;
				$p[$id]['roles']['all']['deaths']++;
				$p[$id]['weapons']["suicide_$weapon"]['deaths']++;
				$p[$id]['weapons']['all']['deaths']++;
			}

			// -----------------------------------------------------------------
			// triggered
			// triggered "chargedeployed"
			// triggered "killedobject" (object "OBJ_SENTRYGUN") (weapon "shotgun_soldier") (objectowner "|RES|Stinkfist<26><STEAM_0:1:229390><Blue>") (attacker_position "-2606 -1010 -84")
			// triggered "kill assist" against "[CSTF]Comic<15><STEAM_0:0:3448133><Red>" (assister_position "-2614 -1316 -255") (attacker_position "-2587 -1530 -230") (victim_position "-2921 -1619 -287")
			// triggered "domination" against "[CSTF]Comic<15><STEAM_0:0:3448133><Red>" (assist "1")
			// triggered "flagevent" (event "picked up") (position "-3016 -1536 -281")
			// triggered "flagevent" (event "defended") (position "-2988 -238 -127")
			// triggered "flagevent" (event "dropped") (position "-3057 -1524 -281")
			// triggered "flagevent" (event "captured") (position "-2922 -1412 -261")
			// triggered "builtobject" (object "OBJ_SENTRYGUN") (position "-2322 -807 -255")
			// -----------------------------------------------------------------
			else if (preg_match('/^triggered/',$action,$m)) {

				$action = preg_replace("/\s*\(\w+position \".*?\"\)/",'',$action);

				if (preg_match('/^triggered "(.+?)"\s?(.*?)\s*$/',$action,$m)) {}

				// Skip if not ready
				if (!$ready) { continue; }

				$trigger = $m[1];
				$details = $m[2];

				// -------------------------------------------------------------
				// builtobject
				// -------------------------------------------------------------
				if ($trigger == 'builtobject') {
					if (preg_match('/^\(object "(.+?)"\)/',$details,$m)) {
						$object = $m[1];

						// Find the current role and update role array
						$role = object_to_role($object);
						if ($role) { $p[$id]['role']['last'] = $role; }

						// Update built arrays
						if (!strcmp($role,'engineer')) {
							$p[$id]['roles'][$p[$id]['role']['last']]['builtobjects']++;
							$p[$id]['roles']['all']['builtobjects']++;
						}
						else if (!strcmp($role,'spy')) {
							$p[$id]['roles'][$p[$id]['role']['last']]['sappersplaced']++;
							$p[$id]['roles']['all']['sappersplaced']++;
						}
					}
				}

				// -------------------------------------------------------------
				// killedobject
				// -------------------------------------------------------------
				else if ($trigger == 'killedobject') {
					if (preg_match('/^\(object "(.+?)"\) \(weapon "(.+?)"\) \(objectowner ".+?<\d+><STEAM_\d:\d:\d+><\w+>"\)/',$details,$m)) {
						$object = $m[1];
						$weapon = $m[2];

						// Find the current role and update role array
						$role = weapon_to_role($weapon);
						if ($role) { $p[$id]['role']['last'] = $role; }

						// Add to player's array
						$p[$id]['roles'][$p[$id]['role']['last']]['killedobjects']++;
						$p[$id]['roles']['all']['killedobjects']++;
						$p[$id]['weapons'][$weapon]['killedobjects']++;
						$p[$id]['weapons']['all']['killedobjects']++;
					}
				}

				// -------------------------------------------------------------
				// captureblocked
				// -------------------------------------------------------------
				else if ($trigger == 'captureblocked') {
					$p[$id]['roles'][$p[$id]['role']['last']]['capturesblocked']++;
					$p[$id]['roles']['all']['capturesblocked']++;
				}

				// -------------------------------------------------------------
				// captureblocked
				// -------------------------------------------------------------
				else if ($trigger == 'damage') {
					$p[$id]['roles'][$p[$id]['role']['last']]['damage']+= $details;
					$p[$id]['roles']['all']['damage']+= $details;
				}

				// -------------------------------------------------------------
				// kill assist
				// -------------------------------------------------------------
				else if ($trigger == 'kill assist') {
					$p[$id]['roles'][$p[$id]['role']['last']]['assists']++;
					$p[$id]['roles']['all']['assists']++;

					// Update enemies array
					if (preg_match('/".+?<\d+><STEAM_(\d:\d:\d+)><\w+>"/',$details,$m)) {
						$p[$id]['enemies'][$m[1]]['assists']++;
					}
				}

				// -------------------------------------------------------------
				// domination
				// -------------------------------------------------------------
				else if ($trigger == 'domination') {
					$p[$id]['roles'][$p[$id]['role']['last']]['dominations']++;
					$p[$id]['roles']['all']['dominations']++;

					// Update enemies array
					if (preg_match('/".+?<\d+><STEAM_(\d:\d:\d+)><\w+>"/',$details,$m)) {
						$p[$id]['enemies'][$m[1]]['dominations']++;
						$p[$m[1]]['roles'][$p[$m[1]]['role']['last']]['dominated']++;
						$p[$m[1]]['roles']['all']['dominated']++;
						$p[$m[1]]['enemies'][$id]['dominated']++;
					}
				}

				// -------------------------------------------------------------
				// revenge
				// -------------------------------------------------------------
				else if ($trigger == 'revenge') {
					$p[$id]['roles'][$p[$id]['role']['last']]['revenges']++;
					$p[$id]['roles']['all']['revenges']++;

					// Update enemies array
					if (preg_match('/".+?<\d+><STEAM_(\d:\d:\d+)><\w+>"/',$details,$m)) {
						$p[$id]['enemies'][$m[1]]['revenges']++;
						$p[$m[1]]['roles'][$p[$m[1]]['role']['last']]['revenged']++;
						$p[$m[1]]['roles']['all']['revenged']++;
						$p[$m[1]]['enemies'][$id]['revenged']++;
					}
				}

				// -------------------------------------------------------------
				// chargedeployed
				// -------------------------------------------------------------
				else if ($trigger == 'chargedeployed') {
					$role = 'medic';
					$p[$id]['role']['last'] = $role;

					// Update ubers array
					$p[$id]['roles'][$p[$id]['role']['last']]['ubers']++;
					$p[$id]['roles']['all']['ubers']++;
				}
			}

			else {
				$event = preg_replace('/>/','&gt;',$event);
				$event = preg_replace('/</','&lt;',$event);
			}
		}
		// ---------------------------------------------------------------------
		// Team pointcaptured
		// L 01/04/2008 - 15:17:46: Team "Red" triggered "pointcaptured" (cp "0") (cpname "#Well_cap_blue_rocket") (numcappers "1") (player1 "|RES|spike<2><STEAM_ID_PENDING><Red>") (position1 "-1578 5788 -360")
		// L 01/04/2008 - 15:24:34: Team "Blue" triggered "pointcaptured" (cp "0") (cpname "#Gravelpit_cap_A") (numcappers "2") (player1 "Gompers<2><STEAM_0:1:99364><Blue>") (position1 "115 555 -184") (player2 "|RES|spike<3><STEAM_0:1:303223><Blue>") (position2 "155 649 -143")
		// ---------------------------------------------------------------------
		else if (preg_match('/^Team "(\w+)" triggered "pointcaptured" \(cp "(\d+)"\) \(cpname "(.+?)"\) \(numcappers "\d+"\).*?$/',$event,$m)) {

			// Strip position information
			$event = preg_replace("/\s*\(position\d+ \".*?\"\)/",'',$event);

			if (preg_match('/^Team "(\w+)" triggered "pointcaptured" \(cp "(\d+)"\) \(cpname "(.+?)"\) \(numcappers "\d+"\) (.+?)\s+$/',$event,$m)) {}

			// Skip if not ready
			if (!$ready) { continue; }

			$team = $m[1];
			$cp = $m[2];
			$cpname = $m[3];
			$cappers = $m[4];

			// Capture point details
			$c['names'][$cp] = $cpname;
			// Reverse logic
			if ($reversed) {
				if (!strcmp($team,'Blue')) { $team = 'Red'; }
				else { $team = 'Blue'; }
			}
			$char = 'a';
			while (array_key_exists($stamp . $char,$c['list'])) { $char++; }
			$c['list'][$stamp . $char] = $cp . "===" . $team . "===POINT";

			// Split into each player that capped
			$cappers = split('\) ',$cappers);
			foreach ($cappers as $capper) {
				if (preg_match('/".+?<\d+><STEAM_(\d:\d:\d+)><\w+>"/',$capper,$m)) {
					$cid = $m[1];

					// Add to caps array
					$p[$cid]['roles'][$p[$cid]['role']['last']]['caps']++;
					$p[$cid]['roles']['all']['caps']++;
				}
			}
		}

		// ---------------------------------------------------------------------
		// World triggered Round_Win
		// example: World triggered "Round_Win" (winner "Red")
		// ---------------------------------------------------------------------
		else if (preg_match('/^World triggered "Round_Win"/',$event,$m)) {
			// Capture point resets
			if (!is_array($c['list'])) { $c['list'] = array(); }
			$char = 'a';
			while (array_key_exists($stamp . $char,$c['list'])) { $char++; }
			$c['list'][$stamp . $char] = "===RESET===";
		}
	}

    if(!$tvRecorded || !$fileClosed){
        return 0;
    }

	// -------------------------------------------------------------------------
	// Get the most used alias
	// -------------------------------------------------------------------------
	foreach ($p as $id => $arr) {
		$p[$id]['alias'] = max_key_assoc_val($p[$id]['aliases']);
	}

	// -------------------------------------------------------------------------
	// Figure out the team to place the player on
	// Store final team in $p[$id]['team']['team']
	// -------------------------------------------------------------------------
	foreach ($p as $id => $arr) {
		if ($clanbattle) {
			$p[$id]['team']['team'] = $p[$id]['team']['initial'];
		}
		else {
			if ($p[$id]['team']['Red'] > $p[$id]['team']['Blue']) {
				$p[$id]['team']['team'] = 'Red';
			}
			else {
				$p[$id]['team']['team'] = 'Blue';
			}
		}
	}

	// -------------------------------------------------------------------------
	// Compute points and sort by points
	// -------------------------------------------------------------------------
	foreach ($p as $id => $arr) {
		foreach (($p[$id]['roles']?$p[$id]['roles']:array()) as $role => $arr1) {
			if (!strcmp($role,'all')) { continue; }
			$points = 0;
			$points += $p[$id]['roles'][$role]['kills'];
			$points += $p[$id]['roles'][$role]['backstabs'];
			$points += $p[$id]['roles'][$role]['headshots'];
			$points += floor($p[$id]['roles'][$role]['assists'] / 2);
			$points += $p[$id]['roles'][$role]['killedobjects'];
			$points += $p[$id]['roles'][$role]['caps'];
			$points += $p[$id]['roles'][$role]['capturesblocked'];
			$points += $p[$id]['roles'][$role]['ubers'];

			$p[$id]['roles'][$role]['points'] = $points;
			$p[$id]['roles']['all']['points'] += $points;
		}
	}
	// Sort by points
	$pnts = array();
	foreach ($p as $id => $arr) {
		$pnts[$id] = $p[$id]['roles']['all']['points'];
	}
	array_multisort($pnts, SORT_DESC, $p);

	// -------------------------------------------------------------------------
	// Create totals per team
	// -------------------------------------------------------------------------
	$totals = array();
	foreach ($p as $id => $arr) {
		$totals[$p[$id]['team']['team']]['points'] += $p[$id]['roles']['all']['points'];
		$totals[$p[$id]['team']['team']]['kills'] += $p[$id]['roles']['all']['kills'];
		$totals[$p[$id]['team']['team']]['assists'] += $p[$id]['roles']['all']['assists'];
		$totals[$p[$id]['team']['team']]['backstabs'] += $p[$id]['roles']['all']['backstabs'];
		$totals[$p[$id]['team']['team']]['headshots'] += $p[$id]['roles']['all']['headshots'];
		$totals[$p[$id]['team']['team']]['killedobjects'] += $p[$id]['roles']['all']['killedobjects'];
		$totals[$p[$id]['team']['team']]['ubers'] += $p[$id]['roles']['all']['ubers'];
		$totals[$p[$id]['team']['team']]['builtobjects'] += $p[$id]['roles']['all']['builtobjects'];
		$totals[$p[$id]['team']['team']]['dominations'] += $p[$id]['roles']['all']['dominations'];
		$totals[$p[$id]['team']['team']]['revenges'] += $p[$id]['roles']['all']['revenges'];
		$totals[$p[$id]['team']['team']]['capturesblocked'] += $p[$id]['roles']['all']['capturesblocked'];
		$totals[$p[$id]['team']['team']]['caps'] += $p[$id]['roles']['all']['caps'];
	}

	// -------------------------------------------------------------------------
	// Figure out clan names if it's a clanbattle
	// -------------------------------------------------------------------------
	if ($clanbattle) {
		$cmp = array();
		foreach ($p as $id1 => $arr1) {
			foreach ($p as $id2 => $arr2) {

				// Don't compare to self
				if (!strcmp($id1,$id2)) { continue; }

				// Don't compare to other team
				if (strcmp($p[$id1]['team']['initial'],$p[$id2]['team']['initial'])) { continue; }

				// Strings to compare
				$name1 = $p[$id1]['alias'];
				$name2 = $p[$id2]['alias'];

				// Length of substr for both
				for ($i=3; $i<8; $i++) {
					// Start of substr for $name1
					for ($j=0; $j<=(strlen($name1)-$i); $j++) {
						$str = substr($name1,$j,$i);
						// Start of substr for $name2
						for ($k=0; $k<=(strlen($name2)-$i); $k++) {
							if (!strcmp($str,substr($name2,$k,$i))) {
								$cmp[$p[$id1]['team']['initial']][$str]++;
							}
						}
					}
				}
			}
		}
		foreach ($cmp as $key => $val) {
			// Delete keys less that have less than 20 occurances
			foreach ($cmp[$key] as $k => $v) { if ($v < 20) { unset($cmp[$key][$k]); } }
			$cmp[$key] = collapse_keys($cmp[$key]);
			$cmp[$key]['clan'] = max_key_assoc_val($cmp[$key]);
		}
		foreach ($p as $id => $arr) {
			$p[$id]['clan'] = max_key_assoc_val($cmp[$p[$id]['team']['initial']]);
		}
	}

	// -------------------------------------------------------------------------
	// Create HTML string for each player
	// -------------------------------------------------------------------------
	foreach ($p as $id => $arr) {
		$p[$id]['html'] = colons_to_underscores($id);
	}

	// -------------------------------------------------------------------------
	// Compute 'class' string for each player
	// -------------------------------------------------------------------------
	foreach ($p as $id => $arr) {
		$num_roles = 0;
		$role1_name = '';
		$role1_val = 0;
		$role2_name = '';
		$role2_val = 0;

		// Go through the roles and the time played on each role and pick the top
		// two to put in the string. Add an elipsis if there are more than 2
		foreach ($p[$id]['role'] as $role => $val) {
			if (!strcmp($role,'last') || !strcmp($role,'last_stamp')) { continue; }
			// skip classes played less than 10 seconds
			if ($val < 10) { continue; }
			if (!strcmp($role,'unknown')) { continue; }
			$num_roles++;
			if ($val > $role1_val) {
				$role2_val = $role1_val;
				$role2_name = $role1_name;
				$role1_val = $val;
				$role1_name = $role;
			}
			else if ($val > $role2_val) {
				$role2_val = $val;
				$role2_name = $role;
			}
		}
		if (strcmp('',$role2_name)) { $middle = "/"; }
		else { $middle = ""; }
		$p[$id]['role']['str'] = shorten_role($role1_name) . $middle . shorten_role($role2_name);
		if ($num_roles > 2) { $p[$id]['role']['str'] .= "/..."; }
	}

	// -------------------------------------------------------------------------
	// Create main weapons array and sort by kills
	// -------------------------------------------------------------------------
	$weapons = array();
	foreach ($p as $id => $arr) {
		foreach (($p[$id]['weapons']?$p[$id]['weapons']:array()) as $weapon => $row) {
			if (!strcmp($weapon,'all')) { continue; }
			if (!$row['kills']) { continue; }
			$weapons[$weapon][$p[$id]['team']['team']]['kills'] += $row['kills'];
			$weapons[$weapon]['all']['kills'] += $row['kills'];
			$weapons['all']['all']['kills'] += $row['kills'];
			if ($row['kills'] > $weapons[$weapon]['all']['max_kills']) {
				$weapons[$weapon]['all']['max_kills'] = $row['kills'];
				$weapons[$weapon]['all']['max_killer'] = $id;
				$weapons[$weapon]['all']['max_team'] = $p[$id]['team']['team'];
			}
		}
	}
	// Sort by points
	$weaponkills = array();
	foreach ($weapons as $weapon => $arr) {
		$weaponkills[$weapon] = $weapons[$weapon]['all']['kills'];
	}
	array_multisort($weaponkills, SORT_DESC, $weapons);

	// -------------------------------------------------------------------------
	// Sort individual player's classes by play time
	// -------------------------------------------------------------------------
	foreach ($p as $id => $arr) {
		$playtime = array();
		foreach (($p[$id]['roles']?$p[$id]['roles']:array()) as $role => $row) {
			$playtime[$role] = $p[$id]['role'][$role];
		}
		if ($p[$id]['roles']) { array_multisort($playtime, SORT_DESC, $p[$id]['roles']); }
	}

	// -------------------------------------------------------------------------
	// Create main chat array and sort by time
	// -------------------------------------------------------------------------
	$chat = array();
	foreach ($p as $id => $arr) {
		foreach (($p[$id]['mm1']?$p[$id]['mm1']:array()) as $mm1 => $val) {
			$char = 'a';
			while (array_key_exists($mm1 . $char,$chat)) { $char++; }
			$chat[$mm1 . $char]['said'] = $val;
			$chat[$mm1 . $char]['who'] = $id;
			$chat[$mm1 . $char]['team'] = $p[$id]['team']['team'];
			$chat[$mm1 . $char]['type'] = 'say';
		}
		foreach (($p[$id]['mm2']?$p[$id]['mm2']:array()) as $mm1 => $val) {
			$char = 'a';
			while (array_key_exists($mm1 . $char,$chat)) { $char++; }
			$chat[$mm1 . $char]['said'] = $val;
			$chat[$mm1 . $char]['who'] = $id;
			$chat[$mm1 . $char]['team'] = $p[$id]['team']['team'];
			$chat[$mm1 . $char]['type'] = 'say_team';
		}
	}
	$char = 'zz';
	$chat[$basestamp . $char]['said'] = "<b>MATCH BEGINS</b>";
	// Sort by key
	ksort($chat);

	// -------------------------------------------------------------------------
	// Create capture point table
	// -------------------------------------------------------------------------
	$cstatus = array();
	$prevtime = $basestamp . 'z';
	// Set the base color, use _red_ or _blue_ to know what caps default to
	foreach (($c['names']?$c['names']:array()) as $cid => $cname) {
		if (preg_match('/_(red|blue)_/i',$cname,$m)) { $cstatus[$basestamp . 'z'][$cid] = ucfirst($m[1]); }
		else { $cstatus[$basestamp . 'z'][$cid] = 'Black'; }
	}
	if (!is_array($cstatus[$basestamp . 'z'])) { $cstatus[$basestamp . 'z'] = array(); }
	ksort($cstatus[$basestamp . 'z']);
	foreach (($c['list']?$c['list']:array()) as $ctime => $row) {
		$split = split('===',$row);
		// split[0] is the capture point number that associates with $c['names'][$split[0]]
		// split[1] is the team that performed the point or flag cap or RESET
		// split[2] is the type of cap, either FLAG or POINT
		if (!strcmp($split[1],'RESET')) {
			// Set the base color, use _red_ or _blue_ to know what caps default to
			foreach (($c['names']?$c['names']:array()) as $cid => $cname) {
				if (preg_match('/_(red|blue)_/i',$cname,$m)) { $cstatus[$ctime][$cid] = ucfirst($m[1]); }
				else { $cstatus[$ctime][$cid] = 'Black'; }
			}
			$prevtime = $ctime;
		}
		else if (!strcmp($split[2],'POINT')) {
			foreach ($c['names'] as $cid => $cname) {
				if ($cid == $split[0]) { $cstatus[$ctime][$cid] = $split[1]; }
				else { $cstatus[$ctime][$cid] = $cstatus[$prevtime][$cid]; }
			}
			$prevtime = $ctime;
		}
		if (!is_array($cstatus[$ctime])) { $cstatus[$ctime] = array(); }
		ksort($cstatus[$ctime]);
	}

	// -------------------------------------------------------------------------
	// DEBUG
	// -------------------------------------------------------------------------
	if ($_GET['debug']) {
		print "<pre>";
		print "cmp\n";
		print_r($cmp);
		print "c\n";
		print_r($c);
		print "cstatus\n";
		print_r($cstatus);
		print "totals\n";
		print_r($totals);
		print "chat\n";
		print_r($chat);
		print "weapons\n";
		print_r($weapons);
		print "players\n";
		print_r($p);
		print "</pre>";
	}

	// -------------------------------------------------------------------------
	// HTML OUTPUT
	// -------------------------------------------------------------------------
	// Note: We have to add spaces to table cells in the total columns because
	// if there is nothing to display IE won't show the top border

	if (!($fh = fopen($directory . "/index.html",'w'))) { return 0; }
	chmod($directory . "/index.html", 0755);

	$nav = <<<EOT
		<li><a href="../index.php">About</a></li>
		<li><a href="../list.php">List</a></li>
		<li class='act'><a href="index.html">Match</a></li>
EOT;

	// -------------------------------------------------------------------------
	// Individual player tables
	// -------------------------------------------------------------------------
	$trh = <<<EOT
		<tr>
			<th width=120px>Class</th>
			<th width=80px>Play<br>Time</th>
			<th>Points</th>
			<th>Kills</th>
			<th>Assists</th>
			<th>Deaths</th>
			<th>Killed<br>Objs</th>
			<th>Caps</th>
			<th>Caps<br>Blkd</th>
			<th>Damage</th>
			<th>Ubers</th>
			<th>Built</th>
			<th>Dmntns</th>
			<th>Rvngs</th>
		</tr>
EOT;

	// Create the individual weapons table header for each team
	$thw['Red'] = <<<EOT
		<tr>
			<th width=150px>Weapon</th>
			<th width=50px>Kills</th>
			<th width=50px>Deaths</th>
EOT;
	$thw['Blue'] = $thw['Red'];
	// Iterate through the players and add a column for those players that are on
	// the other team
	foreach ($p as $id => $arr) {
		if (!strcmp($p[$id]['team']['team'],'Red')) { $thw['Blue'] .= "<th class='lineRed'><a href='{$p[$id]['html']}.html'>{$p[$id]['alias']}</a></th>"; }
		else { $thw['Red'] .= "<th class='lineBlue'><a href='{$p[$id]['html']}.html'>{$p[$id]['alias']}</a></th>"; }
	}

	$thw['Red'] .= "</tr>";
	$thw['Blue'] .= "</tr>";

	// Loop through players
	foreach ($p as $id => $arr) {
		// Create file for each player with format 0_0_<STEAMID.html
		if (!($pfh = fopen($directory . "/{$p[$id]['html']}.html",'w'))) { return 0; }
		chmod($directory . "/{$p[$id]['html']}.html", 0755);

		// Navigation for player page
		$pnav = <<<EOT
			<li><a href="../index.php">About</a></li>
			<li><a href="../list.php">List</a></li>
			<li><a href="index.html">Match</a></li>
			<li class='act'><a href="{$p[$id]['html']}.html">Player</a></li>
EOT;
		if ($clanbattle) { $tmpstr = '- '; }
		$ptable .= "<div class='contentheader{$p[$id]['team']['team']}'>{$p[$id]['alias']} {$tmpstr}{$p[$id]['clan']}</div><table class='maintable'>{$trh}";

		// ---------------------------------------------------------------------
		// Individual player class table, one row for each role
		// ---------------------------------------------------------------------
		$l = 0;
		foreach (($p[$id]['roles']?$p[$id]['roles']:array()) as $role => $row) {
			if (!strcmp($role,'all')) { continue; }
			if (!strcmp($role,'unknown')) { continue; }
			$tmp = $l++ % 2;
			$timeplayed = $p[$id]['role'][$role];
			$timeplayed_min = floor($p[$id]['role'][$role] / 60);
			$timeplayed_sec = $p[$id]['role'][$role] % 60;
			$timeplayed = sprintf("%02d:%02d",$timeplayed_min,$timeplayed_sec);
			$tr = <<<EOT
				<tr class="tr{$tmp}">
					<td>{$role}</td>
					<td>{$timeplayed}</td>
					<td>{$p[$id]['roles'][$role]['points']}</td>
					<td>{$p[$id]['roles'][$role]['kills']}</td>
					<td>{$p[$id]['roles'][$role]['assists']}</td>
					<td>{$p[$id]['roles'][$role]['deaths']}</td>
					<td>{$p[$id]['roles'][$role]['killedobjects']}</td>
					<td>{$p[$id]['roles'][$role]['caps']}</td>
					<td>{$p[$id]['roles'][$role]['capturesblocked']}</td>
					<td>{$p[$id]['roles'][$role]['damage']}</td>
					<td>{$p[$id]['roles'][$role]['ubers']}</td>
					<td>{$p[$id]['roles'][$role]['builtobjects']}</td>
					<td>{$p[$id]['roles'][$role]['dominations']}</td>
					<td>{$p[$id]['roles'][$role]['revenges']}</td>
				</tr>
EOT;
			$ptable .= $tr;
		}

		// Class table totals
		$tr = <<<EOT
			<tr class='tr3'>
				<td><b>Totals</b></th>
				<td>&nbsp;</th>
				<td>{$p[$id]['roles']['all']['points']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['kills']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['assists']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['deaths']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['killedobjects']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['caps']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['capturesblocked']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['damage']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['ubers']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['builtobjects']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['dominations']}&nbsp;</th>
				<td>{$p[$id]['roles']['all']['revenges']}&nbsp;</th>
			</tr>
EOT;

		$ptable .= $tr;
		$ptable .= "</table>";
		$phtml = $ptable;

		// ---------------------------------------------------------------------
		// Individual player weapons table, one row for each weapon
		// ---------------------------------------------------------------------
		$ptable = "<div class='contentheader3'>Weapons</div><table class='maintable'>";
		$ptable .= $thw[$p[$id]['team']['team']];

		// Sort by kills
		$pweaponkills = array();
		foreach (($p[$id]['weapons']?$p[$id]['weapons']:array()) as $sweapon => $row3) {
			$pweaponkills[$sweapon] = $p[$id]['weapons'][$sweapon]['kills'];
		}
		if ($p[$id]['weapons']) {
			array_multisort($pweaponkills, SORT_DESC, $p[$id]['weapons']);
		}

		// Create weapons table
		$l = 0;
		foreach (($p[$id]['weapons']?$p[$id]['weapons']:array()) as $weapon => $row) {
			if (!strcmp($weapon,'all')) { continue; }
			$tmp = $l++ % 2;
			$tr = <<<EOT
				<tr class="tr{$tmp}">
					<td>{$weapon}</td>
					<td>{$p[$id]['weapons'][$weapon]['kills']}</td>
					<td>{$p[$id]['weapons'][$weapon]['deaths']}</td>
EOT;
			// Loop through players on the other team and add a cell
			foreach ($p as $id2 => $arr2) {
				if (strcmp($p[$id]['team']['team'],$p[$id2]['team']['team'])) {
					$tmp_d = $p[$id]['enemies'][$id2]['weapons'][$weapon]['deaths'];
					$tmp_k = $p[$id]['enemies'][$id2]['weapons'][$weapon]['kills'];
					if (!$tmp_d) { $tmp_d = "0"; }
					if (!$tmp_k) { $tmp_k = "0"; }
					$tr .= "<td>{$tmp_k} - {$tmp_d}</td>";
				}
			}
			$tr .= "</tr>";
			$ptable .= $tr;
		}

		// Add totals for weapons table
		$tr = <<<EOT
			<tr class='tr3'>
				<td><b>Totals</b></td>
				<td>&nbsp;</td>
				<td>&nbsp;</td>
EOT;

		foreach ($p as $id2 => $arr2) {
			if (strcmp($p[$id]['team']['team'],$p[$id2]['team']['team'])) {
				$tmp_d = $p[$id]['enemies'][$id2]['weapons']['all']['deaths'];
				$tmp_k = $p[$id]['enemies'][$id2]['weapons']['all']['kills'];
				if (!$tmp_d) { $tmp_d = "0"; }
				if (!$tmp_k) { $tmp_k = "0"; }
				$tr .= "<td>{$tmp_k} - {$tmp_d}</td>";
			}
		}

		$tr .= "</tr>";
		$ptable .= $tr . "</table>";
		$phtml .= "<br>" . $ptable;
		fwrite($pfh,return_page($phtml,$pnav,1));
	}

	// -------------------------------------------------------------------------
	// First two tables, main blue and main red
	// -------------------------------------------------------------------------
	$trh = <<<EOT
		<tr>
			<th width=80px>SteamId</th>
			<th width=150px>Name</th>
			<th width=100px>Classes</th>
			<th>Points</th>
			<th>Kills</th>
			<th>Assists</th>
			<th>Deaths</th>
			<th>Killed<br>Objs</th>
			<th>Caps</th>
			<th>Caps<br>Blkd</th>
			<th>Damage</th>
			<th>Ubers</th>
			<th>Built</th>
			<th>Dmntns</th>
			<th>Rvngs</th>
		</tr>
EOT;

	if ($clanbattle) { $tmpstr = '- '; }
	$blue = "<div class='breadcrumbs' style=\"font-size:15px;\">Download the demo file of this game : <a href='http://demos.tf2pug.org/{$tvFileName}.dem'>{$tvFileName}</a></div>";
	$blue .= "<div class='contentheader'>Blue {$tmpstr}{$cmp['Blue']['clan']}</div><table class='maintable'>{$trh}";
	$red = "<div class='contentheader2'>Red {$tmpstr}{$cmp['Red']['clan']}</div><table class='maintable2'>{$trh}";

	// Loop through each player and seperate them into two teams
	$tmpa['Red'] = 0;
	$tmpa['Blue'] = 0;
	foreach ($p as $id => $arr) {
		$tmpa['mod'] = $tmpa[$p[$id]['team']['team']]++ % 2;
		$tr = <<<EOT
			<tr class="tr{$tmpa['mod']}">
				<td>$id</th>
				<td><a href="{$p[$id]['html']}.html">{$p[$id]['alias']}</a></th>
				<td>{$p[$id]['role']['str']}</th>
				<td>{$p[$id]['roles']['all']['points']}</th>
				<td>{$p[$id]['roles']['all']['kills']}</th>
				<td>{$p[$id]['roles']['all']['assists']}</th>
				<td>{$p[$id]['roles']['all']['deaths']}</th>
				<td>{$p[$id]['roles']['all']['killedobjects']}</th>
				<td>{$p[$id]['roles']['all']['caps']}</th>
				<td>{$p[$id]['roles']['all']['capturesblocked']}</th>
				<td>{$p[$id]['roles']['all']['damage']}</th>
				<td>{$p[$id]['roles']['all']['ubers']}</th>
				<td>{$p[$id]['roles']['all']['builtobjects']}</th>
				<td>{$p[$id]['roles']['all']['dominations']}</th>
				<td>{$p[$id]['roles']['all']['revenges']}</th>
			</tr>
EOT;
		if (!strcmp($p[$id]['team']['team'],'Red')) { $red .= $tr; }
		else if (!strcmp($p[$id]['team']['team'],'Blue')) { $blue .= $tr; }
	}

	# Totals row
	foreach ($totals as $tteam => $row) {
		$ttr = <<<EOT
			<tr class="tr3">
				<td>&nbsp;</td>
				<td><b>Totals</b></td>
				<td>&nbsp;</td>
				<td>{$row['points']}&nbsp;</td>
				<td>{$row['kills']}&nbsp;</td>
				<td>{$row['assists']}&nbsp;</td>
				<td>{$row['deaths']}&nbsp;</td>
				<td>{$row['killedobjects']}&nbsp;</td>
				<td>{$row['caps']}&nbsp;</td>
				<td>{$row['capturesblocked']}&nbsp;</td>
				<td>{$row['damage']}&nbsp;</td>
				<td>{$row['ubers']}&nbsp;</td>
				<td>{$row['builtobjects']}&nbsp;</td>
				<td>{$row['dominations']}&nbsp;</td>
				<td>{$row['revenges']}&nbsp;</td>
			</tr>
EOT;
		if (!strcmp($tteam,'Blue')) { $blue .= $ttr; }
		else if (!strcmp($tteam,'Red')) { $red .= $ttr; }
	}

	$blue .= "</table>";
	$red .= "</table>";

	// -------------------------------------------------------------------------
	// Main weapons table
	// -------------------------------------------------------------------------
	$trh = <<<EOT
		<tr>
			<th width=130px>Weapon</th>
			<th width=50px>Total<br>Kills</th>
			<th width=50px>Red<br>Kills</th>
			<th width=50px>Blue<br>Kills</th>
			<th>Biggest Killer</th>
			<th width=50px>%<br>Total</th>
		</tr>
EOT;

	$weap = "<div class='contentheader3'>Weapons</div><table class='maintable'>{$trh}";

	// One row for each weapon, stats computed prior to this
	$i = 0;
	foreach ($weapons as $weapon => $row) {
		if (!strcmp($weapon,'all')) { continue; }
		$tmp = $i++ % 2;
		$percent = round($row['all']['kills'] * 100 / $weapons['all']['all']['kills']);
		$tr = <<<EOT
			<tr class="tr{$tmp}">
				<td>{$weapon}</td>
				<td>{$row['all']['kills']}</td>
				<td>{$row['Red']['kills']}</td>
				<td>{$row['Blue']['kills']}</td>
				<td class="line{$row['all']['max_team']}"><a href="{$p[$row['all']['max_killer']]['html']}.html">{$p[$row['all']['max_killer']]['alias']}</a> - {$row['all']['max_kills']}</td>
				<td>{$percent}</td>
			</tr>
EOT;
		$weap .= $tr;
	}

	$weap .= "</table>";

	// -------------------------------------------------------------------------
	// Caps table
	// -------------------------------------------------------------------------
	$trh = <<<EOT
		<tr>
			<th width=80px>Time</th>
			<th colspan=99>Status / Cap Name</th>
		</tr>
EOT;

	$cpt = "<div class='contentheader3'>Caps</div><table class='maintable'>{$trh}";

	$i = 0;
	foreach (($c['list']?$c['list']:array()) as $ctime => $row) {
		$tmp = $i++ % 2;
		// We have to chop off the last character to find the timestamp and then
		// compare it with the base timestamp
		$cstamp = substr($ctime,0,-1) - $basestamp;
		$cmin = sprintf("%02d",abs(floor($cstamp / 60)));
		$csec = sprintf("%02d",abs($cstamp % 60));
		if ($cstamp < 0) { $sign = '-'; }
		else { $sign = '+'; }
		// We have to split the entry by '===' because we used that format
		// earlier instead of hashes (i don't remember why i didn't use hashes)
		$split = split('===',$row);
		// split[0] is the capture point number that associates with $c['names'][$split[0]]
		// split[1] is the team that performed the point or flag cap or RESET
		// split[2] is the type of cap, either FLAG or POINT
		if (!strcmp($split[2],'FLAG')) {
			$str_before = "";
			$str_after = "<td width=10px>&nbsp;</td>";
			if (!strcmp($split[1],'Red')) {
				$str_before = $str_after;
				$str_after = "";
			}
			$status = "{$str_before}<td width=10px class='{$split[1]}'>&nbsp;</td>{$str_after}<td width=100%>{$split[1]} captured the flag</td>";
		}
		else if ((!strcmp($split[2],'POINT')) || (!strcmp($split[1],'RESET'))) {
			$status = "";
			foreach ($cstatus[$ctime] as $cpnum => $color) {
				$status .= "<td width=10px class='$color'>$cpnum</td>";
			}
			$status .= "<td width=100%>&nbsp;{$c['names'][$split[0]]}</td>";
		}
		$tr = <<<EOT
			<tr class="tr{$tmp}">
				<td>{$sign}{$cmin}:{$csec}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td>
				{$status}
			</tr>
EOT;
		$cpt .= $tr;
	}

	$cpt .= "</table>";

	// -------------------------------------------------------------------------
	// Chat table
	// -------------------------------------------------------------------------
	$trh = <<<EOT
		<tr>
			<th width=80px>Time</th>
			<th width=150px>Player</th>
			<th width=75px>Type</th>
			<th>Said</th>
		</tr>
EOT;

	$ch = "<div class='contentheader3'>Chat</div><table class='maintable'>{$trh}";

	$i = 0;
	foreach ($chat as $ctime => $row) {
		$tmp = $i++ % 2;
		// We have to chop off the last two characters to find the timestamp and
		// then compare it with the base timestamp
		$cstamp = substr($ctime,0,-2) - $basestamp;
		$cmin = sprintf("%02d",abs(floor($cstamp / 60)));
		$csec = sprintf("%02d",abs($cstamp % 60));
		if ($cstamp < 0) { $sign = '-'; }
		else { $sign = '+'; }
		$tr = <<<EOT
			<tr class="tr{$tmp}">
				<td>{$sign}{$cmin}:{$csec}</td>
				<td class="line{$row['team']}"><a href="{$p[$row['who']]['html']}.html">{$p[$row['who']]['alias']}</a></td>
				<td>{$row['type']}</td>
				<td>{$row['said']}</td>
			</tr>
EOT;
		$ch .= $tr;
	}

	$ch .= "</table>";

	$html = $blue . "<br>" . $red . "<br>" . $weap . "<br>" . $cpt . "<br>" . $ch;
    
    $statsIndex[] =  $date_day . '/' . $date_month . '/' . $date_year;
    $mapName = explode('_', $directory);
    $statsIndex[] = $mapName[2];

	fwrite($fh,return_page($html,$nav,1));

    $logName = explode('/', $directory);
    $logName = $logName[2];
    foreach($statsIndex as $index){
        $index = $database->sqlEscapeString($index);
        $oldIndex = $database->queryAssoc("SELECT * FROM statsIndex where id = '" . $index . "'");
        $explodedOldIndex = array();
        $runUpdate = 1;
        if($oldIndex){
            $explodedOldIndex = explode(':', $oldIndex[0]['files']);
            if(!in_array($index, $explodedOldIndex)){
                $runUpdate = 0;
                $updatedFiles = $oldIndex[0]['files'] . ':' . $logName;
                $database->query("UPDATE statsIndex SET files = '$updatedFiles' WHERE id = '$index'");
            }
        }
        if($runUpdate)
            $database->query("INSERT INTO statsIndex VALUES ('$index', '$logName')");
    }

    $database->query("INSERT INTO files VALUES ('$logName', $fullDate)");

	return 1;
}

// Returns the role that is associated with the weapon parameter or false
// O(1)
function weapon_to_role ($weapon) {
	if (($weapon == 'tf_projectile_rocket') || ($weapon == 'shotgun_soldier') || ($weapon == 'shovel')) { return 'soldier'; }
	if (($weapon == 'minigun') || ($weapon == 'shotgun_hwg') || ($weapon == 'fists')) { return 'heavyweapons'; }
	if (($weapon == 'sniperrifle') || ($weapon == 'smg') || ($weapon == 'club')) { return 'sniper'; }
	if (($weapon == 'obj_sentrygun') || ($weapon == 'shotgun_primary') || ($weapon == 'pistol') || ($weapon == 'wrench')) { return 'engineer'; }
	if (($weapon == 'tf_projectile_pipe') || ($weapon == 'tf_projectile_pipe_remote') || ($weapon == 'bottle')) { return 'demoman'; }
	if (($weapon == 'flamethrower') || ($weapon == 'shotgun_pyro') || ($weapon == 'fireaxe')) { return 'pyro'; }
	if (($weapon == 'knife') || ($weapon == 'revolver') || ($weapon == 'obj_attachment_sapper')) { return 'spy'; }
	if (($weapon == 'scattergun') || ($weapon == 'pistol_scout') || ($weapon == 'bat')) { return 'scout'; }
	if (($weapon == 'syringegun_medic') || ($weapon == 'bonesaw')) { return 'medic'; }
	return false;
}

// Returns the role that is associated with the object parameter or false
// O(1)
function object_to_role ($object) {
	if ($object == 'OBJ_ATTACHMENT_SAPPER') { return 'spy'; }
	if (($object == 'OBJ_TELEPORTER_ENTRANCE') || ($object == 'OBJ_TELEPORTER_EXIT') || ($object == 'OBJ_DISPENSER') || ($object == 'OBJ_SENTRYGUN')) { return 'engineer'; }
	return false;
}

// Returns the array with keys that are substrings of other keys collapsed into
// the longer length key if they have the same value
// O(n^2)
function collapse_keys($arr) {
	foreach ($arr as $key1 => $val1) {
		foreach ($arr as $key2 => $val2) {
			if ($val1 !== $val2) { continue; }
			if (!strcmp($key1,$key2)) { continue; }
			if (strpos($key1,$key2) !== false) {
				unset($arr[$key2]);
			}
		}
	}
	return $arr;
}

// Returns the key from the array that has the highest associated value
// O(n)
function max_key_assoc_val ($arr) {
	$max = 0;
	$str = '';
	foreach (($arr?$arr:array()) as $key => $val) {
		if ($val > $max) {
			$max = $val;
			$str = $key;
		}
	}
	return $str;
}

// Returns the parameter role shortened
// O(1)
function shorten_role ($role) {
	switch ($role) {
		case 'heavyweapons':
			return 'hwg';
		case 'soldier':
			return 'sold';
		case 'engineer':
			return 'engi';
		case 'medic':
			return 'med';
		case 'demoman':
			return 'demo';
		default:
			return $role;
	}
}

function colons_to_underscores ($str) {
	return preg_replace('/:/','_',$str);
}

?>
