import os
from dotenv import load_dotenv
from flask import Flask, render_template, request
import requests
from datetime import datetime

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("STEAM_API_KEY")


def get_player_summary(steam_id):
    url = (
        "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
        f"?key={API_KEY}&steamids={steam_id}"
    )

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)

        print("GetPlayerSummaries status:", response.status_code)
        print(response.text[:500])

        if response.status_code != 200:
            return None

        data = response.json()
        players = data.get("response", {}).get("players", [])

        if not players:
            return None

        player = players[0]

        return {
            "name": player.get("personaname", "Unknown"),
            "avatar": player.get("avatarfull"),
            "country": player.get("loccountrycode", "Unknown"),
            "last_online": datetime.fromtimestamp(
                player.get("lastlogoff", 0)
            ).strftime("%d.%m.%Y %H:%M")
        }

    except Exception as e:
        print("GetPlayerSummaries error:", e)
        return None


def resolve_vanity_url(vanity_name):
    url = (
        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
        f"?key={API_KEY}&vanityurl={vanity_name}"
    )

    try:
        response = requests.get(url, timeout=20)
        data = response.json()

        if data.get("response", {}).get("success") == 1:
            return data["response"]["steamid"]

        return None
    except Exception as e:
        print("ResolveVanityURL error:", e)
        return None


def get_steam_level(steam_id):
    url = (
        "https://api.steampowered.com/IPlayerService/GetSteamLevel/v1/"
        f"?key={API_KEY}&steamid={steam_id}"
    )

    try:
        response = requests.get(url, timeout=20)
        data = response.json()
        return data.get("response", {}).get("player_level", 0)
    except Exception as e:
        print("GetSteamLevel error:", e)
        return 0


def get_owned_games(steam_id):
    url = (
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        f"?key={API_KEY}"
        f"&steamid={steam_id}"
        "&include_appinfo=true"
        "&include_played_free_games=true"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)

        if response.status_code != 200:
            print("GetOwnedGames status:", response.status_code)
            print(response.text[:500])
            return None

        data = response.json()

        if "response" not in data or "games" not in data["response"]:
            print("Games are private or unavailable.")
            print(data)
            return None

        games = data["response"]["games"]
        result = []

        for game in games:
            result.append({
                "appid": game.get("appid"),
                "name": game.get("name"),
                "hours": round(game.get("playtime_forever", 0) / 60, 1),
                "recent_hours": round(game.get("playtime_2weeks", 0) / 60, 1),
                "last_played": (
                    "Played in last 2 weeks"
                    if game.get("playtime_2weeks", 0) > 0
                    else "No recent activity"
                )
            })

        result.sort(key=lambda game: game["hours"], reverse=True)

        return result

    except Exception as e:
        print("GetOwnedGames error:", e)
        return None


def get_game_details(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"

    try:
        response = requests.get(url, timeout=20).json()

        if not response[str(appid)]["success"]:
            return None

        data = response[str(appid)]["data"]
        genres = []

        if "genres" in data:
            genres = [genre["description"] for genre in data["genres"]]

        return {
            "genres": genres
        }

    except Exception as e:
        print("GetGameDetails error:", e)
        return None


def get_recommendations(games):
    if not games:
        return []

    top_games = games[:5]
    favorite_genres = []

    for game in top_games:
        details = get_game_details(game["appid"])
        if details:
            favorite_genres.extend(details["genres"])

    favorite_genres = list(set(favorite_genres))

    popular_games = [
        {"appid": 730, "name": "Counter-Strike 2", "genres": ["Action", "FPS"]},
        {"appid": 570, "name": "Dota 2", "genres": ["MOBA", "Strategy"]},
        {"appid": 578080, "name": "PUBG: BATTLEGROUNDS", "genres": ["Shooter", "Battle Royale"]},
        {"appid": 1172470, "name": "Apex Legends", "genres": ["Shooter", "Battle Royale"]},
        {"appid": 271590, "name": "Grand Theft Auto V", "genres": ["Open World", "Action"]},
        {"appid": 292030, "name": "The Witcher 3: Wild Hunt", "genres": ["RPG", "Open World"]},
        {"appid": 1086940, "name": "Baldur's Gate 3", "genres": ["RPG"]},
    ]

    owned_ids = [game["appid"] for game in games]
    recommendations = []

    for game in popular_games:
        if game["appid"] in owned_ids:
            continue

        if any(genre in favorite_genres for genre in game["genres"]):
            recommendations.append({
                "appid": game["appid"],
                "name": game["name"],
                "reason": f"Matches your favorite genres: {', '.join(game['genres'])}"
            })

    return recommendations[:6]


@app.route("/", methods=["GET", "POST"])
def index():
    profile = None
    games = []
    recommendations = []
    error = None

    if request.method == "POST":
        steam_input = request.form.get("steam_id", "").strip()

        if "steamcommunity.com/profiles/" in steam_input:
            steam_id = steam_input.split(
                "steamcommunity.com/profiles/"
            )[1].split("/")[0]

        elif "steamcommunity.com/id/" in steam_input:
            vanity_name = steam_input.split(
                "steamcommunity.com/id/"
            )[1].split("/")[0]
            steam_id = resolve_vanity_url(vanity_name)

        elif steam_input.isdigit():
            steam_id = steam_input

        else:
            steam_id = resolve_vanity_url(steam_input)

        if not steam_id:
            error = "Invalid Steam ID or custom profile URL."
            return render_template("index.html", error=error)

        try:
            profile = get_player_summary(steam_id)

            if not profile:
                error = "Profile not found."
                return render_template("index.html", error=error)

            profile["level"] = get_steam_level(steam_id)

            games = get_owned_games(steam_id)

            if games is None:
                error = (
                    "Your Steam profile or Game Details are private. "
                    "Please set both 'My Profile' and 'Game Details' to Public."
                )
                return render_template("index.html", error=error)

            recommendations = get_recommendations(games)

        except Exception as e:
            print("ERROR:", e)
            error = (
                "Unable to load your Steam data. "
                "Make sure your Steam ID is correct and your profile is public."
            )

    return render_template(
        "index.html",
        profile=profile,
        games=games,
        recommendations=recommendations,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)
