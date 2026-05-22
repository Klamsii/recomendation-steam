import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file
from openpyxl import Workbook
import io
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


def get_game_details_full(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english"

    try:
        response = requests.get(url, timeout=20).json()

        if str(appid) not in response:
            return None

        if not response[str(appid)]["success"]:
            return None

        data = response[str(appid)]["data"]

        genres = []
        if "genres" in data:
            genres = [
                genre["description"]
                for genre in data["genres"]
            ]

        developers = data.get("developers", [])
        publishers = data.get("publishers", [])

        screenshots = []
        if "screenshots" in data:
            screenshots = [
                screenshot["path_full"]
                for screenshot in data["screenshots"][:5]
            ]

        metacritic_score = None
        if "metacritic" in data:
            metacritic_score = data["metacritic"].get("score")

        price = "Free"
        if "price_overview" in data:
            price = data["price_overview"].get("final_formatted", "Unknown")

        return {
            "appid": appid,
            "name": data.get("name", "Unknown"),
            "header_image": data.get("header_image"),
            "short_description": data.get("short_description", ""),
            "genres": genres,
            "developers": developers,
            "publishers": publishers,
            "release_date": data.get("release_date", {}).get("date", "Unknown"),
            "metacritic_score": metacritic_score,
            "price": price,
            "website": data.get("website"),
            "screenshots": screenshots
        }

    except Exception as e:
        print("GetGameDetailsFull error:", e)
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

    with open("games.json", "r", encoding="utf-8") as file:
        popular_games = json.load(file)

    owned_ids = [game["appid"] for game in games]
    recommendations = []

    for game in popular_games:
        if game["appid"] in owned_ids:
            continue

        if any(genre in favorite_genres for genre in game["genres"]):
            recommendations.append({
                "appid": game["appid"],
                "name": game["name"],
                "reason": (
                    f"Matches your favorite genres: "
                    f"{', '.join(game['genres'])}"
                )
            })

    return recommendations[:6]

def get_top_genres(games):
    genre_hours = {}

    for game in games[:50]:  # анализируем первые 50 игр
        details = get_game_details(game["appid"])

        if not details:
            continue

        for genre in details["genres"]:
            if genre not in genre_hours:
                genre_hours[genre] = 0

            genre_hours[genre] += game["hours"]

    # сортировка по количеству часов
    sorted_genres = sorted(
        genre_hours.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # берём топ-5 жанров
    top_genres = sorted_genres[:5]

    return {
        "labels": [genre for genre, _ in top_genres],
        "values": [round(hours, 1) for _, hours in top_genres]
    }
def get_game_statistics(games):
    top_hours = sorted(games, key=lambda g: g["hours"], reverse=True)[:5]
    top_recent = sorted(
        [g for g in games if g["recent_hours"] > 0],
        key=lambda g: g["recent_hours"],
        reverse=True
    )[:5]

    return {
        "hours_labels": [g["name"] for g in top_hours],
        "hours_values": [g["hours"] for g in top_hours],
        "recent_labels": [g["name"] for g in top_recent],
        "recent_values": [g["recent_hours"] for g in top_recent]
    }

@app.route("/game/<int:appid>")
def game_details_api(appid):
    details = get_game_details_full(appid)

    if not details:
        return jsonify({
            "error": "Game details not found."
        }), 404

    return jsonify(details)


@app.route("/", methods=["GET", "POST"])
def index():
    game_stats = None
    genre_stats = None
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
                    "Please set both 'My Profile' and "
                    "'Game Details' to Public."
                )
                return render_template("index.html", error=error)

            recommendations = get_recommendations(games)
            genre_stats = get_top_genres(games)
            game_stats = get_game_statistics(games)

        except Exception as e:
            print("ERROR:", e)
            error = (
                "Unable to load your Steam data. "
                "Make sure your Steam ID is correct "
                "and your profile is public."
            )

    return render_template(
        "index.html",
        game_stats=game_stats,
        profile=profile,
        games=games,
        recommendations=recommendations,
        genre_stats=genre_stats,
        error=error
    )

@app.route("/export")
def export_excel():
    with open("games.json", "r", encoding="utf-8") as f:
        recommendations = json.load(f)

    wb = Workbook()
    ws = wb.active
    ws.title = "Recommended Games"

    ws.append(["App ID", "Game Name", "Genres"])

    for game in recommendations:
        ws.append([
            game.get("appid"),
            game.get("name"),
            ", ".join(game.get("genres", []))
        ])

    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    return send_file(
        excel_file,
        download_name="recommended_games.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)
