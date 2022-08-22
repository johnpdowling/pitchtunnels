#!/usr/bin/env python3

#imports
from math import sqrt
import datetime, json, urllib.request

#globals
gamesEndpoint = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={date}&endDate={date}&gameType=R&fields=dates,date,dayNight,games,gamePk,teams,away,home,team,name"
gamedataEndpoint = "https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"

def getGamedate():
    while True:
        try:
            gameday = input("Enter date of game (YYYY-MM-DD): ")
            gamedate = datetime.datetime.strptime(gameday,"%Y-%m-%d").date()
            break
        except:
            print("Error parsing valid date from entry")
    return gamedate.strftime('%Y-%m-%d')

def getGamesFromDate(gamedate):
    endpoint = gamesEndpoint.format(date = gamedate)
    games = { }
    try:
        r = urllib.request.urlopen(endpoint)
        data = json.loads(r.read().decode())
        # print(type(data))
        if len(data['dates']) > 0:
            games = data['dates'][0]['games']
        else:
            print("No games scheduled on entered date")
    except:
        print("Error getting games scheduled on entered date")
    return games

def selectGame(games):
    index = 0
    for game in games:
        print(str(index + 1) + ": " + game['teams']['away']['team']['name'] + " @ " + 
                                      game['teams']['home']['team']['name'] +
                                      " (" + game['dayNight'] + ")")
        index += 1
    while True:
        try:
            selectedGame = input("Select game: ")
            if(int(selectedGame) > 0 and int(selectedGame) <= len(games)):
                return games[int(selectedGame) - 1]
            print("Game selection out of range")
        except:
            print("Error parsing game selection")

def getAllPitchersFromGame(liveData):
    pitchers = {}
    for play in liveData['plays']['allPlays']:
        if 'matchup' in play.keys():
            if not play['matchup']['pitcher']['id'] in pitchers.keys():
                pitchers[str(play['matchup']['pitcher']['id'])] = play['matchup']['pitcher']
    return pitchers

def getAllPitchesByPitcherFromGame(liveData, pitcher):
    pitches = []
    for play in liveData['plays']['allPlays']:
        if 'matchup' in play.keys():
            if pitcher == play['matchup']['pitcher']:
                for playEvent in play['playEvents']:
                    if playEvent['isPitch']:
                        pitches.append(playEvent)
    return pitches

def getDataFromGame(gamePkNum):
    endpoint = gamedataEndpoint.format(gamePk=str(gamePkNum))
    r = urllib.request.urlopen(endpoint)
    return json.loads(r.read().decode())
    
def getAllPitchersAndPitchesFromGame(liveData):
    allPitches = { }
    
    pitchers = getAllPitchersFromGame(liveData)
    for pitcher in pitchers.values():
        pitches = getAllPitchesByPitcherFromGame(liveData, pitcher)
        allPitches[str(pitcher['id'])] = pitches
    
    return allPitches

def doTheyTunnel(pitch1, pitch2):
    min_diff = 6.5
    max_diff = 18.5
    tunnel_dist = 33
    release_dist = 50
    max_val = 28
    val  = sqrt(pow(pitch1['pX']-pitch2['pX'],2)+pow(pitch1['pZ']-pitch2['pZ'],2))*12
    diff = sqrt(pow(pitch1['pX']-pitch2['pX'],2)+pow(pitch1['pZ']-pitch2['pZ'],2))*12 - \
            2 * sqrt(
                     pow((pitch1['x0']+pitch1['vX0']*(-sqrt(pow(pitch1['vY0'],2)+2*pitch1['aY']*(tunnel_dist-release_dist))-pitch1['vY0'])/pitch1['aY']+0.5*pitch1['aX']*pow(((-sqrt(pow(pitch1['vY0'],2)+2*pitch1['aY']*(tunnel_dist-release_dist))-pitch1['vY0'])/pitch1['aY']),2))*12-
                     (pitch2['x0']+pitch2['vX0']*(-sqrt(pow(pitch2['vY0'],2)+2*pitch2['aY']*(tunnel_dist-release_dist))-pitch2['vY0'])/pitch2['aY']+0.5*pitch2['aX']*pow(((-sqrt(pow(pitch2['vY0'],2)+2*pitch2['aY']*(tunnel_dist-release_dist))-pitch2['vY0'])/pitch2['aY']),2))*12 ,2)+
                     pow((pitch1['z0']+pitch1['vZ0']*(-sqrt(pow(pitch1['vY0'],2)+2*pitch1['aY']*(tunnel_dist-release_dist))-pitch1['vY0'])/pitch1['aY']+0.5*pitch1['aZ']*pow(((-sqrt(pow(pitch1['vY0'],2)+2*pitch1['aY']*(tunnel_dist-release_dist))-pitch1['vY0'])/pitch1['aY']),2))*12-
                     (pitch2['z0']+pitch2['vZ0']*(-sqrt(pow(pitch2['vY0'],2)+2*pitch2['aY']*(tunnel_dist-release_dist))-pitch2['vY0'])/pitch2['aY']+0.5*pitch2['aZ']*pow(((-sqrt(pow(pitch2['vY0'],2)+2*pitch2['aY']*(tunnel_dist-release_dist))-pitch2['vY0'])/pitch2['aY']),2))*12 ,2)
                    )
    return (min_diff <= diff <= max_diff and val < max_val)

def getTunneledPitches(allPitches):
    tunneledPitches = { }
    for pitcherId in allPitches.keys():
        tunnels = []
        pitchEvents = allPitches[pitcherId]
        for i in range(len(pitchEvents)):
            for j in range(i + 1, len(pitchEvents)):
                if pitchEvents[i]['details']['type']['code'] == pitchEvents[j]['details']['type']['code']:
                    # don't care if 2 pitches are same type
                   continue
                pitch1 = pitchEvents[i]['pitchData']['coordinates']
                pitch2 = pitchEvents[j]['pitchData']['coordinates']
                if doTheyTunnel(pitch1, pitch2):
                    tunnel = (pitchEvents[i], pitchEvents[j])
                    tunnels.append(tunnel)
        tunneledPitches[pitcherId] = tunnels
    return tunneledPitches

def outputTunnelsToCSV(allPitchers, tunneledPitches, filename):
    with open(filename, "w") as f:
        f.write("Pitcher ID,Pitcher Name,Pitch1 Type,Pitch1 ID,Pitch2 Type,Pitch2 ID\n")
        for pitcherID in allPitchers.keys():
            for tunnel in tunneledPitches[pitcherID]:
                f.write(pitcherID + "," + allPitchers[pitcherID]['fullName'] + "," +
                        tunnel[0]['details']['type']['description'] + "," + tunnel[0]['playId'] + "," + 
                        tunnel[1]['details']['type']['description'] + "," + tunnel[1]['playId'] + "\n")

if __name__=="__main__":
    gamedate = getGamedate()
    games = getGamesFromDate(gamedate)
    if len(games) > 0:
        game = selectGame(games)
        print("Selected " + game['teams']['away']['team']['name'] + " @ " + game['teams']['home']['team']['name'])
        data = None
        try:
            data = getDataFromGame(game['gamePk'])
        except:
            print("Error getting game data")
            exit(1)
        liveData = data['liveData']
        if len(liveData['plays']['allPlays']) == 0:
            print("No data for this game yet")
            exit(0)
        allPitchers = getAllPitchersFromGame(liveData)
        allPitches = getAllPitchersAndPitchesFromGame(liveData)
        tunneledPitches = getTunneledPitches(allPitches)
        for pitcherId in allPitchers.keys():
            print(allPitchers[pitcherId]['fullName'] + ": " + str(len(allPitches[pitcherId])) + " pitches, " + str(len(tunneledPitches[pitcherId])) + " tunnel pairs")
        outputToCSV = False
        while True:
            answer = input("Output to CSV? (Y/N): ").lower()
            if answer == "y" or answer == "n":
                outputToCSV = (answer == "y")
                break
        if outputToCSV:
            filename = "pitchTunnels_" + str(game['gamePk']) + ".csv"
            outputTunnelsToCSV(allPitchers, tunneledPitches, filename)