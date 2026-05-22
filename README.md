# recomendation-steam
This program helps users find new games based on their library. You can also find out about game discounts.



#main purpose
This app's main purpose is to fully view and analyze a user's profile. With a few simple steps, you can view a summary of information about any public profile you enter. Our app offers a wide variety of categories: you can see their most frequent games, how many hours they've played, what games they own, and what you can recommend based on their profile. Our data is always up-to-date because we're directly connected to the Steam gaming platform and update information every second.

#Technologies Used
    Python
    Flask
    Steam Web API
    Requests
    OpenPyXL
    HTML/CSS/JavaScript
    JSON


steam-game-recommender/
│
├── templates/
│   └── index.html
│
├── games.json
├── render.yaml
├── .env
├── app.py


#Files Description
app.py — main Flask backend application
index.html — frontend interface and UI design
games.json — local database of games and genres
render.yaml — deployment configuration for Render
.env — environment variables and Steam API key

#Features
Steam Profile Analysis

The application can analyze:

SteamID64
Custom Steam URLs
Full Steam profile links

Example:

https://steamcommunity.com/id/example



#Excel Export

Users can export recommendations into an Excel file:

recommended_games.xlsx

Using OpenPyXL library.
